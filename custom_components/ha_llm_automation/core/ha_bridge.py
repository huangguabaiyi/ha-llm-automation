"""
HABridge — 用 HA 内置对象替代 cli_tool/ha_client 的 REST 调用。

- 实体读取：直接使用 hass.states / entity_registry / area_registry / device_registry
- 自动化 CRUD：通过 aiohttp REST（HA 内部地址 http://localhost:8123）
- 自动化 reload：hass.services.async_call("automation", "reload")
- 访问令牌：setup 阶段获取 refresh_token 对象（长期有效），每次 REST 调用实时生成新 access_token（避免 30 分钟过期）
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

_LOGGER = logging.getLogger(__name__)

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .automations_utils import validate_automation


class HABridge:
    """用 hass 内置对象替代 httpx REST 调用。"""

    def __init__(self, hass: HomeAssistant, refresh_token):
        """
        refresh_token: setup 阶段创建的 refresh_token 对象（长期有效，不过期）
        每次 REST 调用通过 _headers() 实时生成新的 access_token（30分钟内有效）
        """
        self._hass = hass
        self._refresh_token = refresh_token
        self._base_url = "http://localhost:8123"

    # ------------------------------------------------------------------
    # 实体（直接使用 HA Python API，无需 REST）
    # ------------------------------------------------------------------

    async def get_all_states(self) -> list[dict]:
        """获取全量实体状态（等价于 GET /api/states）"""
        states = self._hass.states.async_all()
        return [s.as_dict() for s in states]

    async def get_entity_registry(self) -> list[dict]:
        """获取实体注册表"""
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self._hass)
        return [
            {
                "entity_id": entry.entity_id,
                "device_id": entry.device_id,
                "area_id": entry.area_id,
                "disabled_by": entry.disabled_by.value if entry.disabled_by else None,
                "hidden_by": entry.hidden_by.value if entry.hidden_by else None,
                "entity_category": entry.entity_category.value if entry.entity_category else None,
            }
            for entry in registry.entities.values()
        ]

    async def get_area_registry(self) -> list[dict]:
        """获取区域注册表"""
        from homeassistant.helpers import area_registry as ar
        registry = ar.async_get(self._hass)
        return [
            {"area_id": area.id, "name": area.name}
            for area in registry.areas.values()
        ]

    async def get_device_registry(self) -> list[dict]:
        """获取设备注册表"""
        from homeassistant.helpers import device_registry as dr
        registry = dr.async_get(self._hass)
        return [
            {"id": device.id, "area_id": device.area_id}
            for device in registry.devices.values()
        ]

    async def get_labels(self) -> list[dict]:
        """获取标签注册表"""
        try:
            from homeassistant.helpers import label_registry as lr
            registry = lr.async_get(self._hass)
            return [{"label_id": l.label_id, "name": l.name} for l in registry.labels.values()]
        except Exception:
            return []

    async def get_entity_platforms(self) -> list[str]:
        """获取所有集成平台名称列表"""
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self._hass)
        return sorted({e.platform for e in registry.entities.values() if e.platform})

    async def get_entities(
        self,
        extra_visible_domains: set[str] | None = None,
        hidden_domains: set[str] | None = None,
        area_filter: list[str] | None = None,
        label_filter: list[str] | None = None,
        integration_filter: list[str] | None = None,
    ) -> list[dict]:
        """
        三步合一：注册表 → 过滤 → 注入区域 → 返回实体列表。
        返回格式与 cli_tool/main.py 的 get_entities() 一致。
        支持额外的 area_filter / label_filter / integration_filter 过滤。
        """
        # 获取注册表数据
        try:
            entities_raw = await self.get_entity_registry()
            areas_raw = await self.get_area_registry()
            devices_raw = await self.get_device_registry()
        except Exception:
            entities_raw = []
            areas_raw = []
            devices_raw = []

        # 构建映射
        area_id_to_name: dict[str, str] = {a["area_id"]: a["name"] for a in areas_raw}
        device_area: dict[str, str] = {
            d["id"]: d["area_id"] for d in devices_raw if d.get("area_id")
        }

        _EXCLUDE_CATEGORIES = {"diagnostic", "config"}
        area_map: dict[str, str] = {}
        exclude_ids: set[str] = set()

        # 用于额外过滤的辅助映射
        entity_area_id: dict[str, str] = {}  # entity_id -> area_id (raw)
        entity_labels: dict[str, set[str]] = {}  # entity_id -> set of label_ids
        entity_platform: dict[str, str] = {}  # entity_id -> platform

        # 从实体注册表获取 labels 和 platform（需要原始对象）
        try:
            from homeassistant.helpers import entity_registry as er
            er_registry = er.async_get(self._hass)
            for e in er_registry.entities.values():
                entity_platform[e.entity_id] = e.platform or ""
                if hasattr(e, "labels"):
                    entity_labels[e.entity_id] = set(e.labels) if e.labels else set()
        except Exception:
            pass

        # 若 integration_filter 生效但 entity_platform 为空（注册表读取失败），
        # 则禁用集成过滤，避免因平台信息缺失导致所有实体被错误过滤掉
        if integration_filter and not entity_platform:
            _LOGGER.warning("ha_bridge: entity_platform 为空，integration_filter 已禁用")
            integration_filter = None

        for ent in entities_raw:
            eid = ent.get("entity_id", "")
            if not eid:
                continue
            if ent.get("disabled_by") is not None:
                exclude_ids.add(eid)
                continue
            if ent.get("hidden_by") is not None:
                exclude_ids.add(eid)
                continue
            if ent.get("entity_category") in _EXCLUDE_CATEGORIES:
                exclude_ids.add(eid)
                continue
            area_id = ent.get("area_id") or device_area.get(ent.get("device_id", ""), "")
            if area_id:
                area_map[eid] = area_id_to_name.get(area_id, area_id)
                entity_area_id[eid] = area_id

        # 从 states 获取实体
        all_states = await self.get_all_states()
        _ATTR_WHITELIST: dict[str, list[str]] = {
            "light": ["brightness", "color_temp", "rgb_color", "supported_features"],
            "climate": ["temperature", "current_temperature", "hvac_mode", "hvac_modes"],
            "cover": ["current_position", "supported_features"],
            "media_player": ["media_title", "source", "volume_level", "state"],
            "sensor": ["unit_of_measurement", "device_class", "state_class"],
            "binary_sensor": ["device_class"],
        }
        _SKIP_STATES = {"unavailable", "unknown"}

        # 准备过滤集合
        area_filter_set: set[str] | None = set(area_filter) if area_filter else None
        label_filter_set: set[str] | None = set(label_filter) if label_filter else None
        integration_filter_set: set[str] | None = set(integration_filter) if integration_filter else None

        entities: list[dict] = []
        for s in all_states:
            entity_id = s.get("entity_id", "")
            if not entity_id or entity_id in exclude_ids:
                continue
            state_val = s.get("state", "")
            if state_val in _SKIP_STATES:
                continue

            # 区域过滤
            if area_filter_set is not None:
                eid_area = entity_area_id.get(entity_id, "")
                if eid_area not in area_filter_set:
                    continue

            # 标签过滤
            if label_filter_set is not None:
                eid_labels = entity_labels.get(entity_id, set())
                if not eid_labels.intersection(label_filter_set):
                    continue

            # 集成过滤
            if integration_filter_set is not None:
                eid_platform = entity_platform.get(entity_id, "")
                if eid_platform not in integration_filter_set:
                    continue

            domain = entity_id.split(".")[0] if "." in entity_id else ""
            attrs = s.get("attributes", {})
            allowed_keys = _ATTR_WHITELIST.get(domain, [])
            filtered_attrs = {k: attrs[k] for k in allowed_keys if k in attrs}

            entities.append({
                "entity_id": entity_id,
                "friendly_name": attrs.get("friendly_name", ""),
                "domain": domain,
                "state": state_val,
                "area": area_map.get(entity_id, ""),
                "attributes": filtered_attrs,
            })

        return entities

    # ------------------------------------------------------------------
    # 自动化（使用 REST API）
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        # 每次调用实时生成 access_token（同步方法，避免 token 过期问题）
        fresh_token = self._hass.auth.async_create_access_token(self._refresh_token)
        return {
            "Authorization": f"Bearer {fresh_token}",
            "Content-Type": "application/json",
        }

    async def list_automations(self) -> list[dict]:
        """通过 states 接口列举所有自动化摘要"""
        all_states = await self.get_all_states()
        result = []
        for s in all_states:
            entity_id = s.get("entity_id", "")
            if not entity_id.startswith("automation."):
                continue
            attrs = s.get("attributes", {})
            automation_id = attrs.get("id", "")
            result.append({
                "id": automation_id,
                "alias": attrs.get("friendly_name", entity_id),
                "description": attrs.get("description", ""),
                "mode": attrs.get("mode", "single"),
                "entity_id": entity_id,
            })
        return result

    async def get_automation_config(self, automation_id: str) -> dict:
        """获取单个自动化的完整配置（GET /api/config/automation/config/{id}）"""
        session = async_get_clientsession(self._hass, verify_ssl=False)
        url = f"{self._base_url}/api/config/automation/config/{automation_id}"
        async with session.get(url, headers=self._headers()) as resp:
            if resp.status == 404:
                raise ValueError(f"自动化 {automation_id} 不存在或为 YAML 型（无法通过 API 获取）")
            resp.raise_for_status()
            return await resp.json()

    async def create_automation(self, config: dict) -> str:
        """
        创建新自动化（POST /api/config/automation/config/new）。
        返回新自动化的 ID。
        """
        validate_automation(config)

        # 记录创建前的自动化列表
        before = {a["entity_id"] for a in await self.list_automations()}

        payload = dict(config)
        payload["id"] = str(int(time.time() * 1000))

        session = async_get_clientsession(self._hass, verify_ssl=False)
        url = f"{self._base_url}/api/config/automation/config/new"
        async with session.post(
            url,
            headers=self._headers(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ) as resp:
            if not resp.ok:
                body = (await resp.text())[:600]
                raise RuntimeError(f"{resp.status} — HA 说：{body}")

        # reload 并等待新自动化出现
        await self.reload_automations()
        for _ in range(8):
            await asyncio.sleep(1)
            after = await self.list_automations()
            new_items = [a for a in after if a["entity_id"] not in before]
            if new_items:
                return new_items[-1]["id"] or new_items[-1]["entity_id"]

        return payload["id"]

    async def update_automation(self, automation_id: str, config: dict) -> bool:
        """更新已有自动化（POST /api/config/automation/config/{id}）"""
        validate_automation(config)
        session = async_get_clientsession(self._hass, verify_ssl=False)
        url = f"{self._base_url}/api/config/automation/config/{automation_id}"
        async with session.post(
            url,
            headers=self._headers(),
            data=json.dumps(config, ensure_ascii=False).encode("utf-8"),
        ) as resp:
            if not resp.ok:
                body = (await resp.text())[:600]
                raise RuntimeError(f"{resp.status} — HA 说：{body}")
        return True

    async def delete_automation(self, automation_id: str) -> bool:
        """删除自动化（DELETE /api/config/automation/config/{id}）"""
        session = async_get_clientsession(self._hass, verify_ssl=False)
        url = f"{self._base_url}/api/config/automation/config/{automation_id}"
        async with session.delete(url, headers=self._headers()) as resp:
            resp.raise_for_status()
        return True

    async def reload_automations(self) -> bool:
        """触发 HA 重载自动化配置"""
        await self._hass.services.async_call("automation", "reload", blocking=True)
        return True

    @staticmethod
    def to_yaml(config: dict) -> str:
        return yaml.dump(config, allow_unicode=True, sort_keys=False, default_flow_style=False)


async def create_ha_bridge(hass: HomeAssistant, entry_id: str) -> HABridge:
    """
    创建 HABridge 实例，获取内部 refresh_token 对象。
    在 async_setup_entry 中调用，将结果存入 hass.data。
    """
    refresh_token = await _get_or_create_refresh_token(hass, entry_id)
    return HABridge(hass, refresh_token)


async def _get_or_create_refresh_token(hass: HomeAssistant, entry_id: str):
    """
    为集成创建或重用一个 refresh_token 对象（长期有效，不过期）。
    返回 refresh_token 对象，由 HABridge._headers() 每次调用时实时生成 access_token。
    """
    try:
        users = await hass.auth.async_get_users()
        admin_user = next(
            (u for u in users if not u.system_generated and u.is_admin),
            None,
        )
        if admin_user is None:
            raise RuntimeError("找不到管理员用户，无法创建 refresh token")

        client_name = f"ha_llm_automation_{entry_id}"
        # 检查是否已存在同名 refresh token
        existing = [
            t for t in admin_user.refresh_tokens.values()
            if t.client_name == client_name
        ]
        if existing:
            return existing[0]

        # 使用 LONG_LIVED_ACCESS_TOKEN 类型，不需要 client_id，兼容所有 HA 版本
        from homeassistant.auth.models import TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN
        return await hass.auth.async_create_refresh_token(
            admin_user,
            client_name=client_name,
            token_type=TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
        )
    except Exception as e:
        raise RuntimeError(f"创建 HA refresh token 失败：{e}") from e
