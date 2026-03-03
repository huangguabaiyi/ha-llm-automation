# HA 自动化大模型创建工具 — 项目指南

## 项目概述

本项目是一个基于大模型（LLM）的 Home Assistant 自动化创建与管理工具。
目标是通过自然语言描述，自动生成、修改、备份 HA 自动化脚本，最终封装为 HA 集成插件。

**开发阶段：** CLI 流程已跑通（create 核心功能验证完毕），待完善 update/backup/restore，再封装为 HA Custom Component。

---

## 项目结构

```
HA自动化工具/
├── CLAUDE.md                  # 本文件，项目指南
├── CLAUDE.md.bak              # 上一版本备份
├── config.json                # 本地配置（不提交 git）
├── config.example.json        # 配置模板
├── main.py                    # 主入口 CLI（typer）
├── requirements.txt
├── ha_client/
│   ├── __init__.py
│   ├── connection.py          # HAConnection, load_config
│   ├── entities.py            # EntityManager（带5分钟缓存）
│   ├── automations.py         # AutomationManager + 工具函数
│   └── ws_client.py           # WebSocket 客户端（备用）
├── llm_client/
│   ├── __init__.py            # create_client() 工厂函数
│   ├── base.py                # BaseLLMClient 抽象基类
│   ├── openai_client.py       # OpenAI / 兼容接口
│   └── anthropic_client.py    # Anthropic Claude 接口
├── knowledge/
│   ├── fetcher.py             # DocFetcher（抓取+缓存，7天TTL）
│   ├── prompts.py             # build_system_prompt()
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
  }
}
```

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

- `get_all_entities()` — 带 5 分钟本地缓存
- `get_entities_by_domain(domain)` — 按域过滤
- `search_entities(keyword)` — 模糊搜索
- 传给 LLM 的实体摘要按 domain 白名单过滤 attribute，避免超出 token 限制

---

## 三、自动化脚本管理

### ⚠️ 实际可用的 REST API 端点

> 注意：通过反向代理时，部分端点不可用，以下为实测结果。

| 操作 | 端点 | 状态 |
|------|------|------|
| **列出所有自动化** | `GET /api/config/automation/config` | ❌ 404（代理屏蔽）|
| **改用** | `GET /api/states` 过滤 `automation.*` | ✅ |
| 获取单条完整配置 | `GET /api/config/automation/config/{id}` | ✅ |
| **创建自动化** | `POST /api/config/automation/config/new` | ✅（有特殊要求，见下）|
| **更新自动化** | `POST /api/config/automation/config/{id}` | ✅（非 PUT）|
| 删除自动化 | `DELETE /api/config/automation/config/{id}` | ✅ |
| 重载配置 | `POST /api/services/automation/reload` | ✅ |

### ⚠️ 创建自动化的三个必要条件

向 `POST /api/config/automation/config/new` 发送的 payload 必须同时满足：

1. **含 `id` 字段**：13 位毫秒时间戳（如 `"1772515732053"`），否则 HA 以为是未保存的草稿，UI 点开直接跳新建页面
2. **含 `description` 字段**：哪怕是空字符串 `""`，否则 triggers/actions 不被持久化（保存为空）
3. **alias 必须为 ASCII**：HA API 不接受中文字段值（任何字段含中文均返回 500）

`normalize_automation()` 函数自动处理上述三点：
- 中文 alias → pypinyin 转拼音 snake_case
- 中文 description → 清空为 `""`
- 注入 `description: ""` 兜底
- 注入 `id: str(int(time.time() * 1000))`（在 `create_automation()` 里完成）

### HA 2024+ 新版字段名

```yaml
# 新版（HA 2024.10+，API 返回和接受的格式）
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
- 通过 REST API 创建的自动化，其 entity state 的 `attributes.id` 可能显示为 `"new"`（已知 HA 行为），但自动化内容是正确的
- 自动化存储在 HA 内部（非 `automations.yaml`），在 HA UI「设置 → 自动化」中可见

---

## 四、HA 官方文档学习模块

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

### DocFetcher（`knowledge/fetcher.py`）

- `get_doc(url)` — 优先读缓存，过期自动重新抓取
- `get_preset_docs(keys)` — 批量获取指定文档
- `refresh_all_docs()` — 强制刷新全部文档
- 缓存 TTL：7 天，按 URL MD5 命名文件

### 提示词构建（`knowledge/prompts.py`）

- `build_system_prompt(docs, entities)` — 组装 System Prompt
- 包含：HA 文档摘要（优先级排序）+ 当前实体列表（Markdown 表格）
- 文档最多 12000 字符，实体最多 150 条，控制 token 消耗

---

## 五、LLM API 接口配置

### 支持的 Provider

| Provider | 说明 |
|----------|------|
| `anthropic` | Anthropic 官方 API |
| `openai` | OpenAI 官方 API |
| `openai_compatible` | 兼容 OpenAI 格式的第三方接口（DeepSeek、Ollama、中转站等）|

### 核心对话流程

1. 用户输入自然语言需求
2. 获取实体列表 + 加载 HA 文档缓存
3. `build_system_prompt()` 构建带上下文的 System Prompt
4. 调用 LLM 生成 YAML（要求英文 alias、新版字段名、无 `automation:` 包装）
5. `extract_yaml_from_text()` 提取代码块
6. `unwrap_automation()` 去除多余包装层
7. `normalize_automation()` 转换格式 + 注入 description
8. `validate_automation()` 校验必要字段
9. 用户确认 → 备份当前自动化 → `create_automation()` 写入

---

## 六、备份管理

- 每次 create/update 写入前自动备份全量自动化
- 备份文件：`backup/archives/automations_backup_{YYYYMMDD_HHMMSS}.json`
- 保留最近 10 个版本，自动清理旧备份
- `backup restore` 支持交互式选择恢复版本

---

## 七、CLI 命令速查

```bash
python3 main.py init                          # 交互式初始化配置
python3 main.py test-connection               # 测试 HA 连接
python3 main.py list-entities [--domain light] [--search 关键字]
python3 main.py list-automations              # 列出所有自动化
python3 main.py create "需求描述" [--dry-run] [--no-docs]
python3 main.py update --id <automation_id>   # AI 修改已有自动化
python3 main.py refresh-docs [--list]         # 刷新/查看文档缓存
python3 main.py backup list
python3 main.py backup create
python3 main.py backup restore [--file <path>]
```

---

## 八、开发规范

### 技术栈

- **Python 3.9+**（需 `from __future__ import annotations` 兼容 `|` 语法）
- `httpx` — HTTP 客户端
- `anthropic` / `openai` — LLM SDK
- `pyyaml` — YAML 解析
- `pypinyin` — 中文转拼音（alias ASCII 化）
- `beautifulsoup4` + `markdownify` — 文档抓取
- `rich` + `typer` — CLI 界面

### 安全原则

- `config.json` 已加入 `.gitignore`
- LLM 生成的配置必须经过 schema 校验才能写入 HA
- 写入前自动备份，确保可回滚
- 删除操作需二次确认

---

## 九、已知问题 / 待调试

- [ ] `update` 命令：`POST /{id}` 写入内容是否正确持久化（待验证）
- [ ] `list-automations`：通过 states 获取的 id 部分为 `"new"`，影响 update 时选择目标
- [ ] `backup restore`：逐条恢复流程完整性验证
- [ ] 整体端到端回归测试

---

## 十、后续封装为 HA 插件规划

1. 将核心逻辑提取为独立 Python 包
2. 创建 `custom_components/ha_llm_automation/` 目录
3. 实现 `config_flow.py`（UI 配置向导）
4. 实现 `conversation.py` 或 `service.py` 暴露 HA 服务
5. 注册为 HA 对话代理（Conversation Agent）
6. 编写 `manifest.json` 和 `strings.json`

---

## 十一、快速开始

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

# 5. 创建第一个自动化
python3 main.py create "每天晚上10点关闭客厅灯" --dry-run
python3 main.py create "每天晚上10点关闭客厅灯"
```
