"""
LLM 服务层 — 三大模式的异步核心逻辑。

从 cli_tool/main.py 提取，改为 async 函数，通过 log_callback 推送进度日志。
所有函数接受 hass 和 config_entry，通过 HABridge 访问 HA，通过 LLM Client 调用 LLM。
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Callable

import yaml
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..backup.manager import BackupManager
from ..const import (
    CONF_AREA_FILTER,
    CONF_EXTRA_VISIBLE_DOMAINS,
    CONF_HIDDEN_DOMAINS,
    CONF_INTEGRATION_FILTER,
    CONF_LABEL_FILTER,
    CONF_LLM_API_KEY,
    CONF_LLM_BASE_URL,
    CONF_LLM_MAX_TOKENS,
    CONF_LLM_MODEL,
    CONF_LLM_PROVIDER,
    CONF_LLM_TEMPERATURE,
    CONF_LOG_PROMPT,
    CONF_USE_DOCS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DOMAIN,
)
from ..knowledge.fetcher import DocFetcher
from ..knowledge.prompts import DEFAULT_VISIBLE_DOMAINS
from ..knowledge.prompts import (
    build_consolidate_prompt,
    build_feasibility_prompt,
    build_optimize_analysis_prompt,
    build_optimize_yaml_prompt,
    build_system_prompt,
)
from ..llm_client import create_client
from .automations_utils import (
    extract_action_services,
    extract_entity_ids,
    normalize_automation,
    parse_automations_from_text,
    unwrap_automation,
    validate_automation,
)
from .ha_bridge import HABridge

LogCallback = Callable[[str], None]


def _get_llm_client(config_entry: ConfigEntry):
    """从 config_entry 构建 LLM client 配置并创建实例（只读 entry.options）"""
    opts = config_entry.options
    api_key = opts.get(CONF_LLM_API_KEY, "").strip()
    if not api_key:
        raise RuntimeError("请先在面板配置页设置 LLM API Key")
    llm_config = {
        "provider": opts.get(CONF_LLM_PROVIDER, "openai_compatible"),
        "api_key": api_key,
        "model": opts.get(CONF_LLM_MODEL, "gpt-4o"),
        "max_tokens": opts.get(CONF_LLM_MAX_TOKENS, DEFAULT_MAX_TOKENS),
        "temperature": opts.get(CONF_LLM_TEMPERATURE, DEFAULT_TEMPERATURE),
    }
    base_url = opts.get(CONF_LLM_BASE_URL, "").strip()
    if base_url:
        llm_config["base_url"] = base_url
    return create_client(llm_config)


def _get_visible_domains(config_entry: ConfigEntry) -> set[str]:
    """从 config_entry 计算最终可见 domain 集合"""
    opts = config_entry.options
    extra_str = opts.get(CONF_EXTRA_VISIBLE_DOMAINS, "") or ""
    hidden_str = opts.get(CONF_HIDDEN_DOMAINS, "") or ""
    extra = {d.strip() for d in extra_str.split(",") if d.strip()}
    hidden = {d.strip() for d in hidden_str.split(",") if d.strip()}
    return (DEFAULT_VISIBLE_DOMAINS | extra) - hidden


def _get_entity_filters(config_entry: ConfigEntry) -> dict:
    """从 config_entry 获取实体过滤参数"""
    opts = config_entry.options
    return {
        "area_filter": opts.get(CONF_AREA_FILTER) or None,
        "label_filter": opts.get(CONF_LABEL_FILTER) or None,
        "integration_filter": opts.get(CONF_INTEGRATION_FILTER) or None,
    }


def _maybe_log_prompt(config_entry: ConfigEntry, log_callback: LogCallback, prompt: str) -> None:
    """若启用了 log_prompt 选项，向前端推送 [PROMPT] 日志条目"""
    if config_entry.options.get(CONF_LOG_PROMPT):
        truncated = prompt[:3000] + ("...(截断)" if len(prompt) > 3000 else "")
        log_callback(f"[PROMPT] {truncated}")


def _should_use_docs(config_entry: ConfigEntry) -> bool:
    """从 options 读取是否启用知识库文档（默认 True）"""
    return bool(config_entry.options.get(CONF_USE_DOCS, True))


def _load_docs_with_status(
    fetcher: DocFetcher,
    keys: list[str],
) -> tuple[dict[str, str], bool, list[str]]:
    """同步加载文档，同时返回缓存状态（在 executor 中调用，不调用 log_callback）。
    返回 (docs, all_cached, missing_keys)"""
    cached_keys = {c["key"] for c in fetcher.list_cached() if not c["expired"]}
    needed = set(keys)
    missing = sorted(needed - cached_keys)
    docs = fetcher.get_preset_docs(keys)
    return docs, len(missing) == 0, missing


def _extract_json(text: str) -> dict | None:
    """从 LLM 回复中尝试提取 JSON 对象（容错处理 markdown 包裹和截断）"""
    text = text.strip()

    # 1. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 从 markdown 代码块中提取
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 找到 JSON 对象起始位置
    start = text.find("{")
    if start < 0:
        return None
    json_text = text[start:]

    # 4. 尝试常见截断后缀（针对聚合 JSON 的嵌套结构）
    for suffix in ('"}]}]}', '"]}]}', '"}]}', '"]}', ']}', '}'):
        try:
            return json.loads(json_text + suffix)
        except json.JSONDecodeError:
            pass

    # 5. 利用 JSONDecodeError.pos 定位截断点，在其前 300 字符内找最后完整项
    try:
        json.loads(json_text)
    except json.JSONDecodeError as e:
        err_pos = min(e.pos, len(json_text))
        scan_start = max(0, err_pos - 300)
        for i in range(err_pos, scan_start, -1):
            if json_text[i - 1] in ("}", "]"):
                partial = json_text[:i]
                opens = partial.count("{") - partial.count("}")
                arr_opens = partial.count("[") - partial.count("]")
                if opens < 0 or arr_opens < 0:
                    continue
                closer = "}" * opens
                try:
                    return json.loads(partial + closer)
                except json.JSONDecodeError:
                    pass

    return None


def _get_doc_fetcher(hass: HomeAssistant) -> DocFetcher:
    """创建文档抓取器，缓存目录使用 HA 配置路径"""
    cache_dir = hass.config.path("custom_components", "ha_llm_automation", "doc_cache")
    return DocFetcher(cache_dir=cache_dir)


def _get_backup_manager(hass: HomeAssistant) -> BackupManager:
    """创建备份管理器，目录使用 HA 配置路径"""
    backup_dir = hass.config.path("custom_components", "ha_llm_automation", "backup")
    return BackupManager(backup_dir=backup_dir)


def _get_bridge(hass: HomeAssistant, config_entry: ConfigEntry) -> HABridge:
    """从 hass.data 获取 HABridge 实例"""
    return hass.data[DOMAIN][config_entry.entry_id]["bridge"]


async def _run_llm_async(hass: HomeAssistant, llm_client, messages: list[dict], system: str) -> str:
    """在线程池中运行同步 LLM 调用，避免阻塞事件循环"""
    return await hass.async_add_executor_job(
        lambda: llm_client.chat_with_retry(messages, system)
    )


# ==================================================================
# 创建模式
# ==================================================================

async def run_create(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    requirement: str,
    log_callback: LogCallback,
    use_docs: bool | None = None,  # None = 读取 entry.options
) -> dict:
    """
    创建自动化：可行性检查 + YAML 生成。
    返回 {"automations": [...], "valid_ids": set, "system_prompt": str}
    automations 每项含 {"parsed": dict, "yaml_str": str, "warnings": list}
    """
    bridge = _get_bridge(hass, config_entry)
    llm = _get_llm_async_wrapper(hass, _get_llm_client(config_entry))
    visible_domains = _get_visible_domains(config_entry)
    entity_filters = _get_entity_filters(config_entry)

    log_callback("正在获取实体列表...")
    try:
        entities = await bridge.get_entities(**entity_filters)
        log_callback(f"已获取 {len(entities)} 个实体")
    except Exception as e:
        log_callback(f"获取实体失败（{e}），继续生成")
        entities = []

    docs: dict[str, str] = {}
    effective_use_docs = use_docs if use_docs is not None else _should_use_docs(config_entry)
    if effective_use_docs:
        try:
            fetcher = _get_doc_fetcher(hass)
            _keys = ["automation_basic", "automation_trigger", "automation_action"]
            docs, all_cached, missing = await hass.async_add_executor_job(
                lambda: _load_docs_with_status(fetcher, _keys)
            )
            if all_cached:
                log_callback("读取文档缓存（无需联网）")
            else:
                log_callback(f"加载 HA 文档知识（{', '.join(missing)} 需从网络更新）...")
            log_callback("文档加载完成")
        except Exception as e:
            log_callback(f"文档加载失败（{e}），跳过")

    # Step 1: 可行性检查
    step1_entities: list[str] = []
    if entities:
        log_callback("Step 1/2 — 分析需求可行性...")
        feasibility_prompt = build_feasibility_prompt(entities, visible_domains=visible_domains)
        _maybe_log_prompt(config_entry, log_callback, feasibility_prompt)
        try:
            resp = await llm(
                messages=[{"role": "user", "content": requirement}],
                system=feasibility_prompt,
            )
            feasibility = json.loads(resp.strip())
        except json.JSONDecodeError:
            log_callback("可行性检查返回非 JSON，跳过 Step 1")
            feasibility = {"feasible": True, "entities": [], "reason": ""}
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败（Step 1）：{e}") from e

        if not feasibility.get("feasible", True):
            raise RuntimeError(f"需求不可行：{feasibility.get('reason', '（无说明）')}")

        step1_entities = feasibility.get("entities") or []
        reason = feasibility.get("reason", "")
        if reason:
            log_callback(f"Step 1 分析：{reason}")

    # Step 2: YAML 生成
    if step1_entities:
        step1_set = set(step1_entities)
        filtered_entities = [e for e in entities if e["entity_id"] in step1_set] or entities
    else:
        filtered_entities = entities

    system_prompt = build_system_prompt(docs, filtered_entities, visible_domains=visible_domains)
    log_callback("Step 2/2 — AI 生成 YAML...")
    _maybe_log_prompt(config_entry, log_callback, system_prompt)
    try:
        response = await llm(
            messages=[{"role": "user", "content": requirement}],
            system=system_prompt,
        )
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败（Step 2）：{e}") from e

    automations_list = parse_automations_from_text(response)
    if not automations_list:
        raise RuntimeError(f"AI 未能生成有效的自动化 YAML。原始回复：{response[:500]}")

    valid_ids = {e["entity_id"] for e in entities} if entities else set()

    # 逐条校验
    result_items = []
    for item in automations_list:
        yaml_str = yaml.dump(item, allow_unicode=True, sort_keys=False, default_flow_style=False)
        warnings: list[str] = []
        cfg = None
        try:
            cfg = unwrap_automation(item)
            validate_automation(cfg)
        except Exception as e:
            warnings.append(f"校验失败：{e}")
            cfg = None
        if cfg and valid_ids:
            invalid = extract_entity_ids(cfg) - valid_ids
            if invalid:
                warnings.append(f"幻觉实体：{', '.join(sorted(invalid))}")
            bad_actions = extract_action_services(cfg) & valid_ids
            if bad_actions:
                warnings.append(f"action 字段填写了实体 ID：{', '.join(sorted(bad_actions))}")
                cfg = None
        result_items.append({"parsed": cfg, "yaml_str": yaml_str, "warnings": warnings})

    log_callback(f"生成完成，共 {len(result_items)} 条自动化")
    return {
        "automations": result_items,
        "valid_ids": list(valid_ids),
        "system_prompt": system_prompt,
    }


async def run_create_refine(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    current_yaml: str,
    feedback: str,
    system_prompt: str,
    log_callback: LogCallback,
) -> dict:
    """
    创建模式追问修改：基于 feedback 重新生成 YAML。
    返回 {"parsed": dict | None, "yaml_str": str, "warnings": list}
    """
    llm = _get_llm_async_wrapper(hass, _get_llm_client(config_entry))
    bridge = _get_bridge(hass, config_entry)
    entity_filters = _get_entity_filters(config_entry)

    try:
        entities = await bridge.get_entities(**entity_filters)
        valid_ids = {e["entity_id"] for e in entities}
    except Exception:
        valid_ids = set()

    modify_msg = (
        f"请修改以下 Home Assistant 自动化配置：\n\n"
        f"当前配置：\n```yaml\n{current_yaml}\n```\n\n"
        f"修改要求：{feedback}\n\n请输出修改后的完整 YAML 配置。"
    )
    log_callback("AI 修改中...")
    try:
        response = await llm(
            messages=[{"role": "user", "content": modify_msg}],
            system=system_prompt,
        )
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败：{e}") from e

    new_list = parse_automations_from_text(response)
    if not new_list:
        raise RuntimeError(f"AI 未能生成 YAML。回复：{response[:500]}")

    item = new_list[0]
    yaml_str = yaml.dump(item, allow_unicode=True, sort_keys=False, default_flow_style=False)
    warnings: list[str] = []
    cfg = None
    try:
        cfg = unwrap_automation(item)
        validate_automation(cfg)
    except Exception as e:
        warnings.append(f"校验失败：{e}")
    if cfg and valid_ids:
        invalid = extract_entity_ids(cfg) - valid_ids
        if invalid:
            warnings.append(f"幻觉实体：{', '.join(sorted(invalid))}")
        bad_actions = extract_action_services(cfg) & valid_ids
        if bad_actions:
            warnings.append(f"action 字段填写了实体 ID：{', '.join(sorted(bad_actions))}")
            cfg = None

    return {"parsed": cfg, "yaml_str": yaml_str, "warnings": warnings}


async def run_create_save(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    parsed_list: list[dict],
    log_callback: LogCallback,
) -> list[dict]:
    """
    批量保存已确认的自动化列表。
    parsed_list: list of normalized config dicts
    返回 list of {"alias": str, "id": str | None, "error": str | None}
    """
    bridge = _get_bridge(hass, config_entry)
    backup_mgr = _get_backup_manager(hass)

    log_callback("备份现有自动化...")
    try:
        existing = await _get_full_automations_for_backup(bridge)
        backup_path = backup_mgr.create_backup(existing)
        log_callback(f"备份已保存：{backup_path}")
    except Exception as e:
        log_callback(f"备份失败（{e}），继续写入")

    results = []
    for i, cfg in enumerate(parsed_list, 1):
        alias = cfg.get("alias", f"automation_{i}")
        normalized = normalize_automation(cfg)
        log_callback(f"[{i}/{len(parsed_list)}] 写入 {alias}...")
        try:
            new_id = await bridge.create_automation(normalized)
            results.append({"alias": alias, "id": new_id, "error": None})
            log_callback(f"  {alias} → 成功（ID: {new_id}）")
        except Exception as e:
            results.append({"alias": alias, "id": None, "error": str(e)})
            log_callback(f"  {alias} → 失败：{e}")

    await bridge.reload_automations()
    return results


# ==================================================================
# 优化模式
# ==================================================================

async def run_optimize_analyze(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    automation_id: str,
    log_callback: LogCallback,
    user_direction: str = "",
) -> dict:
    """
    优化模式 Step 1：获取配置 + 分析意图。
    返回 {"automation_yaml": str, "analysis": dict, "automation_id": str}
    """
    bridge = _get_bridge(hass, config_entry)
    llm = _get_llm_async_wrapper(hass, _get_llm_client(config_entry))
    visible_domains = _get_visible_domains(config_entry)
    entity_filters = _get_entity_filters(config_entry)

    log_callback("获取自动化配置...")
    try:
        config = await bridge.get_automation_config(automation_id)
    except Exception as e:
        raise RuntimeError(f"无法获取自动化配置：{e}") from e

    automation_yaml = bridge.to_yaml(config)

    log_callback("获取实体列表...")
    try:
        entities = await bridge.get_entities(**entity_filters)
    except Exception:
        entities = []

    log_callback("Step 1/2 — LLM 分析意图...")
    analysis_prompt = build_optimize_analysis_prompt(
        automation_yaml, entities,
        visible_domains=visible_domains,
        user_direction=user_direction,
    )
    _maybe_log_prompt(config_entry, log_callback, analysis_prompt)
    try:
        resp = await llm(
            messages=[{"role": "user", "content": "请分析这条自动化并返回 JSON 格式的分析结果。"}],
            system=analysis_prompt,
        )
        analysis = json.loads(resp.strip())
    except json.JSONDecodeError:
        log_callback("分析返回非 JSON，使用空分析")
        analysis = {"intent": resp[:200], "related_entities": [], "issues": [], "suggestions": []}
    except Exception as e:
        raise RuntimeError(f"LLM 分析失败：{e}") from e

    log_callback("分析完成")
    return {
        "automation_id": automation_id,
        "automation_yaml": automation_yaml,
        "analysis": analysis,
    }


async def run_optimize_generate(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    automation_yaml: str,
    analysis: dict,
    log_callback: LogCallback,
    user_direction: str = "",
) -> dict:
    """
    优化模式 Step 2：生成优化后 YAML。
    返回 {"yaml_str": str, "parsed": dict | None, "warnings": list, "system_prompt": str}
    """
    bridge = _get_bridge(hass, config_entry)
    llm = _get_llm_async_wrapper(hass, _get_llm_client(config_entry))
    visible_domains = _get_visible_domains(config_entry)
    entity_filters = _get_entity_filters(config_entry)

    docs: dict[str, str] = {}
    if _should_use_docs(config_entry):
        try:
            fetcher = _get_doc_fetcher(hass)
            _keys = ["automation_basic", "automation_trigger", "automation_action"]
            docs, all_cached, missing = await hass.async_add_executor_job(
                lambda: _load_docs_with_status(fetcher, _keys)
            )
            if all_cached:
                log_callback("读取文档缓存（无需联网）")
            else:
                log_callback(f"加载 HA 文档知识（{', '.join(missing)} 需从网络更新）...")
            log_callback("文档加载完成")
        except Exception as e:
            log_callback(f"文档加载失败（{e}），跳过")

    log_callback("获取实体列表...")
    try:
        entities = await bridge.get_entities(**entity_filters)
        valid_ids = {e["entity_id"] for e in entities}
    except Exception:
        entities = []
        valid_ids = set()

    system_prompt = build_optimize_yaml_prompt(
        automation_yaml, analysis, entities, docs, visible_domains=visible_domains
    )
    user_msg = "请生成优化后的完整自动化 YAML 配置。"
    if user_direction.strip():
        user_msg += f"\n\n用户指定的优化方向：{user_direction}"

    log_callback("Step 2/2 — 生成优化 YAML...")
    _maybe_log_prompt(config_entry, log_callback, system_prompt)
    try:
        response = await llm(
            messages=[{"role": "user", "content": user_msg}],
            system=system_prompt,
        )
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败：{e}") from e

    new_list = parse_automations_from_text(response)
    if not new_list:
        raise RuntimeError(f"AI 未能生成 YAML。回复：{response[:500]}")

    item = new_list[0]
    yaml_str = yaml.dump(item, allow_unicode=True, sort_keys=False, default_flow_style=False)
    warnings: list[str] = []
    cfg = None
    try:
        cfg = unwrap_automation(item)
        validate_automation(cfg)
    except Exception as e:
        warnings.append(f"校验失败：{e}")
    if cfg and valid_ids:
        invalid = extract_entity_ids(cfg) - valid_ids
        if invalid:
            warnings.append(f"幻觉实体：{', '.join(sorted(invalid))}")

    log_callback("优化 YAML 生成完成")
    return {"yaml_str": yaml_str, "parsed": cfg, "warnings": warnings, "system_prompt": system_prompt}


async def run_optimize_refine(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    current_yaml: str,
    feedback: str,
    system_prompt: str,
    log_callback: LogCallback,
) -> dict:
    """优化模式追问修改（与 create_refine 共用逻辑）"""
    return await run_create_refine(hass, config_entry, current_yaml, feedback, system_prompt, log_callback)


async def run_optimize_save(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    automation_id: str,
    parsed: dict,
    log_callback: LogCallback,
) -> bool:
    """保存优化结果（POST 更新到 HA）"""
    bridge = _get_bridge(hass, config_entry)
    backup_mgr = _get_backup_manager(hass)

    log_callback("备份现有自动化...")
    try:
        existing = await _get_full_automations_for_backup(bridge)
        backup_path = backup_mgr.create_backup(existing)
        log_callback(f"备份已保存：{backup_path}")
    except Exception as e:
        log_callback(f"备份失败（{e}），继续写入")

    normalized = normalize_automation(parsed)
    log_callback("写入 HA...")
    await bridge.update_automation(automation_id, normalized)
    await bridge.reload_automations()
    log_callback("优化保存成功")
    return True


# ==================================================================
# 聚合模式
# ==================================================================

async def run_consolidate_analyze(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    log_callback: LogCallback,
    automation_ids: list[str] | None = None,
) -> dict:
    """
    聚合模式：获取全部自动化 + LLM 分析。
    automation_ids: 若传入，则只分析指定 ID 的自动化；None 表示分析全部。
    返回 {"merge_groups": [...], "fix_items": [...], "ok_items": [...], "automations_data": [...]}
    """
    bridge = _get_bridge(hass, config_entry)
    llm = _get_llm_async_wrapper(hass, _get_llm_client(config_entry))
    visible_domains = _get_visible_domains(config_entry)

    log_callback("获取自动化列表...")
    all_automations = await bridge.list_automations()

    log_callback(f"批量获取 {len(all_automations)} 条自动化完整配置...")
    automations_data: list[dict] = []
    for a in all_automations:
        aid = a.get("id", "")
        if not aid or aid == "new":
            continue
        try:
            config = await bridge.get_automation_config(aid)
            yaml_str = bridge.to_yaml(config)
            automations_data.append({
                "id": aid,
                "alias": a.get("alias", aid),
                "yaml_str": yaml_str,
                "config": config,
            })
        except Exception:
            log_callback(f"  跳过 {a.get('alias', aid)}（无法获取配置）")

    # 按用户预选的 ID 过滤
    if automation_ids is not None:
        id_set = set(automation_ids)
        automations_data = [a for a in automations_data if a["id"] in id_set]

    if not automations_data:
        raise RuntimeError("没有可分析的自动化（选定的自动化均无法通过 API 获取完整配置）")

    log_callback(f"获取到 {len(automations_data)} 条可分析的自动化，开始 LLM 分析...")

    entity_filters = _get_entity_filters(config_entry)
    log_callback("获取实体列表...")
    try:
        entities = await bridge.get_entities(**entity_filters)
    except Exception:
        entities = []

    prompt_data = [{"id": d["id"], "alias": d["alias"], "yaml_str": d["yaml_str"]} for d in automations_data]
    consolidate_prompt = build_consolidate_prompt(prompt_data, entities, visible_domains=visible_domains)
    _maybe_log_prompt(config_entry, log_callback, consolidate_prompt)
    try:
        resp = await llm(
            messages=[{"role": "user", "content": "请分析以上自动化并返回 JSON 格式的整合方案。"}],
            system=consolidate_prompt,
        )
    except Exception as e:
        raise RuntimeError(f"LLM 分析失败：{e}") from e

    plan = _extract_json(resp)
    if plan is None:
        raise RuntimeError(f"LLM 返回了非 JSON 格式：{resp[:300]}")
    if not isinstance(plan, dict):
        raise RuntimeError(f"LLM 返回了非对象 JSON：{resp[:300]}")
    # 容错：确保必要的键存在
    plan.setdefault("merge_groups", [])
    plan.setdefault("fix_items", [])
    plan.setdefault("ok_items", [])

    log_callback(
        f"分析完成：{len(plan.get('merge_groups', []))} 组合并，"
        f"{len(plan.get('fix_items', []))} 项修复，"
        f"{len(plan.get('ok_items', []))} 项无需修改"
    )

    return {
        "merge_groups": plan.get("merge_groups", []),
        "fix_items": plan.get("fix_items", []),
        "ok_items": plan.get("ok_items", []),
        "automations_data": automations_data,
    }


async def run_consolidate_refine(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    item_type: str,
    item_id: str,
    current_yaml: str,
    feedback: str,
    log_callback: LogCallback,
) -> str:
    """
    聚合模式追问修改单个条目（合并/修复项）。
    返回修改后的 yaml_str。
    """
    bridge = _get_bridge(hass, config_entry)
    llm = _get_llm_async_wrapper(hass, _get_llm_client(config_entry))
    visible_domains = _get_visible_domains(config_entry)
    entity_filters = _get_entity_filters(config_entry)

    try:
        entities = await bridge.get_entities(**entity_filters)
    except Exception:
        entities = []

    docs: dict[str, str] = {}
    if _should_use_docs(config_entry):
        try:
            fetcher = _get_doc_fetcher(hass)
            _keys = ["automation_basic", "automation_trigger"]
            docs, _, _ = await hass.async_add_executor_job(
                lambda: _load_docs_with_status(fetcher, _keys)
            )
        except Exception:
            pass

    system_prompt = build_system_prompt(docs, entities, visible_domains=visible_domains)
    modify_msg = (
        f"请修改以下 Home Assistant 自动化配置：\n\n"
        f"当前配置：\n```yaml\n{current_yaml}\n```\n\n"
        f"修改要求：{feedback}\n\n请输出修改后的完整 YAML 配置。"
    )
    log_callback("AI 修改中...")
    try:
        response = await llm(
            messages=[{"role": "user", "content": modify_msg}],
            system=system_prompt,
        )
    except Exception as e:
        raise RuntimeError(f"LLM 调用失败：{e}") from e

    new_list = parse_automations_from_text(response)
    if not new_list:
        raise RuntimeError(f"AI 未能生成 YAML。回复：{response[:500]}")

    item = new_list[0]
    return yaml.dump(item, allow_unicode=True, sort_keys=False, default_flow_style=False)


async def run_consolidate_execute(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    approved_merges: list[dict],
    approved_fixes: list[dict],
    log_callback: LogCallback,
) -> dict:
    """
    执行已批准的聚合方案。
    approved_merges: list of {ids: [...], merged_yaml: str}
    approved_fixes: list of {id: str, fixed_yaml: str}
    返回 {"success": int, "failed": int, "details": [...]}
    """
    bridge = _get_bridge(hass, config_entry)
    backup_mgr = _get_backup_manager(hass)

    log_callback("备份现有自动化...")
    try:
        existing = await _get_full_automations_for_backup(bridge)
        backup_path = backup_mgr.create_backup(existing)
        log_callback(f"备份已保存：{backup_path}")
    except Exception as e:
        log_callback(f"备份失败（{e}），继续执行")

    success, failed = 0, 0
    details: list[dict] = []

    # 执行合并
    for group in approved_merges:
        old_ids = group.get("ids", [])
        merged_yaml_str = group.get("merged_yaml", "")
        aliases = group.get("aliases", old_ids)
        label = f"合并：{' + '.join(str(a) for a in aliases)}"
        try:
            parsed_list = parse_automations_from_text(f"```yaml\n{merged_yaml_str}\n```")
            if not parsed_list:
                raise ValueError("无法解析 merged_yaml")
            cfg = normalize_automation(parsed_list[0])
            new_id = await bridge.create_automation(cfg)
            log_callback(f"  {label} → 创建成功（ID: {new_id}）")

            # 删除旧自动化
            for old_id in old_ids:
                try:
                    await bridge.delete_automation(old_id)
                    log_callback(f"    删除旧自动化 {old_id} 成功")
                except Exception as e:
                    log_callback(f"    删除旧自动化 {old_id} 失败：{e}")

            success += 1
            details.append({"type": "merge", "label": label, "error": None})
        except Exception as e:
            # 自动 LLM 修复重试（create 操作）
            fixed = await _llm_fix_and_retry(
                hass, config_entry, merged_yaml_str, str(e), bridge, log_callback,
                write_fn=bridge.create_automation,
            )
            if fixed:
                success += 1
                details.append({"type": "merge", "label": label, "error": None})
            else:
                failed += 1
                details.append({"type": "merge", "label": label, "error": str(e)})
                log_callback(f"  {label} → 失败：{e}")

    # 执行修复
    for fix in approved_fixes:
        aid = fix.get("id", "")
        fixed_yaml_str = fix.get("fixed_yaml", "")
        alias = fix.get("alias", aid)
        label = f"修复：{alias}"
        try:
            parsed_list = parse_automations_from_text(f"```yaml\n{fixed_yaml_str}\n```")
            if not parsed_list:
                raise ValueError("无法解析 fixed_yaml")
            cfg = normalize_automation(parsed_list[0])
            await bridge.update_automation(aid, cfg)
            success += 1
            details.append({"type": "fix", "label": label, "error": None})
            log_callback(f"  {label} → 修复成功")
        except Exception as e:
            # 自动 LLM 修复重试（update 操作）
            async def _update_fn(cfg, _aid=aid):
                await bridge.update_automation(_aid, cfg)
            fixed = await _llm_fix_and_retry(
                hass, config_entry, fixed_yaml_str, str(e), bridge, log_callback,
                write_fn=_update_fn,
            )
            if fixed:
                success += 1
                details.append({"type": "fix", "label": label, "error": None})
            else:
                failed += 1
                details.append({"type": "fix", "label": label, "error": str(e)})
                log_callback(f"  {label} → 失败：{e}")

    await bridge.reload_automations()
    log_callback(f"聚合执行完成：{success} 成功，{failed} 失败")
    return {"success": success, "failed": failed, "details": details}


async def _llm_fix_and_retry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    yaml_str: str,
    ha_error: str,
    bridge: HABridge,
    log_callback: LogCallback,
    write_fn,  # async callable: (cfg: dict) -> None
    max_retries: int = 2,
) -> bool:
    """LLM 自动修复 YAML 并重试写入，最多 max_retries 次。返回是否成功。"""
    llm = _get_llm_async_wrapper(hass, _get_llm_client(config_entry))
    current_yaml = yaml_str
    new_list = []

    for attempt in range(1, max_retries + 1):
        log_callback(f"  自动修复重试 {attempt}/{max_retries}...")
        fix_msg = (
            f"以下 Home Assistant 自动化 YAML 在写入时报错，请修复并返回修正后的完整 YAML：\n\n"
            f"```yaml\n{current_yaml}\n```\n\n"
            f"HA 报错信息：{ha_error}\n\n请只返回修复后的 YAML 代码块，不要其他说明。"
        )
        try:
            resp = await llm(
                messages=[{"role": "user", "content": fix_msg}],
                system="你是 Home Assistant 自动化专家，负责修复 YAML 格式和字段错误。",
            )
            new_list = parse_automations_from_text(resp)
            if not new_list:
                continue
            cfg = normalize_automation(new_list[0])
            await write_fn(cfg)
            return True
        except Exception as e:
            ha_error = str(e)
            if new_list:
                current_yaml = yaml.dump(new_list[0], allow_unicode=True, sort_keys=False)

    return False


# ==================================================================
# 知识库 & 备份
# ==================================================================

async def run_refresh_docs(
    hass: HomeAssistant,
    log_callback: LogCallback,
) -> list[str]:
    """刷新所有 HA 文档缓存，返回成功的 key 列表"""
    fetcher = _get_doc_fetcher(hass)
    log_callback("开始刷新 HA 文档缓存...")
    succeeded = await hass.async_add_executor_job(fetcher.refresh_all_docs)
    log_callback(f"刷新完成：{len(succeeded)} 个文档成功")
    return succeeded


async def get_backups(hass: HomeAssistant) -> list[dict]:
    """获取备份列表"""
    mgr = _get_backup_manager(hass)
    return mgr.list_backups()


async def run_restore_backup(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    backup_path: str,
    log_callback: LogCallback,
) -> bool:
    """从备份恢复所有自动化"""
    bridge = _get_bridge(hass, config_entry)
    mgr = _get_backup_manager(hass)

    log_callback(f"读取备份：{backup_path}")
    automations = mgr.restore_backup(backup_path)
    log_callback(f"备份包含 {len(automations)} 条自动化，开始恢复...")

    success, failed, skipped = 0, 0, 0
    for a in automations:
        # 跳过配置为空的条目（YAML 型自动化备份时只含状态信息，无 triggers/actions）
        if not any(k in a for k in ("triggers", "trigger", "actions", "action")):
            skipped += 1
            log_callback(f"  跳过（{a.get('alias', '?')}）：配置为空，可能是 YAML 型自动化")
            continue
        try:
            cfg = normalize_automation(a)
            await bridge.create_automation(cfg)
            success += 1
        except Exception as e:
            failed += 1
            log_callback(f"  恢复失败（{a.get('alias', '?')}）：{e}")

    await bridge.reload_automations()
    log_callback(f"恢复完成：{success} 成功，{failed} 失败，{skipped} 跳过（空配置）")
    return failed == 0


# ==================================================================
# 辅助
# ==================================================================

async def _get_full_automations_for_backup(bridge) -> list[dict]:
    """
    获取所有存储型自动化的完整配置用于备份。
    逐条调用 get_automation_config，跳过 YAML 型（GET 失败）。
    """
    summaries = await bridge.list_automations()
    full_configs = []
    for a in summaries:
        aid = a.get("id", "")
        if not aid or aid == "new":
            continue
        try:
            cfg = await bridge.get_automation_config(aid)
            full_configs.append(cfg)
        except Exception:
            pass  # YAML 型或不可访问，跳过
    return full_configs


def _get_llm_async_wrapper(hass: HomeAssistant, llm_client):
    """返回一个 async 包装，在 executor 中运行同步 LLM 调用"""
    async def _call(messages: list[dict], system: str = "") -> str:
        return await hass.async_add_executor_job(
            lambda: llm_client.chat_with_retry(messages, system)
        )
    return _call
