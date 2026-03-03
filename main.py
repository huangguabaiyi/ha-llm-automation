"""
HA 自动化大模型创建工具 — CLI 入口
"""

import json
import re
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backup.manager import BackupManager
from ha_client.automations import (AutomationManager, extract_action_services,
                                    extract_entity_ids, extract_yaml_from_text,
                                    normalize_automation, unwrap_automation,
                                    validate_automation)
from ha_client.connection import HAConnection, load_config
from ha_client.entities import (EntityManager, enrich_entities_with_areas,
                                 fetch_registry_data)
from knowledge.fetcher import DocFetcher, HA_DOC_URLS
from knowledge.prompts import (DEFAULT_VISIBLE_DOMAINS, build_consolidate_prompt,
                               build_feasibility_prompt, build_optimize_analysis_prompt,
                               build_optimize_yaml_prompt, build_system_prompt)
from llm_client import create_client

app = typer.Typer(
    name="ha-llm",
    help="Home Assistant 自动化大模型创建工具",
    add_completion=False,
    invoke_without_command=True,
)
backup_app = typer.Typer(help="备份管理命令")
app.add_typer(backup_app, name="backup")

console = Console()
CONFIG_PATH = "config.json"


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context):
    """直接运行进入交互式模式选择"""
    if ctx.invoked_subcommand is not None:
        return  # 有子命令时交给子命令处理

    rprint(Panel(
        "[bold]HA 自动化大模型工具[/bold]\n\n"
        "  [cyan]1. 创建[/cyan]  — 用自然语言描述，AI 生成新自动化\n"
        "  [cyan]2. 优化[/cyan]  — 分析并优化单条已有自动化\n"
        "  [cyan]3. 聚合[/cyan]  — 批量整合所有自动化（合并重复、纠正错误）",
        title="请选择模式", border_style="blue",
    ))
    mode = input("\n> ").strip()
    if mode == "1":
        create()
    elif mode == "2":
        optimize()
    elif mode == "3":
        consolidate()
    else:
        rprint("[yellow]请输入 1、2 或 3[/yellow]")


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------

def get_config() -> dict:
    try:
        return load_config(CONFIG_PATH)
    except FileNotFoundError as e:
        rprint(f"[red]错误：{e}[/red]")
        raise typer.Exit(1)


def get_conn(config: dict) -> HAConnection:
    return HAConnection(config)


def get_automation_manager(config: dict) -> AutomationManager:
    return AutomationManager(HAConnection(config))


def get_backup_manager(config: dict) -> BackupManager:
    backup_cfg = config.get("backup", {})
    return BackupManager(
        backup_dir=backup_cfg.get("backup_dir", "./backup/archives"),
        max_versions=backup_cfg.get("max_versions", 10),
    )


def get_entities(config: dict) -> list[dict]:
    """
    获取实体列表：先拿注册表数据（exclude_ids + area_map），
    再创建 EntityManager（一次性过滤隐藏/禁用/诊断实体），最后注入区域信息。
    WebSocket 失败时自动降级，不阻断主流程。
    """
    registry = {"area_map": {}, "exclude_ids": set()}
    try:
        registry = fetch_registry_data(config)
    except Exception:
        pass

    conn = get_conn(config)
    manager = EntityManager(conn, exclude_ids=registry["exclude_ids"])
    entities = manager.get_all_entities()

    area_map = registry["area_map"]
    if area_map:
        entities = enrich_entities_with_areas(entities, area_map)

    return entities


def get_visible_domains(config: dict) -> set[str]:
    """从 config.domains 计算最终可见 domain 集合"""
    domains_cfg = config.get("domains", {})
    extra = set(domains_cfg.get("extra_visible") or [])
    hidden = set(domains_cfg.get("hidden") or [])
    return (DEFAULT_VISIBLE_DOMAINS | extra) - hidden


def get_doc_fetcher(config: dict) -> DocFetcher:
    knowledge_cfg = config.get("knowledge", {})
    return DocFetcher(
        cache_dir=knowledge_cfg.get("cache_dir", "./knowledge/cache"),
        ttl_days=knowledge_cfg.get("cache_ttl_days", 7),
    )


# ------------------------------------------------------------------
# 命令：init — 配置初始化向导
# ------------------------------------------------------------------

@app.command()
def init():
    """交互式初始化配置文件"""
    if Path(CONFIG_PATH).exists():
        overwrite = typer.confirm(f"{CONFIG_PATH} 已存在，是否覆盖？", default=False)
        if not overwrite:
            rprint("[yellow]已取消[/yellow]")
            raise typer.Exit()

    rprint(Panel("[bold]HA 自动化工具 — 配置向导[/bold]"))

    ha_url = typer.prompt("Home Assistant 地址", default="http://homeassistant.local:8123")
    ha_token = typer.prompt("Long-Lived Access Token")
    verify_ssl = typer.confirm("启用 SSL 验证？", default=True)

    rprint("\n[bold]LLM 配置[/bold]")
    provider = typer.prompt("LLM Provider", default="anthropic",
                            show_choices=True,
                            type=typer.Choice(["anthropic", "openai", "openai_compatible"]))
    api_key = typer.prompt("API Key")
    default_model = "claude-sonnet-4-6" if provider == "anthropic" else "gpt-4o"
    model = typer.prompt("模型名称", default=default_model)
    base_url = None
    if provider == "openai_compatible":
        base_url = typer.prompt("Base URL（如 http://localhost:11434/v1）")

    config = {
        "ha": {
            "url": ha_url,
            "token": ha_token,
            "verify_ssl": verify_ssl,
            "timeout": 30,
        },
        "llm": {
            "provider": provider,
            "api_key": api_key,
            "model": model,
            "base_url": base_url,
            "max_tokens": 8192,
            "temperature": 0.3,
        },
        "backup": {"max_versions": 10, "backup_dir": "./backup/archives"},
        "knowledge": {"cache_dir": "./knowledge/cache", "cache_ttl_days": 7},
    }

    Path(CONFIG_PATH).write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rprint(f"[green]配置已保存到 {CONFIG_PATH}[/green]")
    rprint("[dim]提示：config.json 已加入 .gitignore，不会被提交到 git[/dim]")


# ------------------------------------------------------------------
# 命令：test-connection
# ------------------------------------------------------------------

@app.command("test-connection")
def test_connection():
    """测试 Home Assistant 连接"""
    config = get_config()
    conn = get_conn(config)
    with console.status("正在连接 Home Assistant..."):
        try:
            info = conn.test_connection()
        except Exception as e:
            rprint(f"[red]连接失败：{e}[/red]")
            raise typer.Exit(1)

    rprint(f"[green]连接成功！[/green]")
    rprint(f"  版本：{info.get('version', '未知')}")
    rprint(f"  地址：{config['ha']['url']}")
    rprint(f"  位置：{info.get('location_name', '未知')}")


# ------------------------------------------------------------------
# 命令：list-entities
# ------------------------------------------------------------------

@app.command("list-entities")
def list_entities(
    domain: Annotated[Optional[str], typer.Option("--domain", "-d", help="按 domain 过滤")] = None,
    search: Annotated[Optional[str], typer.Option("--search", "-s", help="关键字搜索")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="最多显示条数")] = 50,
):
    """查看实体列表"""
    config = get_config()

    with console.status("获取实体列表..."):
        try:
            entities = get_entities(config)
        except Exception as e:
            rprint(f"[red]获取失败：{e}[/red]")
            raise typer.Exit(1)

    if search:
        kw = search.lower()
        entities = [
            e for e in entities
            if kw in e["entity_id"].lower() or kw in e.get("friendly_name", "").lower()
        ]
    elif domain:
        entities = [e for e in entities if e["domain"] == domain]

    entities = entities[:limit]
    table = Table(title=f"实体列表（共 {len(entities)} 条）", show_lines=False)
    table.add_column("entity_id", style="cyan", no_wrap=True)
    table.add_column("名称", style="white")
    table.add_column("状态", style="green")
    table.add_column("domain", style="dim")

    for e in entities:
        table.add_row(
            e["entity_id"],
            e.get("friendly_name", ""),
            e.get("state", ""),
            e.get("domain", ""),
        )
    console.print(table)


# ------------------------------------------------------------------
# 命令：list-automations
# ------------------------------------------------------------------

@app.command("list-automations")
def list_automations():
    """列出所有自动化"""
    config = get_config()
    manager = get_automation_manager(config)

    with console.status("获取自动化列表..."):
        try:
            automations = manager.list_automations()
        except Exception as e:
            rprint(f"[red]获取失败：{e}[/red]")
            raise typer.Exit(1)

    table = Table(title=f"自动化列表（共 {len(automations)} 条）", show_lines=False)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("名称", style="cyan")
    table.add_column("描述", style="white")
    table.add_column("模式", style="yellow")

    for a in automations:
        table.add_row(a["id"], a["alias"], a.get("description", ""), a.get("mode", "single"))
    console.print(table)


# ------------------------------------------------------------------
# 命令：create — 自然语言创建自动化（核心功能）
# ------------------------------------------------------------------

@app.command()
def create(
    requirement: Annotated[Optional[str], typer.Argument(help="自动化需求描述（可交互输入）")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="只生成 YAML，不写入 HA")] = False,
    no_docs: Annotated[bool, typer.Option("--no-docs", help="不加载文档知识（节省 token）")] = False,
):
    """通过自然语言描述，用 AI 生成自动化"""
    config = get_config()

    if not requirement:
        rprint("[bold]请描述你想要的自动化（输入后按 Enter）：[/bold]")
        requirement = input("> ").strip()
        if not requirement:
            rprint("[yellow]未输入需求，已退出[/yellow]")
            raise typer.Exit()

    # 获取实体列表（含注册表过滤 + 区域信息）
    entities: list[dict] = []
    with console.status("获取实体列表与注册表..."):
        try:
            entities = get_entities(config)
            rprint(f"[dim]实体列表：{len(entities)} 个[/dim]")
        except Exception as e:
            rprint(f"[yellow]警告：获取实体失败（{e}），将不含实体信息[/yellow]")

    # 获取文档
    docs: dict[str, str] = {}
    if not no_docs:
        fetcher = get_doc_fetcher(config)
        with console.status("加载 HA 文档知识..."):
            try:
                docs = fetcher.get_preset_docs(
                    ["automation_basic", "automation_trigger", "automation_action"]
                )
            except Exception as e:
                rprint(f"[yellow]警告：文档加载失败（{e}），将不含文档知识[/yellow]")

    llm = create_client(config["llm"])
    visible_domains = get_visible_domains(config)

    # ------------------------------------------------------------------
    # Step 1 — 可行性检查
    # ------------------------------------------------------------------
    step1_entities: list[str] = []
    if entities:
        feasibility_prompt = build_feasibility_prompt(entities, visible_domains=visible_domains)
        with console.status("Step 1/2 — 分析需求可行性..."):
            try:
                feasibility_response = llm.chat_with_retry(
                    messages=[{"role": "user", "content": requirement}],
                    system=feasibility_prompt,
                )
            except Exception as e:
                rprint(f"[red]LLM 调用失败（Step 1）：{e}[/red]")
                raise typer.Exit(1)

        # 解析 JSON（LLM 可能在 JSON 前后加空行，strip 后解析）
        try:
            feasibility = json.loads(feasibility_response.strip())
        except Exception:
            rprint("[yellow]警告：可行性检查返回了非 JSON 格式，跳过 Step 1，直接生成 YAML[/yellow]")
            rprint(Panel(feasibility_response, title="Step 1 原始回复", border_style="yellow"))
            feasibility = {"feasible": True, "entities": [], "reason": ""}

        if not feasibility.get("feasible", True):
            rprint(f"[red]需求不可行：{feasibility.get('reason', '（无说明）')}[/red]")
            raise typer.Exit(1)

        step1_entities = feasibility.get("entities") or []
        reason = feasibility.get("reason", "")
        if reason:
            rprint(f"[dim]Step 1 分析：{reason}[/dim]")

    # ------------------------------------------------------------------
    # Step 2 — YAML 生成（使用 Step 1 筛选出的相关实体）
    # ------------------------------------------------------------------
    if step1_entities:
        step1_set = set(step1_entities)
        filtered_entities = [e for e in entities if e["entity_id"] in step1_set]
        if not filtered_entities:
            # Step 1 返回的 entity_id 与实体列表不匹配，fallback 全量
            filtered_entities = entities
    else:
        # Step 1 entities 为空但 feasible=true → fallback 全量
        filtered_entities = entities

    system_prompt = build_system_prompt(docs, filtered_entities, visible_domains=visible_domains)

    with console.status("Step 2/2 — AI 生成 YAML..."):
        try:
            response = llm.chat_with_retry(
                messages=[{"role": "user", "content": requirement}],
                system=system_prompt,
            )
        except Exception as e:
            rprint(f"[red]LLM 调用失败（Step 2）：{e}[/red]")
            raise typer.Exit(1)

    # 提取并校验 YAML
    yaml_str = extract_yaml_from_text(response)

    # 检查 LLM 是否返回了 YAML（而不是纯文字说明）
    parsed = yaml.safe_load(yaml_str)
    if not isinstance(parsed, dict):
        rprint("\n[yellow]AI 未能生成 YAML，返回了说明信息：[/yellow]")
        rprint(Panel(response, title="AI 回复", border_style="yellow"))
        raise typer.Exit(1)

    # ------------------------------------------------------------------
    # 交互式修改循环：展示 YAML → 用户确认或提修改意见 → 循环直到满意
    # ------------------------------------------------------------------
    valid_ids = {e["entity_id"] for e in entities} if entities else set()

    while True:
        rprint("\n[bold]生成的自动化配置：[/bold]")
        rprint(Panel(yaml_str, title="YAML", border_style="green"))

        # 解析校验
        try:
            auto_config = unwrap_automation(parsed)
            validate_automation(auto_config)
        except Exception as e:
            rprint(f"[red]YAML 校验失败：{e}，请输入修改意见重新生成[/red]")
            auto_config = None

        # 实体 ID 合法性校验
        if auto_config and valid_ids:
            used_ids = extract_entity_ids(auto_config)
            invalid_ids = used_ids - valid_ids
            if invalid_ids:
                rprint("[yellow]警告：以下实体 ID 在 HA 中不存在（可能是 LLM 编造）：[/yellow]")
                for eid in sorted(invalid_ids):
                    rprint(f"  [red]  - {eid}[/red]")

            bad_actions = extract_action_services(auto_config) & valid_ids
            if bad_actions:
                rprint("[red]错误：以下 action 字段填写了实体 ID 而非服务名：[/red]")
                for a in sorted(bad_actions):
                    rprint(f"  [red]  - {a}[/red]")
                auto_config = None  # 强制修改

        # 提示用户输入修改意见
        rprint("\n[dim]输入修改意见后回车让 AI 重新生成；直接回车接受当前配置[/dim]")
        feedback = input("> ").strip()

        if not feedback:
            if auto_config is None:
                rprint("[yellow]当前配置存在问题，请先输入修改意见[/yellow]")
                continue
            break  # 用户满意，退出循环

        # 用户有修改意见 → 调用 LLM 重新生成
        modify_msg = f"""请修改以下 Home Assistant 自动化配置：

当前配置：
```yaml
{yaml_str}
```

修改要求：{feedback}

请输出修改后的完整 YAML 配置。"""

        with console.status("AI 修改中..."):
            try:
                response = llm.chat_with_retry(
                    messages=[{"role": "user", "content": modify_msg}],
                    system=system_prompt,
                )
            except Exception as e:
                rprint(f"[red]LLM 调用失败：{e}[/red]")
                continue

        yaml_str = extract_yaml_from_text(response)
        parsed = yaml.safe_load(yaml_str)
        if not isinstance(parsed, dict):
            rprint("[yellow]AI 未能生成 YAML，请重新描述修改意见[/yellow]")
            rprint(Panel(response, title="AI 回复", border_style="yellow"))
            continue

    if dry_run:
        rprint("[yellow]--dry-run 模式，不写入 HA[/yellow]")
        raise typer.Exit()

    # 确认写入
    if not typer.confirm("\n是否将此自动化写入 Home Assistant？"):
        rprint("[yellow]已取消[/yellow]")
        raise typer.Exit()

    # 备份 + 写入
    auto_config = normalize_automation(auto_config)
    automation_manager = get_automation_manager(config)
    backup_manager = get_backup_manager(config)

    with console.status("备份现有自动化..."):
        try:
            existing = automation_manager.list_automations()
            backup_file = backup_manager.create_backup(existing)
            rprint(f"[dim]备份已保存：{backup_file}[/dim]")
        except Exception as e:
            rprint(f"[yellow]备份失败（{e}），是否仍要继续写入？[/yellow]")
            if not typer.confirm("继续？", default=False):
                raise typer.Exit()

    with console.status("写入 Home Assistant..."):
        try:
            new_id = automation_manager.create_automation(auto_config)
            automation_manager.reload_automations()
        except Exception as e:
            rprint(f"[red]写入失败：{e}[/red]")
            raise typer.Exit(1)

    rprint(f"[green]自动化创建成功！ID：{new_id}[/green]")


# ------------------------------------------------------------------
# 命令：update — 更新已有自动化
# ------------------------------------------------------------------

@app.command()
def update(
    automation_id: Annotated[str, typer.Option("--id", help="要更新的自动化 ID")] = "",
    requirement: Annotated[Optional[str], typer.Argument(help="修改需求描述")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
):
    """通过自然语言描述修改已有自动化"""
    config = get_config()
    automation_manager = get_automation_manager(config)

    # 选择要修改的自动化
    if not automation_id:
        automations = automation_manager.list_automations()
        rprint("\n[bold]当前自动化列表：[/bold]")
        for i, a in enumerate(automations, 1):
            rprint(f"  {i}. [{a['id']}] {a['alias']}")
        idx_str = typer.prompt("输入序号选择要修改的自动化")
        try:
            idx = int(idx_str) - 1
            automation_id = automations[idx]["id"]
        except (ValueError, IndexError):
            rprint("[red]无效序号[/red]")
            raise typer.Exit(1)

    # 获取现有配置
    with console.status("获取自动化配置..."):
        current = automation_manager.get_automation(automation_id)
    current_yaml = automation_manager.to_yaml(current)
    rprint(f"\n[bold]当前配置（{current.get('alias', automation_id)}）：[/bold]")
    rprint(Panel(current_yaml, title="当前 YAML", border_style="blue"))

    if not requirement:
        rprint("[bold]请描述你想要的修改：[/bold]")
        requirement = input("> ").strip()
        if not requirement:
            rprint("[yellow]未输入需求，已退出[/yellow]")
            raise typer.Exit()

    # 获取实体和文档（含注册表过滤 + 区域信息）
    entities: list[dict] = []
    with console.status("获取实体列表与注册表..."):
        try:
            entities = get_entities(config)
        except Exception:
            pass

    docs: dict[str, str] = {}
    fetcher = get_doc_fetcher(config)
    with console.status("加载文档知识..."):
        try:
            docs = fetcher.get_preset_docs(["automation_basic", "automation_trigger", "automation_action"])
        except Exception:
            pass

    system_prompt = build_system_prompt(docs, entities, visible_domains=get_visible_domains(config))
    user_msg = f"""请修改以下 Home Assistant 自动化配置：

当前配置：
```yaml
{current_yaml}
```

修改需求：{requirement}

请输出修改后的完整 YAML 配置。"""

    llm = create_client(config["llm"])
    with console.status("AI 修改中..."):
        try:
            response = llm.chat_with_retry(
                messages=[{"role": "user", "content": user_msg}],
                system=system_prompt,
            )
        except Exception as e:
            rprint(f"[red]LLM 调用失败：{e}[/red]")
            raise typer.Exit(1)

    yaml_str = extract_yaml_from_text(response)

    parsed = yaml.safe_load(yaml_str)
    if not isinstance(parsed, dict):
        rprint("\n[yellow]AI 未能生成 YAML，返回了说明信息：[/yellow]")
        rprint(Panel(response, title="AI 回复", border_style="yellow"))
        raise typer.Exit(1)

    rprint("\n[bold]修改后的配置：[/bold]")
    rprint(Panel(yaml_str, title="YAML", border_style="green"))

    try:
        new_config = unwrap_automation(parsed)
        validate_automation(new_config)
    except Exception as e:
        rprint(f"[red]YAML 校验失败：{e}[/red]")
        raise typer.Exit(1)

    # 实体 ID 合法性校验
    if entities:
        valid_ids = {e["entity_id"] for e in entities}
        used_ids = extract_entity_ids(new_config)
        invalid_ids = used_ids - valid_ids
        if invalid_ids:
            rprint(f"[yellow]警告：以下实体 ID 在 HA 中不存在：[/yellow]")
            for eid in sorted(invalid_ids):
                rprint(f"  [red]  - {eid}[/red]")
            if not typer.confirm("仍要继续写入？", default=False):
                raise typer.Exit()

        bad_actions = extract_action_services(new_config) & valid_ids
        if bad_actions:
            rprint(f"[red]错误：以下 action 字段填写了实体 ID 而非服务名：[/red]")
            for a in sorted(bad_actions):
                rprint(f"  [red]  - {a}[/red]")
            raise typer.Exit(1)

    if dry_run:
        rprint("[yellow]--dry-run 模式，不写入 HA[/yellow]")
        raise typer.Exit()

    if not typer.confirm("\n是否将修改写入 Home Assistant？"):
        rprint("[yellow]已取消[/yellow]")
        raise typer.Exit()

    # 备份 + 写入
    backup_manager = get_backup_manager(config)
    with console.status("备份中..."):
        try:
            existing = automation_manager.list_automations()
            backup_file = backup_manager.create_backup(existing)
            rprint(f"[dim]备份已保存：{backup_file}[/dim]")
        except Exception as e:
            rprint(f"[yellow]备份失败（{e}），是否仍要继续？[/yellow]")
            if not typer.confirm("继续？", default=False):
                raise typer.Exit()

    new_config = normalize_automation(new_config)
    with console.status("写入 Home Assistant..."):
        try:
            automation_manager.update_automation(automation_id, new_config)
            automation_manager.reload_automations()
        except Exception as e:
            rprint(f"[red]写入失败：{e}[/red]")
            raise typer.Exit(1)

    rprint(f"[green]自动化更新成功！[/green]")


# ------------------------------------------------------------------
# 命令：optimize — 单条自动化优化
# ------------------------------------------------------------------

@app.command()
def optimize(
    automation_id: Annotated[Optional[str], typer.Option("--id", help="要优化的自动化 ID")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="只展示优化结果，不写入 HA")] = False,
    no_docs: Annotated[bool, typer.Option("--no-docs", help="不加载文档知识（节省 token）")] = False,
):
    """分析并优化单条已有自动化（两步 LLM：理解意图→生成优化 YAML）"""
    config = get_config()
    automation_manager = get_automation_manager(config)

    # Step 1：选择自动化（只列出能获取完整配置的）
    if not automation_id:
        with console.status("获取自动化列表（探测可访问性...）"):
            all_automations = automation_manager.list_automations()
            # 过滤出能 GET 到完整配置的（排除旧 YAML 配置、无效 ID 等）
            accessible = []
            for a in all_automations:
                aid = a.get("id", "")
                if not aid or aid == "new":
                    continue
                try:
                    automation_manager.get_automation(aid)
                    accessible.append(a)
                except Exception:
                    pass
        if not accessible:
            rprint("[yellow]没有可优化的自动化（所有自动化均无法通过 API 获取完整配置）[/yellow]")
            rprint("[dim]提示：只有通过本工具或 HA UI 创建的自动化才支持优化[/dim]")
            raise typer.Exit()
        rprint(f"\n[bold]可优化的自动化（共 {len(accessible)} 条）：[/bold]")
        for i, a in enumerate(accessible, 1):
            rprint(f"  {i}. [dim][{a['id']}][/dim] {a['alias']}")
        idx_str = typer.prompt("输入序号选择要优化的自动化")
        try:
            idx = int(idx_str) - 1
            automation_id = accessible[idx]["id"]
        except (ValueError, IndexError):
            rprint("[red]无效序号[/red]")
            raise typer.Exit(1)

    # 获取完整配置
    with console.status("获取自动化配置..."):
        try:
            current = automation_manager.get_automation(automation_id)
        except Exception as e:
            rprint(f"[red]无法获取自动化配置：{e}[/red]")
            rprint("[dim]提示：只有通过本工具或 HA UI 创建的自动化才支持优化[/dim]")
            raise typer.Exit(1)
    current_yaml = automation_manager.to_yaml(current)
    rprint(f"\n[bold]当前配置（{current.get('alias', automation_id)}）：[/bold]")
    rprint(Panel(current_yaml, title="原始 YAML", border_style="blue"))

    # 获取实体列表
    entities: list[dict] = []
    with console.status("获取实体列表..."):
        try:
            entities = get_entities(config)
            rprint(f"[dim]实体列表：{len(entities)} 个[/dim]")
        except Exception as e:
            rprint(f"[yellow]警告：获取实体失败（{e}），将不含实体信息[/yellow]")

    llm = create_client(config["llm"])
    visible_domains = get_visible_domains(config)

    # ------------------------------------------------------------------
    # LLM Step 1 — 理解意图，找出问题和建议
    # ------------------------------------------------------------------
    analysis_prompt = build_optimize_analysis_prompt(
        current_yaml, entities, visible_domains=visible_domains
    )
    with console.status("Step 1/2 — 分析自动化意图与优化点..."):
        try:
            analysis_response = llm.chat_with_retry(
                messages=[{"role": "user", "content": "请分析这条自动化"}],
                system=analysis_prompt,
            )
        except Exception as e:
            rprint(f"[red]LLM 调用失败（Step 1）：{e}[/red]")
            raise typer.Exit(1)

    try:
        analysis = json.loads(analysis_response.strip())
    except Exception:
        rprint("[yellow]警告：分析返回了非 JSON 格式，将跳过分析直接生成优化 YAML[/yellow]")
        rprint(Panel(analysis_response, title="Step 1 原始回复", border_style="yellow"))
        analysis = {}

    # 展示分析报告
    if analysis:
        issues_text = "\n".join(f"  • {i}" for i in analysis.get("issues") or ["（无）"])
        suggestions_text = "\n".join(f"  • {s}" for s in analysis.get("suggestions") or ["（无）"])
        rprint(Panel(
            f"[bold]功能意图：[/bold]{analysis.get('intent', '未知')}\n\n"
            f"[bold]涉及实体：[/bold]{', '.join(analysis.get('related_entities') or []) or '（无）'}\n\n"
            f"[bold]发现问题：[/bold]\n{issues_text}\n\n"
            f"[bold]优化建议：[/bold]\n{suggestions_text}",
            title="分析报告", border_style="cyan",
        ))

    if not typer.confirm("\n是否继续生成优化后的配置？", default=True):
        rprint("[yellow]已取消[/yellow]")
        raise typer.Exit()

    # ------------------------------------------------------------------
    # LLM Step 2 — 生成优化后的完整 YAML
    # ------------------------------------------------------------------
    docs: dict[str, str] = {}
    if not no_docs:
        fetcher = get_doc_fetcher(config)
        with console.status("加载文档知识..."):
            try:
                docs = fetcher.get_preset_docs(
                    ["automation_basic", "automation_trigger", "automation_action"]
                )
            except Exception:
                pass

    optimize_prompt = build_optimize_yaml_prompt(
        current_yaml, analysis, entities, docs, visible_domains=visible_domains
    )
    with console.status("Step 2/2 — 生成优化后的 YAML..."):
        try:
            response = llm.chat_with_retry(
                messages=[{"role": "user", "content": "请生成优化后的完整自动化配置"}],
                system=optimize_prompt,
            )
        except Exception as e:
            rprint(f"[red]LLM 调用失败（Step 2）：{e}[/red]")
            raise typer.Exit(1)

    yaml_str = extract_yaml_from_text(response)
    parsed = yaml.safe_load(yaml_str)
    if not isinstance(parsed, dict):
        rprint("[yellow]AI 未能生成 YAML，返回了说明信息：[/yellow]")
        rprint(Panel(response, title="AI 回复", border_style="yellow"))
        raise typer.Exit(1)

    # ------------------------------------------------------------------
    # 交互式修改循环
    # ------------------------------------------------------------------
    valid_ids = {e["entity_id"] for e in entities} if entities else set()
    system_prompt = build_system_prompt(docs, entities, visible_domains=visible_domains)

    while True:
        rprint("\n[bold]优化后的自动化配置：[/bold]")
        rprint(Panel(yaml_str, title="优化 YAML", border_style="green"))

        try:
            auto_config = unwrap_automation(parsed)
            validate_automation(auto_config)
        except Exception as e:
            rprint(f"[red]YAML 校验失败：{e}，请输入修改意见重新生成[/red]")
            auto_config = None

        if auto_config and valid_ids:
            used_ids = extract_entity_ids(auto_config)
            invalid_ids = used_ids - valid_ids
            if invalid_ids:
                rprint("[yellow]警告：以下实体 ID 在 HA 中不存在（可能是 LLM 编造）：[/yellow]")
                for eid in sorted(invalid_ids):
                    rprint(f"  [red]  - {eid}[/red]")

        rprint("\n[dim]输入修改意见后回车让 AI 重新生成；直接回车接受当前配置[/dim]")
        feedback = input("> ").strip()

        if not feedback:
            if auto_config is None:
                rprint("[yellow]当前配置存在问题，请先输入修改意见[/yellow]")
                continue
            break

        modify_msg = f"""请修改以下 Home Assistant 自动化配置：

当前配置：
```yaml
{yaml_str}
```

修改要求：{feedback}

请输出修改后的完整 YAML 配置。"""
        with console.status("AI 修改中..."):
            try:
                response = llm.chat_with_retry(
                    messages=[{"role": "user", "content": modify_msg}],
                    system=system_prompt,
                )
            except Exception as e:
                rprint(f"[red]LLM 调用失败：{e}[/red]")
                continue
        yaml_str = extract_yaml_from_text(response)
        parsed = yaml.safe_load(yaml_str)
        if not isinstance(parsed, dict):
            rprint("[yellow]AI 未能生成 YAML，请重新描述修改意见[/yellow]")
            continue

    if dry_run:
        rprint("[yellow]--dry-run 模式，不写入 HA[/yellow]")
        raise typer.Exit()

    if not typer.confirm("\n是否将优化后的配置写入 Home Assistant？"):
        rprint("[yellow]已取消[/yellow]")
        raise typer.Exit()

    auto_config = normalize_automation(auto_config)
    backup_manager = get_backup_manager(config)
    with console.status("备份中..."):
        try:
            existing = automation_manager.list_automations()
            backup_file = backup_manager.create_backup(existing)
            rprint(f"[dim]备份已保存：{backup_file}[/dim]")
        except Exception as e:
            rprint(f"[yellow]备份失败（{e}），是否仍要继续？[/yellow]")
            if not typer.confirm("继续？", default=False):
                raise typer.Exit()

    with console.status("写入 Home Assistant..."):
        try:
            automation_manager.update_automation(automation_id, auto_config)
            automation_manager.reload_automations()
        except Exception as e:
            rprint(f"[red]写入失败：{e}[/red]")
            raise typer.Exit(1)

    rprint(f"[green]自动化优化成功！[/green]")


# ------------------------------------------------------------------
# 命令：consolidate — 多条自动化批量整合
# ------------------------------------------------------------------

@app.command()
def consolidate(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="只展示方案，不执行写入/删除")] = False,
):
    """分析全部自动化，合并重复项、纠正错误，逐条确认后执行"""
    config = get_config()
    automation_manager = get_automation_manager(config)
    llm = create_client(config["llm"])
    visible_domains = get_visible_domains(config)

    # Step 1：获取所有自动化摘要
    with console.status("获取自动化列表..."):
        automations = automation_manager.list_automations()
    if not automations:
        rprint("[yellow]当前没有任何自动化[/yellow]")
        raise typer.Exit()
    rprint(f"[dim]共找到 {len(automations)} 条自动化[/dim]")

    # 批量获取完整配置（跳过 id 无效的）
    automations_data: list[dict] = []
    with console.status("获取自动化完整配置..."):
        for a in automations:
            aid = a.get("id", "")
            if not aid or aid == "new":
                rprint(f"[dim]  跳过 {a['alias']}（ID 无效：{aid!r}）[/dim]")
                continue
            try:
                full = automation_manager.get_automation(aid)
                automations_data.append({
                    "id": aid,
                    "alias": a["alias"],
                    "yaml_str": automation_manager.to_yaml(full),
                })
            except Exception as e:
                rprint(f"[yellow]  跳过 {a['alias']}（获取失败：{e}）[/yellow]")

    if not automations_data:
        rprint("[yellow]没有可分析的自动化（所有条目 ID 无效或获取失败）[/yellow]")
        raise typer.Exit()
    rprint(f"[dim]成功获取 {len(automations_data)} 条完整配置[/dim]")

    # 获取实体列表
    entities: list[dict] = []
    with console.status("获取实体列表..."):
        try:
            entities = get_entities(config)
        except Exception:
            pass

    # LLM 单次整合分析
    consolidate_prompt = build_consolidate_prompt(
        automations_data, entities, visible_domains=visible_domains
    )
    with console.status("AI 分析整合方案中...（自动化较多时需要较长时间）"):
        try:
            analysis_response = llm.chat_with_retry(
                messages=[{"role": "user", "content": "请分析以上所有自动化，给出整合优化方案"}],
                system=consolidate_prompt,
            )
        except Exception as e:
            rprint(f"[red]LLM 调用失败：{e}[/red]")
            raise typer.Exit(1)

    # 解析 JSON（LLM 有时会加 markdown 代码块，尝试多种方式提取）
    plan: dict = {}
    raw = analysis_response.strip()
    try:
        plan = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                plan = json.loads(m.group())
            except Exception:
                pass
    if not plan:
        rprint("[red]无法解析 AI 返回的分析结果[/red]")
        rprint(Panel(analysis_response, title="AI 原始回复", border_style="red"))
        raise typer.Exit(1)

    merge_groups: list[dict] = plan.get("merge_groups") or []
    fix_items: list[dict] = plan.get("fix_items") or []
    ok_items: list[dict] = plan.get("ok_items") or []

    # 展示总体方案
    rprint("\n" + "=" * 60)
    rprint("[bold]整合分析结果[/bold]")
    rprint("=" * 60)

    if not merge_groups and not fix_items:
        rprint(f"[green]所有自动化运行良好，无需整合（共 {len(ok_items)} 条）[/green]")
        raise typer.Exit()

    if merge_groups:
        rprint(f"\n[bold cyan]可合并的自动化组（{len(merge_groups)} 组）：[/bold cyan]")
        for i, g in enumerate(merge_groups, 1):
            names = " + ".join(g.get("aliases") or g.get("ids") or [])
            rprint(f"  {i}. {names}")
            rprint(f"     原因：{g.get('reason', '')}")

    if fix_items:
        rprint(f"\n[bold yellow]需要修复的自动化（{len(fix_items)} 条）：[/bold yellow]")
        for i, f_ in enumerate(fix_items, 1):
            rprint(f"  {i}. {f_.get('alias', f_.get('id', ''))}")
            rprint(f"     问题：{f_.get('issue', '')}")

    if ok_items:
        rprint(f"\n[dim]无需变动：{len(ok_items)} 条[/dim]")

    if not typer.confirm("\n是否逐条查看并确认每项变更？", default=True):
        rprint("[yellow]已取消[/yellow]")
        raise typer.Exit()

    # 加载文档（追问修改循环使用）
    docs: dict[str, str] = {}
    fetcher = get_doc_fetcher(config)
    with console.status("加载文档知识..."):
        try:
            docs = fetcher.get_preset_docs(
                ["automation_basic", "automation_trigger", "automation_action"]
            )
        except Exception:
            pass
    system_prompt = build_system_prompt(docs, entities, visible_domains=visible_domains)
    valid_ids = {e["entity_id"] for e in entities} if entities else set()

    def _review_yaml_loop(
        yaml_str: str,
        title: str,
        border: str,
    ) -> dict | None:
        """展示 YAML → 修改循环，返回接受的 dict 或 None（跳过）"""
        parsed_ = yaml.safe_load(yaml_str) if yaml_str else None
        if not yaml_str or not isinstance(parsed_, dict):
            rprint("[yellow]  YAML 无效，自动跳过[/yellow]")
            return None

        while True:
            rprint(Panel(yaml_str, title=title, border_style=border))
            rprint("[dim]直接回车接受；输入修改意见让 AI 重新生成；输入 s 跳过此项[/dim]")
            feedback = input("> ").strip()

            if feedback.lower() == "s":
                return None

            if not feedback:
                try:
                    cfg = unwrap_automation(parsed_)
                    validate_automation(cfg)
                    return cfg
                except Exception as e:
                    rprint(f"[red]YAML 校验失败：{e}，请输入修改意见[/red]")
                    continue

            modify_msg = f"""请修改以下 Home Assistant 自动化配置：

当前配置：
```yaml
{yaml_str}
```

修改要求：{feedback}

请输出修改后的完整 YAML 配置。"""
            with console.status("AI 修改中..."):
                try:
                    resp = llm.chat_with_retry(
                        messages=[{"role": "user", "content": modify_msg}],
                        system=system_prompt,
                    )
                except Exception as e:
                    rprint(f"[red]LLM 调用失败：{e}[/red]")
                    continue
            yaml_str = extract_yaml_from_text(resp)
            parsed_ = yaml.safe_load(yaml_str)
            if not isinstance(parsed_, dict):
                rprint("[yellow]AI 未能生成 YAML，请重新描述修改意见[/yellow]")

    # 逐条确认合并组
    confirmed_merges: list[dict] = []
    for i, group in enumerate(merge_groups, 1):
        names = " + ".join(group.get("aliases") or group.get("ids") or [])
        rprint(f"\n[bold]合并方案 {i}/{len(merge_groups)}：{names}[/bold]")
        rprint(f"原因：{group.get('reason', '')}")
        cfg = _review_yaml_loop(
            group.get("merged_yaml", ""), title="合并后的 YAML", border="green"
        )
        if cfg is not None:
            group["_parsed"] = cfg
            confirmed_merges.append(group)
        else:
            rprint("[dim]  已跳过此合并组[/dim]")

    # 逐条确认修复项
    confirmed_fixes: list[dict] = []
    for i, item in enumerate(fix_items, 1):
        rprint(f"\n[bold]修复方案 {i}/{len(fix_items)}：{item.get('alias', item.get('id', ''))}[/bold]")
        rprint(f"问题：{item.get('issue', '')}")
        cfg = _review_yaml_loop(
            item.get("fixed_yaml", ""), title="修复后的 YAML", border="yellow"
        )
        if cfg is not None:
            item["_parsed"] = cfg
            confirmed_fixes.append(item)
        else:
            rprint("[dim]  已跳过此修复项[/dim]")

    if not confirmed_merges and not confirmed_fixes:
        rprint("[yellow]没有确认任何变更，退出[/yellow]")
        raise typer.Exit()

    # 执行计划摘要
    rprint("\n[bold]执行计划摘要：[/bold]")
    if confirmed_merges:
        rprint(f"  合并：{len(confirmed_merges)} 组")
    if confirmed_fixes:
        rprint(f"  修复：{len(confirmed_fixes)} 条")

    if dry_run:
        rprint("[yellow]--dry-run 模式，不写入 HA[/yellow]")
        raise typer.Exit()

    if not typer.confirm("\n确认执行以上所有变更？", default=False):
        rprint("[yellow]已取消[/yellow]")
        raise typer.Exit()

    # 整体备份
    backup_manager = get_backup_manager(config)
    with console.status("备份中..."):
        try:
            existing = automation_manager.list_automations()
            backup_file = backup_manager.create_backup(existing)
            rprint(f"[dim]备份已保存：{backup_file}[/dim]")
        except Exception as e:
            rprint(f"[yellow]备份失败（{e}），是否仍要继续？[/yellow]")
            if not typer.confirm("继续？", default=False):
                raise typer.Exit()

    # 执行合并（先 create 成功再 delete）
    for group in confirmed_merges:
        ids_to_delete: list[str] = group.get("ids") or []
        merged_config = normalize_automation(group["_parsed"])
        with console.status("创建合并后的自动化..."):
            try:
                new_id = automation_manager.create_automation(merged_config)
                rprint(f"[green]  合并创建成功（ID: {new_id}）[/green]")
            except Exception as e:
                rprint(f"[red]  合并创建失败：{e}，跳过删除旧自动化[/red]")
                continue
        for old_id in ids_to_delete:
            try:
                automation_manager.delete_automation(old_id)
                rprint(f"[dim]  已删除旧自动化：{old_id}[/dim]")
            except Exception as e:
                rprint(f"[yellow]  删除旧自动化失败（{old_id}）：{e}[/yellow]")

    # 执行修复
    for item in confirmed_fixes:
        fix_id: str = item.get("id", "")
        fixed_config = normalize_automation(item["_parsed"])
        with console.status(f"更新 {item.get('alias', fix_id)}..."):
            try:
                automation_manager.update_automation(fix_id, fixed_config)
                rprint(f"[green]  {item.get('alias', fix_id)} 修复成功[/green]")
            except Exception as e:
                rprint(f"[red]  修复失败（{fix_id}）：{e}[/red]")

    # Reload
    with console.status("重载自动化配置..."):
        automation_manager.reload_automations()

    rprint("[green]整合完成！[/green]")


# ------------------------------------------------------------------
# 命令：refresh-docs
# ------------------------------------------------------------------

@app.command("refresh-docs")
def refresh_docs(
    list_cache: Annotated[bool, typer.Option("--list", "-l", help="仅列出缓存状态")] = False,
):
    """刷新 HA 官方文档缓存"""
    config = get_config()
    fetcher = get_doc_fetcher(config)

    if list_cache:
        cached = fetcher.list_cached()
        if not cached:
            rprint("[yellow]暂无缓存[/yellow]")
            return
        table = Table(title="文档缓存状态", show_lines=False)
        table.add_column("URL/Key", style="cyan", no_wrap=True)
        table.add_column("大小(字符)", justify="right")
        table.add_column("缓存时间(h)", justify="right")
        table.add_column("状态", style="green")
        for c in cached:
            status = "[red]已过期[/red]" if c["expired"] else "[green]有效[/green]"
            table.add_row(c["key"], str(c["chars"]), str(c["age_hours"]), status)
        console.print(table)
        return

    rprint(f"[bold]将刷新以下 {len(HA_DOC_URLS)} 个文档：[/bold]")
    for key, url in HA_DOC_URLS.items():
        rprint(f"  - {key}: {url}")

    with console.status("抓取文档中..."):
        succeeded = fetcher.refresh_all_docs()

    rprint(f"[green]成功刷新 {len(succeeded)}/{len(HA_DOC_URLS)} 个文档[/green]")
    failed = set(HA_DOC_URLS.keys()) - set(succeeded)
    if failed:
        rprint(f"[yellow]失败：{', '.join(failed)}[/yellow]")


# ------------------------------------------------------------------
# backup 子命令
# ------------------------------------------------------------------

@backup_app.command("list")
def backup_list():
    """列出所有备份"""
    config = get_config()
    manager = get_backup_manager(config)
    backups = manager.list_backups()

    if not backups:
        rprint("[yellow]暂无备份[/yellow]")
        return

    table = Table(title="备份列表", show_lines=False)
    table.add_column("文件名", style="cyan")
    table.add_column("时间", style="white")
    table.add_column("条数", justify="right", style="green")
    table.add_column("大小(KB)", justify="right", style="dim")
    for b in backups:
        table.add_row(b["name"], b["mtime"], str(b["count"]), str(b["size_kb"]))
    console.print(table)


@backup_app.command("create")
def backup_create():
    """立即备份当前所有自动化"""
    config = get_config()
    automation_manager = get_automation_manager(config)
    backup_manager = get_backup_manager(config)

    with console.status("获取自动化并备份..."):
        try:
            automations = automation_manager.list_automations()
            # 获取完整配置
            full = [automation_manager.get_automation(a["id"]) for a in automations]
            backup_file = backup_manager.create_backup(full)
        except Exception as e:
            rprint(f"[red]备份失败：{e}[/red]")
            raise typer.Exit(1)

    rprint(f"[green]备份成功：{backup_file}（共 {len(full)} 条自动化）[/green]")


@backup_app.command("restore")
def backup_restore(
    file: Annotated[Optional[str], typer.Option("--file", "-f", help="备份文件路径")] = None,
):
    """从备份恢复自动化（覆盖式写入）"""
    config = get_config()
    backup_manager = get_backup_manager(config)

    if not file:
        backups = backup_manager.list_backups()
        if not backups:
            rprint("[yellow]暂无备份[/yellow]")
            raise typer.Exit()
        rprint("[bold]可用备份：[/bold]")
        for i, b in enumerate(backups, 1):
            rprint(f"  {i}. {b['name']}  ({b['mtime']}, {b['count']} 条)")
        idx_str = typer.prompt("选择备份序号")
        try:
            file = backups[int(idx_str) - 1]["file"]
        except (ValueError, IndexError):
            rprint("[red]无效序号[/red]")
            raise typer.Exit(1)

    automations = backup_manager.restore_backup(file)
    rprint(f"\n[bold]将恢复 {len(automations)} 条自动化[/bold]")
    rprint(f"[yellow]警告：此操作将逐条更新 HA 中的自动化，请确认！[/yellow]")

    if not typer.confirm("确认恢复？", default=False):
        rprint("[yellow]已取消[/yellow]")
        raise typer.Exit()

    automation_manager = get_automation_manager(config)
    success = 0
    with console.status("恢复中..."):
        for a in automations:
            try:
                aid = a.get("id", "")
                if aid:
                    automation_manager.update_automation(aid, a)
                else:
                    automation_manager.create_automation(a)
                success += 1
            except Exception as e:
                rprint(f"[yellow]  跳过 {a.get('alias', '?')}：{e}[/yellow]")

        automation_manager.reload_automations()

    rprint(f"[green]恢复完成：{success}/{len(automations)} 条成功[/green]")


# ------------------------------------------------------------------
# 主入口
# ------------------------------------------------------------------

if __name__ == "__main__":
    app()
