# HA 自动化大模型创建工具 — 项目指南

## 项目概述

本项目是一个基于大模型（LLM）的 Home Assistant 自动化创建与管理工具。
目标是通过自然语言描述，自动生成、修改、备份 HA 自动化脚本，最终封装为 HA 集成插件。

**开发阶段：** 三大核心模式均已实现并通过端到端测试（create / optimize / consolidate）；统一交互入口（`python3 main.py`）已上线；最终封装为 HA Custom Component。

---

## 项目结构

```
HA自动化工具/
├── CLAUDE.md                  # 本文件，项目指南
├── config.json                # 本地配置（不提交 git）
├── config.example.json        # 配置模板
├── main.py                    # 主入口 CLI（typer）；无参数时显示模式选择菜单
├── requirements.txt
├── ha_client/
│   ├── __init__.py
│   ├── connection.py          # HAConnection, load_config
│   ├── entities.py            # EntityManager + fetch_registry_data
│   ├── automations.py         # AutomationManager + 工具函数
│   └── ws_client.py           # WebSocket 客户端（区域/实体注册表）
├── llm_client/
│   ├── __init__.py            # create_client() 工厂函数
│   ├── base.py                # BaseLLMClient 抽象基类
│   ├── openai_client.py       # OpenAI / 兼容接口
│   └── anthropic_client.py    # Anthropic Claude 接口
├── knowledge/
│   ├── fetcher.py             # DocFetcher（抓取+缓存，7天TTL）
│   ├── prompts.py             # 所有提示词构建函数（5个）
│   └── cache/                 # 文档本地缓存（已缓存7个HA官方文档）
├── backup/
│   ├── manager.py             # BackupManager
│   └── archives/              # 备份文件存放
└── tests/
```

---

## 一、HA 连接配置

### 配置文件格式（`config.json`）

```json
{
  "ha": {
    "url": "http://homeassistant.local:8123",
    "token": "your_long_lived_access_token",
    "verify_ssl": false,
    "timeout": 30
  },
  "llm": {
    "provider": "openai_compatible",
    "api_key": "sk-...",
    "model": "gpt-4o",
    "base_url": "https://your-api-endpoint/v1",
    "max_tokens": 8192,
    "temperature": 0.3
  },
  "backup": {
    "max_versions": 10,
    "backup_dir": "./backup/archives"
  },
  "knowledge": {
    "cache_dir": "./knowledge/cache",
    "cache_ttl_days": 7
  },
  "domains": {
    "extra_visible": [],
    "hidden": []
  }
}
```

`domains` 字段用于自定义传给 LLM 的实体域白名单：
- `extra_visible`：追加额外 domain（如 `["notify", "remote"]`）
- `hidden`：屏蔽不想展示的 domain（如 `["weather"]`）
- 留空则使用内置默认白名单（见下方）

### 反向代理注意事项

- 若 HA 通过反向代理对外暴露，URL **不要加端口号**（如 `https://xxx.example.com` 而非 `https://xxx.example.com:8123`）
- SSL 证书由代理处理，建议设置 `verify_ssl: false` 避免证书验证问题

### HA Long-Lived Access Token 获取

1. 登录 HA Web UI → 左下角头像 →「个人资料」
2. 滚动到底部「长期访问令牌」→ 创建令牌

---

## 二、实体与设备信息

### API 端点

```
GET /api/states                   # 获取全量实体（已验证可用）
GET /api/states/{entity_id}       # 获取单个实体状态
```

### EntityManager（`ha_client/entities.py`）

- `EntityManager(conn, exclude_ids=set())` — 构造时传入要过滤的实体 ID 集合
- `get_all_entities()` — 带 5 分钟本地缓存，首次 fetch 时一次性过滤 exclude_ids
- `get_entities_by_domain(domain)` / `search_entities(keyword)` — 按域/关键字过滤
- 传给 LLM 的实体摘要按 domain 白名单过滤 attribute，避免超出 token 限制

### fetch_registry_data（`ha_client/entities.py`）

```python
fetch_registry_data(config) -> {"area_map": {...}, "exclude_ids": set()}
```

通过 WebSocket 获取实体注册表，返回：
- `area_map`：`{entity_id: area_name}`，含实体/设备两级区域继承
- `exclude_ids`：需过滤的实体集合
  - `disabled_by` 非 null（禁用实体）
  - `hidden_by` 非 null（隐藏实体，注意 `/api/states` 仍会返回隐藏实体）
  - `entity_category` in `("diagnostic", "config")`（诊断/配置类）

失败时返回空值，不阻断主流程。

### get_entities()（`main.py` 公共 helper）

```python
get_entities(config) -> list[dict]
```

三步合一：fetch_registry_data → EntityManager(exclude_ids) → enrich_entities_with_areas。
所有命令（create / update / list-entities）统一调用此 helper，确保拿到的实体列表是干净的。

### 实体列表格式（prompts._build_entity_section）

- **全局/虚拟类实体**（todo/calendar/timer/input_* 等）在顶部独立展示，不被 150 条上限截断
- **物理实体**按区域分组，含 `domain` 列，LLM 自行判断 trigger/action 用途
- 默认可见 domain 白名单（`DEFAULT_VISIBLE_DOMAINS`）：

```
可控设备：light, switch, climate, cover, fan, media_player, lock, vacuum,
          scene, script, button, select, number
输入辅助：input_boolean, input_select, input_number, input_text
传感器：  sensor, binary_sensor, device_tracker
其他：    todo, calendar, timer, counter, weather, person
```

---

## 三、自动化脚本管理

### ⚠️ 实际可用的 REST API 端点

> 注意：通过反向代理时，部分端点不可用，以下为实测结果。

| 操作 | 端点 | 状态 |
|------|------|------|
| **列出所有自动化** | `GET /api/config/automation/config` | ❌ 404（代理屏蔽）|
| **改用** | `GET /api/states` 过滤 `automation.*` | ✅ |
| 获取单条完整配置 | `GET /api/config/automation/config/{id}` | ⚠️ 仅对「存储型」自动化有效（见下）|
| **创建自动化** | `POST /api/config/automation/config/new` | ✅（有特殊要求，见下）|
| **更新自动化** | `POST /api/config/automation/config/{id}` | ✅（非 PUT）|
| 删除自动化 | `DELETE /api/config/automation/config/{id}` | ✅ |
| 重载配置 | `POST /api/services/automation/reload` | ✅ |

### ⚠️ 「存储型」vs「YAML型」自动化

HA 中存在两类自动化：

| 类型 | 存储位置 | GET 完整配置 | 说明 |
|------|---------|------------|------|
| **存储型** | HA `.storage/` | ✅ | 通过 HA UI 或本工具 REST API 创建 |
| **YAML型** | `automations.yaml` | ❌ 404 | 手动在配置文件中定义 |

`/api/states` 两类都会列出（包含 `attributes.id`），但 GET 完整配置只对存储型有效。
`optimize` 和 `consolidate` 命令启动时自动探测并过滤，只展示可访问的自动化。

#### 辨别方法
- YAML 型：`attributes.restored = true, state = unavailable`（HA 重启后从 state DB 恢复）
- 存储型：`state = on/off`，正常工作

### ⚠️ 创建自动化的三个必要条件

向 `POST /api/config/automation/config/new` 发送的 payload 必须同时满足：

1. **含 `id` 字段**：13 位毫秒时间戳（如 `"1772515732053"`），否则 HA 以为是未保存的草稿
2. **含 `description` 字段**：哪怕是空字符串 `""`，否则 triggers/actions 不被持久化
3. **alias 必须为 ASCII**：HA API 不接受中文字段值（任何字段含中文均返回 500）

`normalize_automation()` 函数自动处理上述三点：
- 中文 alias → pypinyin 转拼音 snake_case（HA 用 alias 做标识符，必须 ASCII）
- description 中文 → **保留**，通过 `ensure_ascii=False` + UTF-8 编码正常发送
- 注入 `id: str(int(time.time() * 1000))`

### HA 2024+ 新版字段名

```yaml
alias: turn_on_light_morning
triggers:           # 不是 trigger:
  - trigger: time   # 不是 platform: time
    at: "07:00:00"
conditions: []      # 不是 condition:
actions:            # 不是 action:
  - action: light.turn_on   # 不是 service:
    target:
      entity_id: light.living_room
mode: single
```

`normalize_automation()` 会自动将旧格式（trigger/action/service）转换为新格式。

### 自动化 ID 说明

- HA 存储的 automation ID 为 13 位毫秒时间戳字符串（如 `"1769504038939"`）
- 通过 REST API 创建的自动化，entity state 的 `attributes.id` 可能显示为 `"new"`（已知 HA 行为），自动化内容本身是正确的

---

## 四、两步 LLM 创建流程

```
get_entities() → 过滤隐藏/禁用/诊断实体 + 注入区域
       ↓
Step 1：可行性检查（build_feasibility_prompt）
  - LLM 语义推断需要哪些实体（触发器 + 动作目标）
  - 返回 JSON: {"feasible": bool, "entities": [...], "reason": "..."}
  - 不可行 → 显示原因，退出
       ↓
Step 2：YAML 生成（build_system_prompt，仅含 Step1 筛出的实体）
  - 生成带 description 字段的完整 YAML
       ↓
交互式修改循环：
  - 展示 YAML，提示"输入修改意见（直接回车接受）"
  - 有意见 → LLM 携带当前 YAML + 修改要求重新生成 → 循环
  - 回车接受 → 校验 → 确认写入
       ↓
normalize → validate → 备份 → create_automation → reload
```

---

## 五、HA 官方文档学习模块

### 已缓存文档（`knowledge/cache/`）

| Key | URL |
|-----|-----|
| automation_basic | https://www.home-assistant.io/docs/automation/ |
| automation_trigger | https://www.home-assistant.io/docs/automation/trigger/ |
| automation_condition | https://www.home-assistant.io/docs/automation/condition/ |
| automation_action | https://www.home-assistant.io/docs/automation/action/ |
| templating | https://www.home-assistant.io/docs/configuration/templating/ |
| scripts | https://www.home-assistant.io/docs/scripts/ |
| service_calls | https://www.home-assistant.io/docs/scripts/service-calls/ |

### 提示词构建（`knowledge/prompts.py`）

- `build_system_prompt(docs, entities, visible_domains)` — create/update Step 2 YAML 生成提示词
- `build_feasibility_prompt(entities, visible_domains)` — create Step 1 可行性检查提示词
- `build_optimize_analysis_prompt(automation_yaml, entities, visible_domains)` — optimize Step 1 分析意图，返回 JSON `{intent, related_entities, issues, suggestions}`
- `build_optimize_yaml_prompt(automation_yaml, analysis, entities, docs, visible_domains)` — optimize Step 2 生成优化 YAML
- `build_consolidate_prompt(automations_data, entities, visible_domains)` — consolidate 批量分析，返回 JSON `{merge_groups, fix_items, ok_items}`
- `DEFAULT_VISIBLE_DOMAINS` — 默认可见域集合（可被 config.domains 覆盖）
- 文档最多 12000 字符，实体最多 150 条（全局实体优先，不受截断影响）

---

## 六、LLM API 接口配置

### 支持的 Provider

| Provider | 说明 |
|----------|------|
| `anthropic` | Anthropic 官方 API |
| `openai` | OpenAI 官方 API |
| `openai_compatible` | 兼容 OpenAI 格式的第三方接口（DeepSeek、Ollama、中转站等）|

---

## 七、备份管理

- 每次 create/update 写入前自动备份全量自动化
- 备份文件：`backup/archives/automations_backup_{YYYYMMDD_HHMMSS}.json`
- 保留最近 10 个版本，自动清理旧备份
- `backup restore` 支持交互式选择恢复版本

---

## 八、使用入口与 CLI 命令速查

### 统一交互入口（推荐）

```bash
python3 main.py
```

启动后显示模式选择菜单：
```
╭─ 请选择模式 ────────────────────────────────────────────────╮
│ HA 自动化大模型工具                                         │
│                                                             │
│   1. 创建  — 用自然语言描述，AI 生成新自动化               │
│   2. 优化  — 分析并优化单条已有自动化                      │
│   3. 聚合  — 批量整合所有自动化（合并重复、纠正错误）      │
╰─────────────────────────────────────────────────────────────╯
>
```

### 直接子命令（调试/高级用法）

```bash
python3 main.py init                          # 交互式初始化配置
python3 main.py test-connection               # 测试 HA 连接
python3 main.py list-entities [--domain light] [--search 关键字]
python3 main.py list-automations              # 列出所有自动化
python3 main.py create "需求描述" [--dry-run] [--no-docs]
python3 main.py update --id <automation_id>   # AI 修改已有自动化
python3 main.py optimize [--id <automation_id>] [--dry-run]  # 单条自动化优化
python3 main.py consolidate [--dry-run]       # 多条自动化批量整合
python3 main.py refresh-docs [--list]         # 刷新/查看文档缓存
python3 main.py backup list
python3 main.py backup create
python3 main.py backup restore [--file <path>]
```

---

## 九、开发规范

### 技术栈

- **Python 3.9+**（所有文件需 `from __future__ import annotations` 兼容 `|` 语法）
- `httpx` — HTTP 客户端
- `anthropic` / `openai` — LLM SDK
- `pyyaml` — YAML 解析（注意：解析时丢弃 `#` 注释，不要依赖注释传递信息）
- `pypinyin` — 中文转拼音（alias ASCII 化）
- `beautifulsoup4` + `markdownify` — 文档抓取
- `rich` + `typer` — CLI 界面
- `websocket-client` — WebSocket（获取实体注册表）

### 安全原则

- `config.json` 已加入 `.gitignore`
- LLM 生成的配置必须经过 schema 校验才能写入 HA
- 写入前自动备份，确保可回滚
- 删除操作需二次确认

### Git

- 已初始化本地 git 仓库（不需要 GitHub）
- 每次完成功能点后 commit 存档

---

## 十、命令实现详情

### 单条自动化优化（`optimize` 命令）

**功能目标**：选择一条已有自动化，让 LLM 理解其意图并进行优化，支持追问修改后写回 HA。

**完整流程**：

```
1. 列出所有自动化 → 用户选择目标（交互式菜单 or --id 参数）
2. GET /api/config/automation/config/{id} 获取完整配置
   + get_entities(config) 获取当前实体列表
3. LLM Step 1：理解意图（build_optimize_analysis_prompt）
   - 传入：自动化完整 YAML + 实体列表
   - 输出 JSON：{intent, related_entities, issues, suggestions}
     - intent: 对当前自动化功能的自然语言描述
     - related_entities: 当前涉及实体列表
     - issues: 发现的问题（缺少 description / 逻辑不完整 / 幻觉实体等）
     - suggestions: 优化建议列表
4. 展示分析报告，询问用户是否继续生成优化配置
5. LLM Step 2：生成优化后的完整 YAML（build_optimize_yaml_prompt）
   - 优化方向（根据意图自动判断）：
     - 补充/完善 description 字段
     - 补充同意图相关的同类设备（如"离家节能"只关了客厅灯，可补充其他区域灯/空调等）
     - 修正幻觉 entity_id（引用了不存在的实体）
     - 完善 conditions（时间段限制、人员在家判断等）
     - 统一字段格式到 HA 2024+ 规范
6. 交互式追问修改循环（同 create 命令：输入意见→LLM重新生成→循环）
7. 用户确认 → 备份 → POST /api/config/automation/config/{id} 写回
```

**提示词**：
- `build_optimize_analysis_prompt(automation_yaml, entities, visible_domains)` → JSON 分析
- `build_optimize_yaml_prompt(automation_yaml, analysis, entities, docs, visible_domains)` → 优化 YAML

---

### 多条自动化批量整合（`consolidate` 命令）

**功能目标**：分析当前全部自动化，发现可合并的重复项和逻辑错误，输出优化方案供用户逐条确认后执行。

**完整流程**：

```
1. list_automations() 获取所有自动化摘要
2. 批量 GET /api/config/automation/config/{id} 获取全量完整配置
   （跳过 id 为空或 "new" 的无效条目）
   + get_entities(config) 获取实体列表
3. LLM 单次分析（build_consolidate_prompt，传入全部 YAML + 实体列表）
   输出 JSON：
   {
     "merge_groups": [
       {"ids": [...], "aliases": [...], "reason": "...", "merged_yaml": "..."}
     ],
     "fix_items": [
       {"id": "...", "alias": "...", "issue": "...", "fixed_yaml": "..."}
     ],
     "ok_items": [{"id": "...", "alias": "..."}]
   }
4. 格式化展示整合方案（合并组/修复项/无需变动数量）
5. 逐条展示 YAML → 用户确认（直接回车接受 / 输入修改意见 / 输入 s 跳过）
6. 追问修改循环（同 create 命令）
7. 执行前整体备份 →
   - 合并：先 create 新自动化，确认成功后 delete 旧自动化
   - 纠错：update 对应自动化
   - reload automations
```

**注意事项**：
- 自动化 YAML 总量超过约 40000 字符时自动截断，优先保留前 N 条
- 合并必须先确认新自动化写入成功才删除旧的
- `--dry-run` 模式只展示方案，不执行写入/删除

---

## 十一、已知问题 / 待调试

- [ ] `update` 命令：`POST /{id}` 写入内容是否正确持久化（待验证）
- [ ] YAML 型自动化（`restored=true, state=unavailable`）无法通过 GET 获取完整配置；optimize/consolidate 已自动过滤
- [ ] WebSocket `config/automation/config/list` 在 HA 2026.2.3 返回 unknown_command，自动化配置只能 REST GET 逐条获取
- [ ] consolidate 命令：尚未实测完整执行流程
- [ ] `backup restore`：逐条恢复流程完整性验证

---

## 十二、后续封装为 HA 插件规划

1. 将核心逻辑提取为独立 Python 包
2. 创建 `custom_components/ha_llm_automation/` 目录
3. 实现 `config_flow.py`（UI 配置向导）
4. 实现 `conversation.py` 或 `service.py` 暴露 HA 服务
5. 注册为 HA 对话代理（Conversation Agent）
6. 编写 `manifest.json` 和 `strings.json`

---

## 十三、快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化配置
cp config.example.json config.json
python3 main.py init

# 3. 测试连接
python3 main.py test-connection

# 4. 抓取 HA 文档（首次必做）
python3 main.py refresh-docs

# 5. 创建第一个自动化（--dry-run 先预览）
python3 main.py create "每天晚上10点关闭客厅灯" --dry-run
python3 main.py create "每天晚上10点关闭客厅灯"
```
