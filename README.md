# HA LLM Automation

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License](https://img.shields.io/github/license/huangguabaiyi/ha-llm-automation.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.2%2B-blue.svg)](https://www.home-assistant.io/)

> 用大语言模型（LLM）来管理 Home Assistant 自动化 —— 用自然语言**创建、优化、聚合**你的自动化脚本。

支持 OpenAI (GPT-4o)、Anthropic (Claude) 以及任何 OpenAI 兼容接口（DeepSeek / 本地 Ollama / 中转站等）。

---

## ✨ 核心功能

### 📝 创建模式
> "每天晚上 10 点关闭客厅灯，但如果有人在家就不关"

输入一句自然语言描述，LLM 会自动：
- 识别你家里相关的实体（灯、传感器、人员等）
- 可行性检查（告诉你能不能实现、需要哪些实体）
- 生成合规的 HA 2024+ YAML 配置
- 支持交互式追问修改，直到满意再写入

### 🔧 优化模式
选择一条已有的自动化 → LLM 理解意图 → 输出优化方案：
- 补全缺失的 description / conditions
- 修正幻觉 entity_id
- 补充同场景的相关设备（如"离家节能"可自动扩展到其他区域）
- 转换旧版字段名到 HA 2024+ 规范
- Diff 对比视图（左右/内联切换）

### 🧩 聚合模式
批量分析全部自动化，按使用场景合并重复项、纠正逻辑错误：
- 场景驱动：离家节能 / 到家迎接 / 睡前准备 / 起床唤醒 …
- 逐条预览，支持批量勾选执行
- 写入失败自动让 LLM 根据 HA 错误信息修复

### 🎨 界面特色
- 中英文随 HA 语言自动切换
- 三态主题切换（🖥️ 自动 / 🌙 暗色 / ☀️ 亮色）
- 液态荡漾输入框（桌面端流光动画 + 移动端优化）
- 实时日志面板
- 备份管理（双模式恢复：增量 / 覆盖）

---

## 📦 安装

### 方式一：通过 HACS 安装（推荐）

1. 确保已安装 [HACS](https://hacs.xyz/)
2. HACS → 右上角三点菜单 → **Custom repositories**
3. Repository 填写：`https://github.com/huangguabaiyi/ha-llm-automation`
4. Category 选择：**Integration**
5. 点击 **ADD**
6. 在 HACS 集成列表中找到 "HA LLM Automation" → Download
7. **重启 Home Assistant**
8. 进入 设置 → 设备与服务 → 添加集成 → 搜索 "HA LLM Automation"

### 方式二：手动安装

1. 下载最新 [Release](https://github.com/huangguabaiyi/ha-llm-automation/releases)
2. 解压后将 `custom_components/ha_llm_automation/` 整个目录复制到你 HA 的 `config/custom_components/` 下
3. 重启 Home Assistant
4. 添加集成：HA LLM Automation

---

## ⚙️ 配置

添加集成后，侧边栏会出现 **LLM Automation** 入口（图标为 ✨）。点击进入后切换到 **配置** Tab：

| 配置项 | 说明 | 示例 |
|---|---|---|
| **Provider** | LLM 服务商 | `openai_compatible` / `openai` / `anthropic` |
| **API Key** | LLM 平台密钥 | `sk-...` |
| **Base URL** | OpenAI 兼容接口地址 | `https://api.openai.com/v1` |
| **Model** | 使用的模型 | `gpt-4o` / `claude-3-5-sonnet-20241022` |
| **Max Tokens** | 最大输出长度 | `8192` |
| **Temperature** | 生成随机性 | `0.3` |
| **Use Docs** | 是否注入 HA 官方文档（本地缓存 7 天）| ✅ 推荐开启 |
| **Log Prompt** | 是否把 prompt 打到日志面板（调试用）| 默认关闭 |

### 可选：实体过滤

支持三种过滤方式，避免 LLM 拿到与你需求无关的实体：
- **区域过滤**：只传递选定区域内的实体
- **标签过滤**：按 HA 标签筛选
- **集成过滤**：只传递来自特定集成的实体（如只要米家、Z-Wave 的）

---

## 🚀 使用示例

### 创建一条自动化
```
模式选择 → 创建
"我希望周末早上 8 点打开卧室窗帘，工作日 7 点"
→ AI 可行性检查通过 → 生成 YAML → 预览 → 确认写入
```

### 优化已有自动化
```
模式选择 → 优化 → 选择"起床自动化"
→ AI 分析：意图明确，但缺少 description + 未考虑节假日
→ 追问："加上节假日判断" → AI 重新生成 → 确认写入
```

### 批量整合重复自动化
```
模式选择 → 聚合 → 一键分析
→ AI 识别出 3 组可合并（离家节能 / 睡前 / 起床）+ 2 条需修复
→ 逐条预览 → 勾选需要的 → 批量执行
```

---

## 📋 系统要求

- Home Assistant **2024.2.0** 或更高版本
- Python 3.11+（HA 自带）
- 一个可用的 LLM API 账号（OpenAI / Anthropic / DeepSeek / 本地 Ollama 等）

---

## 🔄 重装 / 升级说明

### 升级插件（HACS 推送新版本）
直接在 HACS 里 Update，重启 HA 即可。**你的 LLM 配置会保留**，不用重填 API Key。

### 彻底卸载并清空所有配置
如果需要完全重置（例如换 API Provider、或排查问题），仅卸载 HACS 是**不够的**：

```
设置 → 设备与服务 → HA LLM Automation → 右侧 ⋮ → 【删除集成】
         ↓ 这一步才会清除 API Key、模型设置等所有配置
HACS → HA LLM Automation → 移除
重启 HA
```

仅在 HACS 里 Remove，或者仅删除 `custom_components/ha_llm_automation/` 目录，配置会保留在 HA 的 `.storage/core.config_entries` 里，下次重装时自动恢复。

---

## ⚠️ 已知限制

- **YAML 型自动化**（写在 `automations.yaml` 里的）无法通过本工具读取/修改，只能操作"存储型"自动化（HA UI 或本工具创建的）。工具会自动过滤不可访问的条目。
- **删除 YAML 型自动化** 需要手动编辑 `automations.yaml`。
- **首次使用需要抓取 HA 官方文档**（约 7 个文件，一次性几秒钟，之后 7 天缓存）。
- **反向代理环境**建议 URL 不要加端口号，SSL 证书由代理处理。

---

## 🩹 面板白屏排障

打开 **LLM Automation** 侧边栏后整块白屏？按下面步骤逐一排查（1.0.3 起自带诊断保护，多数白屏会变成红色错误卡片；如果依然白屏说明是交付层问题）：

1. **确认实际加载的版本**
   浏览器 DevTools → **Network** → 过滤 `ha-llm`，刷新一次。看到请求 `…/ha_llm_automation/frontend/ha-llm-automation.js?v=1.0.3`（或更高）+ 状态 `200` 才算拿到新版。如果 `v=` 停留在旧版号 → Service Worker / HACS 没更新，继续下一步。

2. **硬刷新 + 无痕窗口**
   Mac `Shift + Cmd + R`，Windows `Ctrl + F5`；仍然白屏就用**无痕/隐私窗口**打开 HA URL —— 无痕窗口绕过 PWA Service Worker 缓存，可以一秒鉴别是代码问题还是缓存问题。

3. **看 Console**
   DevTools → **Console**。
   - 若有 **红色错误卡片**（1.0.3 起）：把卡片文字 + Console 堆栈复制到 issue，这是最有用的信息。
   - 若有 `SyntaxError` 但没看到错误卡片 → 浏览器加载的还是旧 JS，回到第 1 步。
   - 若 Console 干净但仍白屏 → 截图 Network + Console 到 issue。

4. **清前端缓存**
   HA 侧边栏 → **设置 → 面板**（或地址栏访问 `/config/dashboard`）→ 右上角三点 → **清除前端缓存**。之后刷新。

5. **HACS 重装兜底**
   HACS → HA LLM Automation → 更多 → **Redownload**（重新下载）→ 重启 HA。

---

## 🐛 问题反馈

遇到 bug 或有建议？欢迎提 [Issue](https://github.com/huangguabaiyi/ha-llm-automation/issues)。

提交时请附上：
- HA 版本
- 插件版本
- LLM Provider + 模型
- 日志面板截图（右上角"日志"Tab）

---

## 📝 开源许可

[MIT License](LICENSE) © 2026 huangguabaiyi

---

## 🙏 致谢

- [Home Assistant](https://www.home-assistant.io/) — 开源智能家居平台
- [HACS](https://hacs.xyz/) — Home Assistant 社区插件商店
- OpenAI / Anthropic 及各开源 LLM 社区

如果这个项目对你有用，欢迎点一颗 ⭐️ Star 支持！
