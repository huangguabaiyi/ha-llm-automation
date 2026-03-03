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
- 如果用户要求创建多条自动化，**每条自动化单独用一个 ```yaml``` 代码块输出**，不要合并成列表，不要用 `---` 分隔在同一块里
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
description: "Every day at 22:00, turn off the living room light (light.deng) to save energy at night"
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
  - 必填，用**纯英文 ASCII** 写一段完整的功能说明，要让人一眼看出这个自动化做什么
  - 内容要求：
    1. **触发条件**：何时/何种情况下触发（时间、传感器状态、设备变化等）
    2. **判断条件**（有则写）：满足什么额外条件才执行
    3. **执行动作**：对哪些设备做了什么操作（开/关/调节/通知等）
  - 格式建议：用完整英文句子，不要只写箭头缩写；多个动作用逗号分隔
  - 示例：
    - `description: "Every day at 22:00, turn off all lights in the living room (light.sofa, light.ceiling)"`
    - `description: "When motion sensor in bedroom detects motion between 22:00-07:00, dim bedroom light to 10% brightness"`
    - `description: "When todo list gets a new item tagged urgent, send a notification and turn on the study room light"`
    - `description: "When living room temperature exceeds 26C and someone is home, turn on the air conditioner and set to 24C cool mode"`
  - 【严格要求】只能使用 ASCII 字符，箭头必须用 `->` 或完整句子，绝不能用 `→`（Unicode 箭头会导致写入失败）

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


def build_optimize_analysis_prompt(
    automation_yaml: str,
    entities: list[dict],
    visible_domains: set[str] | None = None,
) -> str:
    """
    构建单条自动化优化 Step 1 分析提示词。
    LLM 需理解意图、找出问题并给出优化建议，严格返回 JSON。
    """
    entity_section = _build_entity_section(entities, visible_domains=visible_domains)
    return f"""\
你是一名 Home Assistant 自动化专家，负责分析已有自动化的意图并找出优化点。

## 要分析的自动化 YAML

```yaml
{automation_yaml}
```

{entity_section}

## 分析任务
1. 理解这条自动化的功能意图（它想做什么，为了什么目的）
2. 列出它实际涉及的实体 ID
3. 找出存在的问题，例如：description 缺失或过于简短、引用了不存在的实体、逻辑不完整、缺少合理 conditions 等
4. 提出具体优化建议，例如：补充同意图相关的同类设备、完善 conditions、统一字段格式到 HA 2024+ 规范等

## 输出格式（严格 JSON，不加代码块，不加任何其他文字）
{{"intent": "用中文描述该自动化的功能意图（1-2句话）", "related_entities": ["entity_id_1", "entity_id_2"], "issues": ["问题1", "问题2"], "suggestions": ["建议1", "建议2"]}}

requirements:
- 返回纯 JSON，不要 markdown 代码块
- issues 和 suggestions 用中文描述，没有问题时返回空数组
- related_entities 只列出自动化中真正引用的实体 ID\
"""


def build_optimize_yaml_prompt(
    automation_yaml: str,
    analysis: dict,
    entities: list[dict],
    docs: dict[str, str] | None = None,
    visible_domains: set[str] | None = None,
) -> str:
    """
    构建单条自动化优化 Step 2 YAML 生成提示词。
    基于 Step 1 的分析结果，生成优化后的完整 YAML。
    """
    sections: list[str] = [_ROLE_PROMPT]

    if docs:
        sections.append(_build_doc_section(docs))

    if entities:
        sections.append(_build_entity_section(entities, visible_domains=visible_domains))

    intent = analysis.get("intent", "")
    issues = analysis.get("issues", [])
    suggestions = analysis.get("suggestions", [])

    analysis_lines = [f"功能意图：{intent}"]
    if issues:
        analysis_lines.append("发现的问题：\n" + "\n".join(f"  - {i}" for i in issues))
    if suggestions:
        analysis_lines.append("优化建议：\n" + "\n".join(f"  - {s}" for s in suggestions))

    sections.append(f"""\
## 优化任务

请基于以下分析，对这条 Home Assistant 自动化进行优化并输出完整的新 YAML 配置。

### 原始配置
```yaml
{automation_yaml}
```

### 分析报告
{chr(10).join(analysis_lines)}

优化要求：
- 必须保留原有核心功能，不得改变自动化的主要意图
- 修正分析中列出的所有问题
- 落实分析中的优化建议（如补充同类设备、完善 conditions 等）
- 如原配置 description 缺失或过短，务必补充完整的英文描述\
""")

    sections.append(_OUTPUT_RULES)
    return "\n\n".join(sections)


def build_consolidate_prompt(
    automations_data: list[dict],
    entities: list[dict],
    visible_domains: set[str] | None = None,
    max_total_chars: int = 40000,
) -> str:
    """
    构建多条自动化批量整合分析提示词。
    automations_data: list of {id, alias, yaml_str}
    LLM 返回 JSON {merge_groups, fix_items, ok_items}。
    """
    entity_section = _build_entity_section(entities, visible_domains=visible_domains)

    # 构建自动化 YAML 列表，限制总字符数
    auto_parts: list[str] = []
    total_chars = 0
    truncated = 0
    for auto in automations_data:
        block = f"### [{auto['id']}] {auto['alias']}\n```yaml\n{auto['yaml_str']}\n```"
        if total_chars + len(block) > max_total_chars:
            truncated = len(automations_data) - len(auto_parts)
            break
        auto_parts.append(block)
        total_chars += len(block)

    automations_str = "\n\n".join(auto_parts)
    truncation_note = f"\n\n（注意：共 {len(automations_data)} 条自动化，因 token 限制仅分析前 {len(auto_parts)} 条）" if truncated else ""

    return f"""\
你是一名 Home Assistant 自动化专家，负责分析一组自动化并提出整合优化方案。

{entity_section}

## 当前所有自动化配置{truncation_note}

{automations_str}

## 分析任务
1. 找出功能高度重复或触发/动作相似的自动化，建议合并为一条
2. 找出引用了不存在的实体、逻辑错误或字段格式问题的自动化，建议纠正
3. 其余运行良好的自动化标记为 ok，不做变动

## 输出格式（严格 JSON，不加代码块）
{{"merge_groups": [{{"ids": ["id1", "id2"], "aliases": ["alias1", "alias2"], "reason": "中文说明为什么可以合并", "merged_yaml": "合并后完整YAML（用\\n换行，不要加代码块标记）"}}], "fix_items": [{{"id": "id3", "alias": "alias3", "issue": "中文说明存在什么问题", "fixed_yaml": "修复后完整YAML（用\\n换行，不要加代码块标记）"}}], "ok_items": [{{"id": "id4", "alias": "alias4"}}]}}

requirements:
- 返回纯 JSON，不要 markdown 代码块
- merged_yaml 和 fixed_yaml 是完整合法的自动化 YAML 字符串，换行用 \\n 转义
- alias 必须是英文 snake_case，description 必须是纯 ASCII 英文句子
- 如无需合并/修复，对应列表返回空数组 []\
"""


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
1. 理解需求：推断实现这些自动化需要哪些类型的设备参与（传感器、可控设备、特定区域的灯/开关等）
2. 如果用户要求创建多条自动化，为**所有条**的实现方案一起规划所需实体
3. 在实体列表中搜索所有参与设备，找出能满足需求的具体 entity_id（返回所有自动化所需实体的并集）
4. 判断所需设备是否存在；若关键设备完全缺失，则不可行

## 输出格式（严格 JSON，不加代码块、不加任何其他文字）
可行时：
{{"feasible": true, "entities": ["entity_id_1", "entity_id_2"], "reason": "找到测试房间的灯、开关、传感器等设备，可创建多条测试自动化"}}

不可行时：
{{"feasible": false, "entities": [], "reason": "该区域没有可控设备，无法完成此操作"}}

requirements:
- 返回纯 JSON，不要 markdown 代码块
- entities 列出**所有**自动化所需的实体 ID 并集
- reason 用中文简短说明\
"""
