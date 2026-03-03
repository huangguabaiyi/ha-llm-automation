"""提示词构建模块"""


def build_system_prompt(docs: dict[str, str], entities: list[dict]) -> str:
    """
    构建包含 HA 文档知识和实体列表的 System Prompt。

    docs: {key: markdown_content}
    entities: EntitySummary 列表
    """
    sections: list[str] = [_ROLE_PROMPT]

    # --- HA 文档知识 ---
    if docs:
        doc_section = _build_doc_section(docs)
        sections.append(doc_section)

    # --- 可用实体列表 ---
    if entities:
        entity_section = _build_entity_section(entities)
        sections.append(entity_section)

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

### 实体选择规则：
- **只能使用上方实体列表中出现的 entity_id**，禁止编造不存在的实体
- 用户提到特定房间/区域时，**只选择该区域列中对应的实体**，不要跨区域使用
- 实体列表中有"区域"列时，严格按区域过滤
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


# domain 分类白名单
_CONTROLLABLE_DOMAINS = {
    "light", "switch", "climate", "cover", "fan",
    "media_player", "lock", "vacuum", "select", "number",
    "button", "scene", "script",
}
_SENSOR_DOMAINS = {
    "sensor", "binary_sensor", "input_boolean",
    "input_number", "device_tracker",
}


def _build_entity_section(entities: list[dict], max_entities: int = 150) -> str:
    """构建实体列表章节（按区域+类型两级分组）"""
    has_area = any(e.get("area") for e in entities)

    if not has_area:
        # 无区域信息时降级为平铺表格（只保留可展示 domain）
        lines = ["## 当前可用实体列表\n"]
        lines.append("entity_id | 名称 | 状态")
        lines.append("--- | --- | ---")
        count = 0
        for e in entities:
            domain = e.get("domain", "")
            if domain not in _CONTROLLABLE_DOMAINS and domain not in _SENSOR_DOMAINS:
                continue
            if count >= max_entities:
                break
            lines.append(f"{e.get('entity_id','')} | {e.get('friendly_name','')} | {e.get('state','')}")
            count += 1
        return "\n".join(lines)

    # 按区域分组，unknown 区域放到最后
    _NO_AREA = "（未分配区域）"
    area_groups: dict[str, list[dict]] = {}
    for e in entities:
        domain = e.get("domain", "")
        if domain not in _CONTROLLABLE_DOMAINS and domain not in _SENSOR_DOMAINS:
            continue
        area = e.get("area") or _NO_AREA
        area_groups.setdefault(area, []).append(e)

    lines = ["## 可用实体（按区域和类型分类）\n"]
    total = 0

    for area in sorted(area_groups.keys(), key=lambda a: (a == _NO_AREA, a)):
        if total >= max_entities:
            break
        lines.append(f"\n### {area}")

        ents = area_groups[area]
        controllable = [e for e in ents if e.get("domain", "") in _CONTROLLABLE_DOMAINS]
        sensors = [e for e in ents if e.get("domain", "") in _SENSOR_DOMAINS]

        if controllable:
            lines.append("**可控设备**（可作为 action 目标）")
            lines.append("entity_id | 名称 | 状态")
            lines.append("--- | --- | ---")
            for e in controllable:
                if total >= max_entities:
                    break
                lines.append(f"{e.get('entity_id','')} | {e.get('friendly_name','')} | {e.get('state','')}")
                total += 1

        if sensors:
            lines.append("**传感器/触发器**（可作为 trigger/condition 来源）")
            lines.append("entity_id | 名称 | 状态")
            lines.append("--- | --- | ---")
            for e in sensors:
                if total >= max_entities:
                    break
                lines.append(f"{e.get('entity_id','')} | {e.get('friendly_name','')} | {e.get('state','')}")
                total += 1

    if total >= max_entities and sum(len(v) for v in area_groups.values()) > max_entities:
        lines.append(f"\n（实体过多，仅展示前 {max_entities} 个）")

    return "\n".join(lines)


def build_feasibility_prompt(entities: list[dict]) -> str:
    """
    构建可行性检查阶段的 System Prompt（Step 1）。
    LLM 需分析用户需求是否可行，并严格返回 JSON。
    """
    entity_section = _build_entity_section(entities)
    return f"""\
你是一名 Home Assistant 自动化分析专家。
你的任务是：根据以下实体列表，分析用户的自动化需求是否可行。

{entity_section}

## 分析规则
1. 找出与需求相关的区域和设备
2. 判断该区域是否存在满足需求的可控设备或传感器
3. **只能使用上方列表中出现的 entity_id**

## 输出格式（严格 JSON，不加代码块、不加任何其他文字）
可行时：
{{"feasible": true, "entities": ["entity_id_1", "entity_id_2"], "reason": "找到客厅的可控灯光设备"}}

不可行时：
{{"feasible": false, "entities": [], "reason": "该区域没有可控设备，无法完成此操作"}}

requirements:
- 返回纯 JSON，不要 markdown 代码块
- entities 只列出本次需求真正需要的实体 ID
- reason 用中文简短说明\
"""
