# HA 自动化大模型创建工具 — 项目指南

## 项目概述

本项目是一个基于大模型（LLM）的 Home Assistant 自动化创建与管理工具。
目标是通过自然语言描述，自动生成、修改、备份 HA 自动化脚本，最终封装为 HA 集成插件。

**开发阶段：** 三大核心模式均已实现（create / optimize / consolidate）；CLI 工具（`python3 main.py`）与 HACS Custom Component（`custom_components/ha_llm_automation/`）均已完成。当前版本：**v2.6**（前端全量 i18n，中英文随 HA 语言自动切换；新增 hacs.json 准备 GitHub 发布）。

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
| 删除自动化 | `DELETE /api/config/automation/config/{id}` | ⚠️ 仅存储型有效；YAML 型返回 400 "Resource not found"，只能手动编辑 automations.yaml |
| 重载配置 | `POST /api/services/automation/reload` | ✅ |

### ⚠️ 「存储型」vs「YAML型」自动化

HA 中存在两类自动化：

| 类型 | 存储位置 | GET 完整配置 | DELETE | 说明 |
|------|---------|------------|--------|------|
| **存储型** | HA `.storage/` | ✅ | ✅ | 通过 HA UI 或本工具 REST API 创建 |
| **YAML型** | `automations.yaml` | ❌ 404 | ❌ 400 | 手动在配置文件中定义；只能编辑 automations.yaml 删除 |

`/api/states` 两类都会列出（包含 `attributes.id`），但 GET 完整配置只对存储型有效。
`optimize` 和 `consolidate` 命令启动时自动探测并过滤，只展示可访问的自动化。

#### 辨别方法
- YAML 型：`attributes.restored = true, state = unavailable`（HA 重启后从 state DB 恢复）
- 存储型：`state = on/off`，正常工作

### ⚠️ 创建自动化的必要条件 & normalize_automation() 处理

向 `POST /api/config/automation/config/new` 发送的 payload 必须同时满足：

1. **含 `id` 字段**：13 位毫秒时间戳（如 `"1772515732053"`），否则 HA 以为是未保存的草稿
2. **含 `description` 字段**：哪怕是空字符串 `""`，否则 triggers/actions 不被持久化
3. **alias 必须为纯 ASCII**：HA API 不接受中文 alias（返回 500）

`normalize_automation()` 函数（`ha_client/automations.py`）自动处理以上问题，以及：

- **剔除 meta 字段**：`last_triggered`、`uid`、`state`、`context`、顶层 `entity_id` 不属于 config schema，LLM 可能从原配置复制这些字段，必须清除（否则 400）
- **alias**：中文 → `pypinyin` 转拼音 snake_case
- **description**：替换常见 Unicode 符号（`→` → `->`），再移除全部非 ASCII 字符（HA 配置 API 不接受非 ASCII）；不存在时补 `""`
- **旧版字段名**：`trigger` → `triggers`，`condition` → `conditions`，`action` → `actions`，`service:` → `action:`
- **注入 id**：`str(int(time.time() * 1000))`（由 `create_automation()` 负责）

### ⚠️ choose 块内 conditions 不能用 trigger 语法

`choose` 里的 `conditions` 使用 **condition 语法**，不能用 trigger 专属字段：

```yaml
# ❌ 错误：at: 是 trigger 专属字段
actions:
  - choose:
      - conditions:
          - at: "22:00:00"   # HA 会返回 400：extra keys not allowed

# ✅ 正确：condition: time 语法
actions:
  - choose:
      - conditions:
          - condition: time
            after: "22:00:00"
            before: "07:00:00"
```

### ⚠️ HTTP 错误信息

`connection.py` 的 `post()` / `put()` 失败时会在异常中附带 HA 返回的 response body（最多 600 字符），便于定位具体原因。

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

## 四、两步 LLM 创建流程（支持单条/多条自动化）

```
get_entities() → 过滤隐藏/禁用/诊断实体 + 注入区域
       ↓
Step 1：可行性检查（build_feasibility_prompt）
  - LLM 推断实现所有需求所需的实体（返回并集）
  - 返回 JSON: {"feasible": bool, "entities": [...], "reason": "..."}
  - 不可行 → 显示原因，退出
       ↓
Step 2：YAML 生成（build_system_prompt，仅含 Step1 筛出的实体）
  - 每条自动化单独输出一个 ```yaml``` 代码块
       ↓
【单条自动化】交互式修改循环：
  - 展示 YAML → 输入修改意见 → LLM 重新生成 → 循环
  - 直接回车接受 → 校验 → 确认写入
  → normalize → validate → 备份 → create_automation → reload

【多条自动化】批量预览 + 选择写入：
  - 逐条展示并校验（幻觉实体/action字段错误标红警告）
  - 用户可输入要跳过的编号（如 2,5）或直接回车全部写入
  → normalize → 备份 → 批量 create_automation → reload
```

`parse_automations_from_text()` 支持解析：单 dict / list[dict] / 多个独立 yaml 块 / `automation:` 顶层包装

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

- 每次 create/update/consolidate 写入前自动备份全量自动化
- 备份文件：`backup/archives/automations_backup_{YYYYMMDD_HHMMSS}.yaml`（**YAML 格式，可直接导入 HA**）
- `list_backups` / `restore_backup` 向后兼容旧 `.json` 备份
- 保留最近 10 个版本（yaml + json 合并计算），自动清理旧备份
- `backup restore` 支持交互式选择恢复版本

---

## 八、使用入口与 CLI 命令速查

### 统一交互入口（推荐）

```bash
python3 main.py
```

启动后显示模式选择菜单（while 循环，完成一次操作后自动返回菜单）：
```
╭─ 请选择模式 ────────────────────────────────────────────────╮
│ HA 自动化大模型工具                                         │
│                                                             │
│   1. 创建  — 用自然语言描述，AI 生成新自动化               │
│   2. 优化  — 分析并优化单条已有自动化                      │
│   3. 聚合  — 批量整合所有自动化（合并重复、纠正错误）      │
│                                                             │
│   输入 exit 退出                                            │
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
- `readline` — 标准库，修复 macOS 下 `input()` 退格/方向键异常
- `websocket-client` — WebSocket（获取实体注册表）

### 安全原则

- `config.json` 已加入 `.gitignore`
- LLM 生成的配置必须经过 schema 校验才能写入 HA
- 写入前自动备份，确保可回滚
- 删除操作需二次确认

### 前端 JS 校验（必做）

- 每次修改 `custom_components/ha_llm_automation/frontend/*.js` 后、commit 前必须运行 `bash scripts/check_frontend.sh`
- 脚本内部调用 `node --check`（零依赖，Node 18+），只做语法解析，失败即报错
- 翻译值里出现 ASCII 双引号必须写成 `\"`（或改用全角 `“ ”`）。未转义即整份模块 SyntaxError → 面板白屏（v2.6 已踩过坑）

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

**功能目标**：分析当前全部自动化，按使用场景合并重复项、纠正逻辑错误，供用户逐条确认后执行。

**场景驱动合并策略**（`build_consolidate_prompt` 4 步分析）：

```
Step 1：识别每条自动化的使用场景
        离家节能 / 到家迎接 / 睡前准备 / 起床唤醒 / 夜间安全 / 定时控制 / 温湿度联动 ...

Step 2：判断合并条件
  ✅ 触发相同（或等价）且属于同一场景 → 合并（即使操作不同的设备）
     例：离家后关灯 + 离家后关电扇 → 合并为「离家节能」
  ❌ 触发不同 / 场景目的明显不同 → 不合并

Step 3：找出需修复的问题
        幻觉实体 / 旧版字段名 / 缺少description / 逻辑错误

Step 4：生成合并 YAML（必须包含所有被合并自动化的全部设备操作）
```

**LLM 输出 JSON 格式**：
```json
{
  "merge_groups": [
    {"ids": [...], "aliases": [...], "scenario": "离家节能", "reason": "...", "merged_yaml": "..."}
  ],
  "fix_items": [{"id": "...", "alias": "...", "issue": "...", "fixed_yaml": "..."}],
  "ok_items": [{"id": "...", "alias": "..."}]
}
```

**完整流程**：

```
1. list_automations() → 批量 GET 完整配置（跳过 GET 失败 / id 为空 / "new" 的条目）
2. LLM 场景分析 → 展示方案（含场景标签）
3. 逐条展示 YAML → 用户确认（回车接受 / 输入意见让 AI 改 / s 跳过）
4. 整体备份 → 执行：
   - 合并：create 新 → 成功后 delete 旧
   - 修复：update 对应自动化
   - reload
5. 执行失败（400等）→ 自动把 HA 错误 + YAML 发给 LLM 修复，最多重试 2 次
```

**注意事项**：
- YAML 总量超过约 40000 字符时自动截断，优先保留前 N 条
- 合并必须先确认新自动化写入成功才删除旧的
- `--dry-run` 模式只展示方案，不执行写入/删除
- `_llm_fix_yaml(parsed, ha_error)` 内部函数负责错误驱动的自动修复

---

## 十一、已知问题 / 待调试

- [ ] `update` 命令：`POST /{id}` 写入内容是否正确持久化（待验证）
- [ ] YAML 型自动化（`restored=true, state=unavailable`）无法通过 GET 获取完整配置；optimize/consolidate 已自动过滤
- [ ] WebSocket `config/automation/config/list` 在 HA 2026.2.3 返回 unknown_command，自动化配置只能 REST GET 逐条获取
- [ ] consolidate 命令：场景驱动策略已实现，端到端效果待实测
- [x] 清除不可访问自动化：两级清除策略已实测验证（幽灵实体通过注册表移除成功清除）
- [ ] HACS 卡片图标/发布：hacs.json 已就绪，需推送至 GitHub + 通过 HACS 安装才可生效
- [ ] i18n 翻译完整性：v2.6 已覆盖全部 UI，后续新增文案需同步更新 TRANSLATIONS 常量

### v2.2 已修复

- **HA access_token 30 分钟过期**：`HABridge` 改存 `refresh_token` 对象，`_headers()` 每次调用实时生成新 access_token。`_get_or_create_refresh_token()` 返回 refresh_token 对象（不再调用 `async_create_access_token`）。
- **亮色模式输入框灰底**：CSS 改为 `background: transparent`
- **亮色模式 Tab 文字不可见**：Tab 字体改用 `var(--app-header-text-color)` + opacity
- **聚合模块**：`run_consolidate_analyze` 新增 `automation_ids` 参数，前端聚合 Tab 加预选 checkbox 列表
- **前端新增**：主题切换（🌓 循环三态）、终止按钮（■）、优化 diff 切换（左右/内联）、配置页筛选备注

### v2.3 已修复 / 新增

- **系统主题实时跟随**：`connectedCallback/disconnectedCallback` 增加 `prefers-color-scheme` matchMedia 监听，系统切换主题时页面自动重绘
- **标题颜色修复**：`.header h1` 改为 `var(--app-header-text-color, #ffffff)`，亮色 header（蓝色背景）下可见
- **聚合 prompt 全量覆盖**：`build_consolidate_prompt` 合并条件改为**以场景为唯一依据**（去掉时间差匹配条件，触发时间不一致也可合并），新增「强制要求」段确保每条自动化出现在三个列表之一、不得遗漏
- **优化追问方向**：分析结果卡片（step1）增加可选方向 textarea（`#opt-direction-input`）；`run_optimize_generate` 新增 `user_direction` 参数，`ws_optimize_generate` schema 同步新增 `vol.Optional("user_direction")`
- **聚合批量勾选执行**：聚合结果顶部新增 `.consolidate-batch-bar`（全选/全不选/批量执行按钮）；每条 merge/fix item header 增加 `.cons-item-cb` checkbox，勾选状态与 `_consolidateApproved` 同步
- **追问按钮更醒目**：创建 Tab 中 `btn-refine-toggle-${i}` 按钮由 `btn-secondary btn-sm` 改为 `btn-primary`
- **use_docs 标签文字**：改为"在 Prompt 中注入 HA 官方文档（本地缓存，7 天后自动更新；关闭则完全跳过）"
- **配置保存反馈**：按钮点击后立即禁用并显示"⏳ 保存中..."，完成后恢复，防止重复点击
- **聚合预选 checkbox 颜色**：`.consolidate-check-item` 新增 `accent-color: #818cf8`，无需 hover 即显示蓝色
- **优化 step1 重新分析按钮**：分析报告卡片标题右侧新增"🔄 重新分析"按钮，可随时重新执行 step1；direction 标签改为"追加优化方向（传给 Step 2）"
- **HA 2026.x 静态路径 API 兼容**：`hass.http.register_static_path()` 在 2026.x 被移除，改用 `await hass.http.async_register_static_paths([StaticPathConfig(...)])` + 新增 `from homeassistant.components.http import StaticPathConfig`（兼容 2024.2+）
- **滚动跳顶修复（Critical UX）**：① `hass` setter 仅在首次注入时调用 `_render()`，避免 HA 每次推送实体状态更新都触发全量重绘；② `_render()` 在重写 innerHTML 前保存 `.content/.main-area` 的 `scrollTop`，重写后立即恢复
- **备份恢复跳过空配置**：`run_restore_backup` 检测无 triggers/actions 的条目（YAML 型自动化空配置），直接 skip + 记录日志，避免误报"缺少必要字段"
- **聚合列表过滤不可访问**：`_renderConsolidate` 加 `a.accessible !== false` 过滤，不再展示 YAML 型不可访问自动化
- **优化 Step1 追问重新分析**：去掉标题处的独立"重新分析"按钮，textarea 下方改为双按钮行（🔄重新分析 + ▶生成优化方案）；`_optimizeAnalyze()` 读取方向输入传 `user_direction`；后端 `build_optimize_analysis_prompt`/`run_optimize_analyze`/`ws_optimize_analyze` 同步支持
- **集成筛选容错**：`ha_bridge.get_entities()` 检测到 `entity_platform` 为空时禁用 `integration_filter`（避免全量误过滤），新增 `import logging` / `_LOGGER`
- **优化下拉不再收起**：新增 `_updateLogPanel()` 精准更新 `.log-entries`，日志订阅回调和 `_log()` 均改用它替代 `_render()`，防止日志推送触发 DOM 重建
- **配置保存 Toast + 表单值持久**：`_render()` 前保存 `.toast-container` 子节点 + 8 个配置输入字段值，重写 innerHTML 后恢复，Toast 不再消失、表单不再被 re-render 重置
- **自动化列表加载状态 UX**：`_automations` 从 `[]` 改为 `null` 区分「未加载」与「已加载为空」；新增 `_automationsLoading` 标志；优化/聚合 Tab 选择卡片顶部各加「🔄 刷新列表」按钮，显示三态：加载中（spinner）/ 加载失败（null，提示重试）/ 无数据（已加载但空）

### v2.4 已修复 / 新增

- **备份内容完整性（Critical 修复）**：备份前改为逐条调用 `GET /api/config/automation/config/{id}` 获取完整配置（含 triggers/actions）；三处备份调用（create/optimize/consolidate）统一使用 `_get_full_automations_for_backup()` helper，跳过 YAML 型
- **清除不可访问自动化**：聚合 Tab 新增「🗑 清除不可访问（N 条）」红色按钮；后端 `ws_delete_inaccessible_automations` 后端自动探测（list → 逐GET → 失败则DELETE → reload），**不依赖前端传 ID**（规避 HA 2026.x WS 框架数组参数兼容性问题）；全流程加 `_LOGGER`，前端失败详情逐条打到日志面板。**两级清除策略**：① DELETE API 成功 → 正常删除；② DELETE 返回 "Resource not found" → 尝试 `entity_registry.async_remove(entity_id)` 清除幽灵实体；③ 注册表也失败 → 提示手动编辑 `automations.yaml`；前端区分三种结果（`[OK]`幽灵清除 / `[WARN]`需手动 / `[ERROR]`真实失败）
- **HA WS 数组参数兼容性坑（Critical）**：HA 2026.x WS 框架对 `list` 类型参数有序列化兼容问题；`vol.Required`→Required key error；`vol.Optional(default=[])`→默认值被用参数始终为空。**原则：WS 命令避免接收数组，改为后端自行处理**
- **移动端键盘收起修复（v2.4.1 深化）**：① 删除 `textarea` 的 `backdrop-filter: blur(6px)` GPU合成层；② `@media (hover:none) and (pointer:coarse)` 禁用 `.input-wrap` 两个伪元素动画 + 清除 `will-change`；③ **切 Tab 后首次 focus 仍收起根因**：`_render()` 重建 DOM 后第一次 focus 触发 `transition`/`box-shadow` 变化 → GPU 合成层与键盘弹出 viewport 缩小同时发生 → WebKit 收起键盘；修复：touch 设备再追加 `transition: none !important` + `box-shadow: none !important`（textarea/input/:focus/.input-wrap:focus-within）
- **HACS 图标**：`custom_components/ha_llm_automation/icon.png`（256×256 RGBA）；HACS 卡片图标需 GitHub 仓库才生效，本地阶段 icon.png 已就位
- **侧边栏图标**：`PANEL_ICON = "mdi:creation"`（AI 魔法星花，`const.py`）
- **液态荡漾输入框**：全局 textarea/input 玻璃磨砂效果（无 backdrop-filter）；`.input-wrap` 三处主输入框加流光渐变边框 + 液态荡漾高光动画；亮/暗主题 + 触摸设备适配（touch 设备禁用重型动画）

### v2.5 新增功能

- **自动化管理 Tab（📋 管理）**：列出全部自动化，支持批量勾选；批量操作栏含「全选/全不选/备份选中(N)/删除选中(N)」；不可访问条目禁用勾选；批量删除后自动 reload；后端新增 `ws_batch_delete_automations`（逗号分隔ID规避WS数组兼容）和 `ws_backup_selected`（生成子集备份文件）
- **备份恢复双模式**：备份管理卡顶部增加模式切换按钮；**增量**（跳过已有同名自动化）/ **覆盖**（已有则 update，否则 create）；模式持久到 `_restoreMode` 状态，确认弹窗显示当前模式；后端 `run_restore_backup` 新增 `restore_mode` 参数，覆盖模式通过 alias 匹配现有 id 执行 `update_automation`
- **主题按钮三态区分**：`🖥️ 自动`（半透明边框）/ `🌙 暗色`（紫色背景+边框）/ `☀️ 亮色`（金色背景+边框）；按钮同步显示当前状态文字标签

### v2.5.1 移动端 CSS 精准优化

- **问题**：前版过度禁用了 touch 设备 CSS 动画（`inputGradientFlow` 被禁），手机效果远弱于桌面
- **核心洞察**：区分"在 focus 前已运行"（安全）vs"在 focus 时启动/变化"（危险）：
  - **安全**：`inputGradientFlow`（渐变边框）在 focus 前就在播，focus 时不触发新的合成层变化 → 保留（降频 6s）
  - **危险**：`inputLiquidRipple`（荡漾高光）从 focus 开始启动；`box-shadow` 在 focus 时从无到有；`transition` 在 focus 时产生渐变 → 全部禁用
- **修复**：`@media (hover:none)` 内仅保留 `inputGradientFlow`（6s）；禁用 `inputLiquidRipple`；所有 `transition: none !important`；所有 focus 触发的 `box-shadow: none !important`；补偿：`.input-wrap` 加常驻微光（不依赖 focus，无变化）
- **结果**：手机端流光渐变边框 + 常驻微光保留；键盘稳定不收起；桌面端完整效果不变

### v2.6 新增功能（前端全量 i18n + hacs.json）

- **前端全量 i18n**：
  - 新增 `TRANSLATIONS` 常量（`zh` / `en` 两套，覆盖全部 UI 文案）
  - 全局 `_i18n(lang, key, vars)` 函数，支持 `{varName}` 插值
  - `_lang` getter：读 `hass.language`，`zh-*` → `zh`，其余 → `en`
  - `_t(key, vars)` 实例方法，全部 6 个 Tab 的 `_render*()` 方法均改用 `_t()`
  - 完整覆盖：confirm 弹窗、toast 消息、日志面板、按钮文字、说明文字
  - `_pushLog()` 颜色检测兼容中英文关键词（ERROR/错误、WARN/警告、OK/成功等）
- **hacs.json**：项目根目录新增 HACS 集成元数据文件，支持未来 GitHub/HACS 发布
  - `homeassistant: "2024.2.0"`，`content_in_root: false`

### v2.6.1 已修复（前端白屏回归）

- **根因**：`frontend/ha-llm-automation.js` L35/L56 两条中文翻译值 `"加载失败，请点击"刷新列表"重试"` 将 ASCII 双引号嵌入同样用 ASCII 双引号包裹的字符串字面量（未转义），V8 抛 `SyntaxError: Unexpected identifier '刷新列表'` → 整份模块解析失败 → `customElements.define("ha-llm-automation", ...)` 从未执行 → HACS 安装后打开面板白屏
- **修复**：两处改为 `"加载失败，请点击\"刷新列表\"重试"`，与英文版 `\"Refresh\"` 同构；`TRANSLATIONS` 注释块新增转义约定（用 `\"` 或改用全角 `“ ”`）
- **兜底**：新增 `scripts/check_frontend.sh`（`node --check`，零依赖），对 `frontend/*.js` 做语法校验；已写入开发规范「前端 JS 校验（必做）」小节
- **版本**：`manifest.json` 从 `2.6` bump 到 `2.6.1`

### macOS 退格键 / 方向键异常

**已修复**：`main.py` 顶部加 `import readline`（标准库），Python `input()` 即可获得 GNU readline 支持（退格、左右方向键、历史记录等）。

---

## 十二、HACS Custom Component（已实现，v2.6）

`custom_components/ha_llm_automation/` 已完整实现，结构如下：

```
custom_components/ha_llm_automation/
├── __init__.py          ← setup_entry + 25个WS命令 + 面板注册 + 旧配置迁移
├── config_flow.py       ← 纯确认步骤（无字段，全配置在前端配置Tab完成）
├── const.py             ← CONF_LOG_PROMPT/USE_DOCS/AREA_FILTER/LABEL_FILTER/INTEGRATION_FILTER；PANEL_ICON="mdi:creation"
├── core/
│   ├── ha_bridge.py     ← HABridge；delete_automation 捕获响应体
│   ├── llm_service.py   ← 三大模式async化；_get_full_automations_for_backup() 备份完整配置
│   └── automations_utils.py
├── knowledge/ / llm_client/ / backup/
├── icon.png             ← HACS 图标（256×256 RGBA）
└── frontend/ha-llm-automation.js  ← v2.6 前端（液态荡漾输入框 + 全量 i18n）
hacs.json                ← HACS 集成元数据（根目录）
```

### 关键设计决策

- **Token**：`setup_entry` 时用 `TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN` 创建 refresh_token（不过期），存入 `HABridge`；每次 REST 调用通过 `_headers()` 实时生成 access_token（避免 30 分钟过期）
- **配置存储**：全部 LLM 配置存 `entry.options`；config_flow 仅一步确认，无字段
- **实体**：使用 HA 内置 `hass.states` / `entity_registry` / `area_registry`（无 REST）
- **自动化 CRUD**：aiohttp 对 `localhost:8123`（避免反向代理限制）
- **日志推送**：dispatcher send → WS subscribe_log → 前端实时显示

### 部署方式

```
将 custom_components/ha_llm_automation/ 复制到 HA config/custom_components/
重启 HA → 集成页面添加"HA LLM Automation" → 点击确认
侧边栏出现 LLM Automation 入口 → 配置Tab → 填写 API Key 等 → 保存
```

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

---

## 十四、三大模块设计评审（待优化方向）

> 当前版本已实现，以下为设计层面的已知不足，供后续迭代参考。

### 创建模块

- **知识库按需注入**：简单需求（"每天7点开灯"）不需要文档，可在可行性检查阶段判断需求复杂度，按需决定是否注入文档，节省 token
- **修改循环缺版本对比**：多轮追问后用户无法看到与初始版本的 diff，建议在循环内提供「和上一版对比」入口
- **多条批量生成的跳过粒度粗**：只能整条跳过，无法单独修改某条后其余照常写入

### 优化模块

- **step1 分析结论未贯穿追问循环**：追问时 step1 的诊断结论不一定在上下文中，AI 可能遗忘初始发现的问题
- **优化边界前置确认**：AI 可能自作主张扩大范围（把客厅灯扩展到全屋），应在 step1 报告后让用户先确认优化边界
- **幻觉实体检测应在校验层**：diff 只是展示，可在校验阶段检测新增 entity_id 是否都在当前实体列表，若未出现应标红警告

### 聚合模块（问题最多）

- **全量 YAML 一次喂 LLM 负担重**：20条+时 prompt 体积大，LLM 容易遗漏或错误合并；更好策略：先粗分场景，再对每个场景独立推理合并
- **场景分组用户无参与**：方案出来前用户完全没有参与，AI 的场景理解可能与用户不符；应在 LLM 输出场景分组后先让用户确认分组再进入合并生成
- **合并质量不可验证**：写入成功只说明格式正确，不代表合并后逻辑等价于原几条的并集，目前只能靠用户事后测试

### 三模块共同问题

- **知识库静态化**：7天缓存文档，HA 迭代快；文档内容的价值低于「当前版本支持的 trigger/action 类型清单」这类动态信息
- **设备上下文缺语义归类**：传给 LLM 的是原始 entity_id 摘要，AI 需自行推断语义；若在准备阶段做一次按功能分组（如"照明/温控/安防"），生成质量会提升
- **写入后无验证手段**：备份在写入前做，但写入后自动化是否按预期触发完全不可观测，需要用户手动测试
