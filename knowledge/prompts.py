"""提示词构建模块"""
from __future__ import annotations


def build_system_prompt(
    docs: dict[str, str],
    entities: list[dict],
    visible_domains: set[str] | None = None,
) -> str:
    """
    构建包含 HA 文档知识和实体列表的 System Prompt。

    docs: {key: markdown_content}
    entities: EntitySummary 列表
    visible_domains: 可见 domain 集合，None 时使用默认白名单
    """
    sections: list[str] = [_ROLE_PROMPT]

    if docs:
        sections.append(_build_doc_section(docs))

    if entities:
        sections.append(_build_entity_section(entities, visible_domains=visible_domains))

    sections.append(_OUTPUT_RULES)
    return "\n\n".join(sections)


# ------------------------------------------------------------------
# 固定提示词片段
# ------------------------------------------------------------------

_ROLE_PROMPT = """\
你是一名 Home Assistant 自动化专家，能够根据用户的自然语言描述，\
生成标准的 Home Assistant 自动化 YAML 配置。

你的职责：
1. 理解用户意图，生成完整、可直接使用的 HA 自动化 YAML
2. 优先使用用户已有的实体（见下方实体列表）
3. 严格遵守 HA 自动化语法规范（见下方文档参考）
4. 如有不确定之处，优先选择简单可靠的实现方式
5. 不要编造不存在的实体 ID\
"""

_OUTPUT_RULES = """\
## 输出规范

- 必须输出完整的 YAML 配置，用 ```yaml ... ``` 代码块包裹
- 顶层字段直接写，【绝对不要】在外面包一层 `automation:` 键

### 必须使用 HA 2024+ 新版字段名（全部用复数）：
  - `triggers:` （不是 trigger:）
  - `conditions:` （不是 condition:，无条件时写 conditions: []）
  - `actions:` （不是 action:）

### actions 内部动作格式：
  - 调用服务用 `action:` 字段（不是 service:）
  - 例：`action: light.turn_off`

### alias 必须是英文 snake_case（HA API 不支持中文 alias）：
  - 正确：`alias: close_light_at_22`
  - 错误：`alias: 每天晚上关灯`

### 正确示例：
```yaml
alias: close_light_at_22
triggers:
  - trigger: time
    at: "22:00:00"
conditions: []
actions:
  - action: light.turn_off
    target:
      entity_id: light.deng
mode: single
```

### description 字段规范（唯一会被 HA 持久化保存的备注）：
  - 必填，用**纯英文 ASCII**描述自动化逻辑，格式：`trigger -> action`
  - 有条件判断时：`trigger -> condition check -> action`
  - 示例：`description: "Every day at 22:00 -> turn off all living room lights"`
  - 示例：`description: "Living room occupied -> turn on lights"`
  - 【严格要求】只能使用 ASCII 字符，箭头必须用 `->` 而非 `→`（Unicode 箭头会导致写入失败）

### 实体选择规则：
- **只能使用上方实体列表中出现的 entity_id**，禁止编造不存在的实体
- 用户提到特定房间/区域时，**只选择该区域列中对应的实体**，不要跨区域使用
- 如果指定区域没有满足条件的实体，在代码块外明确说明

- 如果需要说明，在代码块外用中文解释
- YAML 中的字符串值如包含特殊字符，必须加引号\
"""


def _build_doc_section(docs: dict[str, str], max_chars: int = 12000) -> str:
    """构建文档参考章节，总长度不超过 max_chars"""
    parts = ["## Home Assistant 自动化语法参考\n"]
    used = 0
    priority_keys = [
        "automation_basic", "automation_trigger",
        "automation_condition", "automation_action",
        "scripts", "service_calls", "templating",
    ]
    ordered = sorted(docs.keys(), key=lambda k: priority_keys.index(k) if k in priority_keys else 99)

    for key in ordered:
        content = docs[key]
        # 截取每个文档前 N 字符
        budget = max_chars - used
        if budget <= 200:
            break
        chunk = content[:min(budget, 2500)]
        parts.append(f"### {key}\n\n{chunk}\n")
        used += len(chunk)

    return "\n".join(parts)


# 默认可见 domain 白名单（可通过 config.json 的 domains.visible 覆盖）
DEFAULT_VISIBLE_DOMAINS: set[str] = {
    # 可控设备（常用于 action）
    "light", "switch", "climate", "cover", "fan",
    "media_player", "lock", "vacuum", "scene", "script",
    "button", "select", "number",
    # 输入辅助（可做 trigger 也可做 action）
    "input_boolean", "input_select", "input_number", "input_text",
    # 传感器（常用于 trigger/condition）
    "sensor", "binary_sensor", "device_tracker",
    # 其他常用
    "todo", "calendar", "timer", "counter", "weather", "person",
}

# 全局/虚拟类 domain：不属于具体房间，单独列在顶部区域组之前
_GLOBAL_DOMAINS: set[str] = {
    "todo", "calendar", "timer", "counter", "weather",
    "person", "input_boolean", "input_select", "input_number", "input_text",
    "script", "scene",
}


def _build_entity_section(
    entities: list[dict],
    max_entities: int = 150,
    visible_domains: set[str] | None = None,
) -> str:
    """构建实体列表章节（全局实体顶部展示，物理实体按区域分组，含 domain 列）"""
    domains = visible_domains if visible_domains is not None else DEFAULT_VISIBLE_DOMAINS
    _NO_AREA = "（未分配区域）"

    # 分为"全局/虚拟"和"物理/区域"两类
    global_entities: list[dict] = []
    area_groups: dict[str, list[dict]] = {}

    for e in entities:
        domain = e.get("domain", "")
        if domain not in domains:
            continue
        if domain in _GLOBAL_DOMAINS:
            global_entities.append(e)
        else:
            area = e.get("area") or _NO_AREA
            area_groups.setdefault(area, []).append(e)

    if not global_entities and not area_groups:
        return "## 当前可用实体列表\n\n（无可用实体）"

    lines = [
        "## 可用实体",
        "",
        "说明：light/switch/climate/fan/cover 等可作为 action 目标；"
        "sensor/binary_sensor/todo/calendar 等可作为 trigger/condition 来源；"
        "input_boolean/input_select/script 等两者皆可。",
    ]
    total = 0

    # 全局实体优先展示
    if global_entities:
        lines.append("\n### 全局服务与虚拟实体")
        lines.append("entity_id | domain | 名称 | 状态")
        lines.append("--- | --- | --- | ---")
        for e in global_entities:
            if total >= max_entities:
                break
            lines.append(
                f"{e.get('entity_id','')} | {e.get('domain','')} | "
                f"{e.get('friendly_name','')} | {e.get('state','')}"
            )
            total += 1

    # 物理实体按区域分组
    for area in sorted(area_groups.keys(), key=lambda a: (a == _NO_AREA, a)):
        if total >= max_entities:
            break
        lines.append(f"\n### {area}")
        lines.append("entity_id | domain | 名称 | 状态")
        lines.append("--- | --- | --- | ---")
        for e in area_groups[area]:
            if total >= max_entities:
                break
            lines.append(
                f"{e.get('entity_id','')} | {e.get('domain','')} | "
                f"{e.get('friendly_name','')} | {e.get('state','')}"
            )
            total += 1

    total_all = len(global_entities) + sum(len(v) for v in area_groups.values())
    if total >= max_entities and total_all > max_entities:
        lines.append(f"\n（实体过多，仅展示前 {max_entities} 个）")

    return "\n".join(lines)


def build_feasibility_prompt(
    entities: list[dict],
    visible_domains: set[str] | None = None,
) -> str:
    """
    构建可行性检查阶段的 System Prompt（Step 1）。
    LLM 需分析用户需求是否可行，并严格返回 JSON。
    """
    entity_section = _build_entity_section(entities, visible_domains=visible_domains)
    return f"""\
你是一名 Home Assistant 自动化分析专家。
你的任务是：根据以下实体列表，分析用户的自动化需求是否可行。

{entity_section}

## 分析步骤
1. 理解需求：推断实现这个自动化需要哪些类型的设备参与（例如：感知状态的传感器、执行操作的可控设备、特定区域的灯/开关等）
2. 在实体列表中搜索所有参与设备，找出能满足需求的具体 entity_id
3. 判断每类必要设备是否都能找到；若有任何一类缺失，则不可行

## 输出格式（严格 JSON，不加代码块、不加任何其他文字）
可行时：
{{"feasible": true, "entities": ["entity_id_1", "entity_id_2"], "reason": "找到驾照传感器和测试房间的可控设备"}}

不可行时：
{{"feasible": false, "entities": [], "reason": "该区域没有可控设备，无法完成此操作"}}

requirements:
- 返回纯 JSON，不要 markdown 代码块
- entities 列出实现该自动化所需的**全部**实体 ID
- reason 用中文简短说明\
"""
