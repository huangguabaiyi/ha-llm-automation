from __future__ import annotations

import re
import time

import yaml
from pypinyin import lazy_pinyin

from .connection import HAConnection


def _to_ascii_alias(text: str) -> str:
    """将中文 alias 转为拼音 snake_case（纯 ASCII 不变）"""
    if all(ord(c) < 128 for c in text):
        return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "automation"
    words = lazy_pinyin(text)
    joined = "_".join(words)
    return re.sub(r"[^a-z0-9]+", "_", joined.lower()).strip("_") or "automation"

# HA 2024.10+ 使用复数形式；旧版使用单数形式
_TRIGGER_KEYS = ("triggers", "trigger")
_ACTION_KEYS  = ("actions",  "action")


class AutomationManager:
    """Home Assistant 自动化脚本管理（REST API）"""

    def __init__(self, conn: HAConnection):
        self._conn = conn

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_automations(self) -> list[dict]:
        """通过 states 接口列举所有自动化摘要"""
        states: list[dict] = self._conn.get("states")
        result = []
        for s in states:
            entity_id: str = s.get("entity_id", "")
            if not entity_id.startswith("automation."):
                continue
            attrs = s.get("attributes", {})
            result.append({
                "id": attrs.get("id", ""),
                "alias": attrs.get("friendly_name", entity_id),
                "description": "",
                "mode": attrs.get("mode", "single"),
                "entity_id": entity_id,
            })
        return result

    def get_automation(self, automation_id: str) -> dict:
        """获取单个自动化的完整配置"""
        return self._conn.get(f"config/automation/config/{automation_id}")

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def create_automation(self, config: dict) -> str:
        """
        创建新自动化并写入完整内容。
        HA 要求：
        - 必须有 description 字段（否则 triggers/actions 不持久化）
        - 必须有毫秒级时间戳 id（否则 HA UI 以为是未保存的新建页面）
        """
        validate_automation(config)
        before = {a["entity_id"] for a in self.list_automations()}

        # 注入 id（毫秒时间戳，与 HA 原生格式一致）
        payload = dict(config)
        payload["id"] = str(int(time.time() * 1000))

        self._conn.post("config/automation/config/new", payload)
        self._conn.post("services/automation/reload")

        # 等待新自动化出现
        for _ in range(8):
            time.sleep(1)
            after = self.list_automations()
            new_items = [a for a in after if a["entity_id"] not in before]
            if new_items:
                return new_items[-1]["id"] or new_items[-1]["entity_id"]

        raise RuntimeError("创建自动化后未能在 HA 中找到，请检查 HA 状态")

    def update_automation(self, automation_id: str, config: dict) -> bool:
        """更新已有自动化（POST 到 /{id}）"""
        validate_automation(config)
        self._conn.post(f"config/automation/config/{automation_id}", config)
        return True

    def delete_automation(self, automation_id: str) -> bool:
        """删除自动化"""
        return self._conn.delete(f"config/automation/config/{automation_id}")

    def reload_automations(self) -> bool:
        """触发 HA 重载自动化配置"""
        self._conn.post("services/automation/reload")
        return True

    # ------------------------------------------------------------------
    # 格式转换
    # ------------------------------------------------------------------

    def to_yaml(self, config: dict) -> str:
        return yaml.dump(config, allow_unicode=True, sort_keys=False, default_flow_style=False)

    def from_yaml(self, yaml_str: str) -> dict:
        result = yaml.safe_load(yaml_str)
        if not isinstance(result, dict):
            raise ValueError("YAML 内容必须是一个 mapping 对象")
        return result


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def unwrap_automation(config: dict) -> dict:
    """自动处理 LLM 多余的顶层 automation: 包装"""
    if list(config.keys()) == ["automation"] and isinstance(config["automation"], dict):
        return config["automation"]
    return config


def normalize_automation(config: dict) -> dict:
    """
    规范化自动化配置，使其能被 HA REST API 接受：
    1. 字段名：trigger->triggers, condition->conditions, action->actions
    2. 动作格式：service: -> action:（HA 2024.10+）
    3. alias：中文转拼音 ASCII（HA 用 alias 做标识符，必须 ASCII）
    4. description：补空字符串兜底（中文 description 通过 UTF-8 正常发送）
    """
    out = dict(config)

    # 字段名统一为复数
    for old, new in [("trigger", "triggers"), ("condition", "conditions"), ("action", "actions")]:
        if old in out and new not in out:
            out[new] = out.pop(old)

    # service: -> action:
    if "actions" in out and isinstance(out["actions"], list):
        new_actions = []
        for act in out["actions"]:
            if isinstance(act, dict) and "service" in act and "action" not in act:
                act = dict(act)
                act["action"] = act.pop("service")
            new_actions.append(act)
        out["actions"] = new_actions

    # alias 含非 ASCII -> 转拼音（HA 用 alias 做标识符，必须 ASCII）
    if "alias" in out:
        out["alias"] = _to_ascii_alias(str(out["alias"]))

    # description 含非 ASCII -> 替换常见 Unicode 符号为 ASCII 等价，再移除剩余非 ASCII
    # 不存在时补空字符串（HA 必须有此字段才能保存 triggers/actions）
    if "description" in out and out["description"]:
        desc = out["description"]
        _UNICODE_REPLACEMENTS = {"→": "->", "←": "<-", "↑": "^", "↓": "v",
                                  "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}
        for uc, asc in _UNICODE_REPLACEMENTS.items():
            desc = desc.replace(uc, asc)
        # 移除剩余非 ASCII 字符
        desc = "".join(c for c in desc if ord(c) < 128).strip()
        out["description"] = desc
    if "description" not in out:
        out["description"] = ""

    return out


def validate_automation(config: dict) -> None:
    """基础 schema 校验，兼容新版（triggers/actions）和旧版（trigger/action）"""
    if "alias" not in config:
        raise ValueError("自动化配置缺少必要字段: alias")

    trigger_key = next((k for k in _TRIGGER_KEYS if k in config), None)
    if trigger_key is None:
        raise ValueError("自动化配置缺少必要字段: triggers（或 trigger）")
    if not isinstance(config[trigger_key], list):
        raise ValueError(f"{trigger_key} 字段必须是列表")

    action_key = next((k for k in _ACTION_KEYS if k in config), None)
    if action_key is None:
        raise ValueError("自动化配置缺少必要字段: actions（或 action）")
    if not isinstance(config[action_key], list):
        raise ValueError(f"{action_key} 字段必须是列表")


def extract_yaml_from_text(text: str) -> str:
    """从 LLM 响应文本中提取 YAML 代码块"""
    pattern = r"```(?:yaml)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_automations_from_text(text: str) -> list[dict]:
    """
    从 LLM 响应文本中提取并解析所有自动化配置，返回 list[dict]。
    支持以下 LLM 输出格式：
    - 单个 dict（单条自动化）
    - list[dict]（多条自动化写在同一个 YAML 块里）
    - 多个独立 ```yaml``` 代码块（每块一条）
    - automation: dict/list 顶层包装
    """
    pattern = r"```(?:yaml)?\s*\n(.*?)```"
    blocks = re.findall(pattern, text, re.DOTALL)
    if not blocks:
        blocks = [text.strip()]

    results: list[dict] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        try:
            for doc in yaml.safe_load_all(block):
                if doc is None:
                    continue
                if isinstance(doc, list):
                    for item in doc:
                        if isinstance(item, dict):
                            results.append(unwrap_automation(item))
                elif isinstance(doc, dict):
                    # automation: [list] 包装
                    if list(doc.keys()) == ["automation"] and isinstance(doc["automation"], list):
                        for item in doc["automation"]:
                            if isinstance(item, dict):
                                results.append(item)
                    else:
                        results.append(unwrap_automation(doc))
        except Exception:
            continue
    return results


def extract_action_services(config: dict) -> set[str]:
    """
    递归提取 actions 中所有 action/service 字段值（即 service call 名称）。
    用于校验 LLM 是否把 entity_id 错误地填入了 action 字段。
    """
    services: set[str] = set()

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            for key in ("action", "service"):
                val = obj.get(key)
                if isinstance(val, str) and val:
                    services.add(val)
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    for key in ("actions", "action"):
        if key in config:
            _walk(config[key])
    return services


def extract_entity_ids(config: dict) -> set[str]:
    """
    递归提取自动化配置中所有 entity_id 值。
    覆盖 triggers / conditions / actions 各层级。
    """
    ids: set[str] = set()

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            val = obj.get("entity_id")
            if isinstance(val, str) and val:
                ids.add(val)
            elif isinstance(val, list):
                for v in val:
                    if isinstance(v, str) and v:
                        ids.add(v)
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    for key in ("triggers", "trigger", "conditions", "condition", "actions", "action"):
        if key in config:
            _walk(config[key])
    return ids
