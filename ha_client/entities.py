from __future__ import annotations

import time
from typing import Any

from .connection import HAConnection
from .ws_client import HAWebSocketClient

# 传给 LLM 时保留的 attribute 白名单（按 domain）
_ATTR_WHITELIST: dict[str, list[str]] = {
    "light": ["brightness", "color_temp", "rgb_color", "supported_features"],
    "climate": ["temperature", "current_temperature", "hvac_mode", "hvac_modes"],
    "cover": ["current_position", "supported_features"],
    "media_player": ["media_title", "source", "volume_level", "state"],
    "sensor": ["unit_of_measurement", "device_class", "state_class"],
    "binary_sensor": ["device_class"],
}
_DEFAULT_TTL = 300  # 5 分钟


class EntityManager:
    """实体与设备信息管理"""

    def __init__(
        self,
        conn: HAConnection,
        cache_ttl: int = _DEFAULT_TTL,
        exclude_ids: set[str] | None = None,
    ):
        self._conn = conn
        self._cache_ttl = cache_ttl
        self._exclude_ids: set[str] = exclude_ids or set()
        self._cache: list[dict] | None = None
        self._cache_ts: float = 0.0

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def get_all_entities(self, force_refresh: bool = False) -> list[dict]:
        """获取全量实体摘要列表（带缓存）"""
        if force_refresh or self._is_cache_stale():
            self._refresh_cache()
        return self._cache or []

    def get_entities_by_domain(self, domain: str) -> list[dict]:
        """按 domain 过滤实体"""
        return [e for e in self.get_all_entities() if e["domain"] == domain]

    def search_entities(self, keyword: str) -> list[dict]:
        """按 entity_id 或 friendly_name 模糊搜索"""
        kw = keyword.lower()
        return [
            e for e in self.get_all_entities()
            if kw in e["entity_id"].lower()
            or kw in e.get("friendly_name", "").lower()
        ]

    def get_entity_state(self, entity_id: str) -> dict:
        """获取单个实体的完整状态（不走缓存）"""
        return self._conn.get(f"states/{entity_id}")

    def refresh_cache(self) -> None:
        """强制刷新缓存"""
        self._refresh_cache()

    def list_domains(self) -> list[str]:
        """列出所有存在的 domain"""
        domains = {e["domain"] for e in self.get_all_entities()}
        return sorted(domains)

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _is_cache_stale(self) -> bool:
        return self._cache is None or (time.time() - self._cache_ts) > self._cache_ttl

    def _refresh_cache(self) -> None:
        raw: list[dict] = self._conn.get("states")
        _SKIP_STATES = {"unavailable", "unknown"}
        self._cache = [
            self._summarize(e) for e in raw
            if e.get("state", "") not in _SKIP_STATES
            and e.get("entity_id", "") not in self._exclude_ids
        ]
        self._cache_ts = time.time()

    def _summarize(self, entity: dict) -> dict:
        """精简实体信息，减少传给 LLM 的 token 数量"""
        entity_id: str = entity.get("entity_id", "")
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        attrs: dict[str, Any] = entity.get("attributes", {})

        # 只保留白名单 attribute，其余省略
        allowed_keys = _ATTR_WHITELIST.get(domain, [])
        filtered_attrs = {k: attrs[k] for k in allowed_keys if k in attrs}
        # friendly_name 单独处理
        friendly_name = attrs.get("friendly_name", "")

        return {
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "domain": domain,
            "state": entity.get("state", ""),
            "area": "",  # 由 enrich_entities_with_areas() 填充
            "attributes": filtered_attrs,
        }


def fetch_registry_data(config: dict) -> dict:
    """
    通过 WebSocket 获取实体注册表完整数据，返回：
      area_map:    {entity_id: area_name}  — 含区域的实体映射
      exclude_ids: set[str]                — 需要从实体列表排除的 entity_id
                   (disabled_by != null / hidden_by != null /
                    entity_category in ("diagnostic", "config"))
    失败时返回 {"area_map": {}, "exclude_ids": set()}（不阻断主流程）。
    """
    try:
        ws = HAWebSocketClient(config)
        areas_raw = ws.get_area_registry()
        entities_raw = ws.get_entity_registry()
        devices_raw = ws.get_device_registry()
    except Exception:
        return {"area_map": {}, "exclude_ids": set()}

    # area_id -> area_name
    area_id_to_name: dict[str, str] = {
        a["area_id"]: a["name"] for a in areas_raw if "area_id" in a
    }

    # device_id -> area_id（设备层面的区域分配）
    device_area: dict[str, str] = {}
    for dev in devices_raw:
        did = dev.get("id", "")
        aid = dev.get("area_id") or ""
        if did and aid:
            device_area[did] = aid

    _EXCLUDE_CATEGORIES = {"diagnostic", "config"}
    area_map: dict[str, str] = {}
    exclude_ids: set[str] = set()

    for ent in entities_raw:
        eid = ent.get("entity_id", "")
        if not eid:
            continue

        # 排除禁用/隐藏/诊断配置类实体
        if ent.get("disabled_by") is not None:
            exclude_ids.add(eid)
            continue
        if ent.get("hidden_by") is not None:
            exclude_ids.add(eid)
            continue
        if ent.get("entity_category") in _EXCLUDE_CATEGORIES:
            exclude_ids.add(eid)
            continue

        # 实体层优先，否则继承设备层区域
        area_id = ent.get("area_id") or device_area.get(ent.get("device_id", ""), "")
        if area_id:
            area_map[eid] = area_id_to_name.get(area_id, area_id)

    return {"area_map": area_map, "exclude_ids": exclude_ids}


def fetch_entity_area_map(config: dict) -> dict[str, str]:
    """
    通过 WebSocket 获取 entity_id -> area_name 映射。
    HA 中区域可分配在实体层或设备层，此处两级都查：
      实体自身 area_id > 所属设备 area_id
    失败时返回空 dict（不阻断主流程）。
    """
    try:
        ws = HAWebSocketClient(config)
        areas_raw = ws.get_area_registry()
        entities_raw = ws.get_entity_registry()
        devices_raw = ws.get_device_registry()
    except Exception:
        return {}

    # area_id -> area_name
    area_id_to_name: dict[str, str] = {
        a["area_id"]: a["name"] for a in areas_raw if "area_id" in a
    }

    # device_id -> area_id（设备层面的区域分配）
    device_area: dict[str, str] = {}
    for dev in devices_raw:
        did = dev.get("id", "")
        aid = dev.get("area_id") or ""
        if did and aid:
            device_area[did] = aid

    result: dict[str, str] = {}
    for ent in entities_raw:
        eid = ent.get("entity_id", "")
        if not eid:
            continue
        # 实体层优先，否则继承设备层区域
        area_id = ent.get("area_id") or device_area.get(ent.get("device_id", ""), "")
        if area_id:
            result[eid] = area_id_to_name.get(area_id, area_id)
    return result


def enrich_entities_with_areas(
    entities: list[dict], area_map: dict[str, str]
) -> list[dict]:
    """将 area_map 中的区域名注入实体列表（原地修改副本）"""
    if not area_map:
        return entities
    enriched = []
    for e in entities:
        entry = dict(e)
        entry["area"] = area_map.get(e["entity_id"], "")
        enriched.append(entry)
    return enriched
