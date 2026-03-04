# HA 自动化工具 — CLI 版

这是原始的命令行工具版本，保留用于本地直接调用。

## 快速开始

```bash
# 进入 cli_tool 目录
cd cli_tool

# 安装依赖（若使用虚拟环境请先激活）
pip install -r requirements.txt

# 复制配置文件并填写
cp config.example.json config.json
# 编辑 config.json，填入 HA URL、Token 和 LLM 配置

# 测试连接
python3 main.py test-connection

# 抓取 HA 官方文档（首次必做）
python3 main.py refresh-docs

# 启动交互式菜单
python3 main.py
```

## 命令速查

```bash
python3 main.py                              # 交互式模式菜单（推荐）
python3 main.py init                         # 交互式初始化配置
python3 main.py test-connection              # 测试 HA 连接
python3 main.py list-entities                # 查看实体列表
python3 main.py list-automations             # 查看自动化列表
python3 main.py create "需求描述"            # AI 创建自动化
python3 main.py create "需求" --dry-run      # 预览不写入
python3 main.py optimize [--id <id>]         # 优化单条自动化
python3 main.py consolidate [--dry-run]      # 批量整合自动化
python3 main.py backup list                  # 查看备份列表
python3 main.py backup restore               # 恢复备份
```

## 注意事项

- `config.json` 不提交到 git（含密钥），使用 `config.example.json` 作为模板
- CLI 调用方式改为从项目根目录运行：`python3 cli_tool/main.py`
  或 `cd cli_tool && python3 main.py`
