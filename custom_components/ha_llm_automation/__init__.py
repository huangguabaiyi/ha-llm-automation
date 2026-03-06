"""
HA LLM Automation — 集成入口

注册：
- 侧边栏面板（ha-llm-automation）
- ~16 个 WebSocket 命令处理器
- 日志实时推送（dispatcher）
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_AREA_FILTER,
    CONF_EXTRA_VISIBLE_DOMAINS,
    CONF_HIDDEN_DOMAINS,
    CONF_INTEGRATION_FILTER,
    CONF_LABEL_FILTER,
    CONF_LLM_API_KEY,
    CONF_LLM_BASE_URL,
    CONF_LLM_MAX_TOKENS,
    CONF_LLM_MODEL,
    CONF_LLM_PROVIDER,
    CONF_LLM_TEMPERATURE,
    CONF_LOG_PROMPT,
    CONF_USE_DOCS,
    DOMAIN,
    PANEL_ICON,
    PANEL_NAME,
    PANEL_TITLE,
    WS_EVENT_LOG,
)
from .core.ha_bridge import create_ha_bridge

_LOGGER = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """集成初始化（yaml 配置兼容）"""
    hass.data.setdefault(DOMAIN, {})
    return True


_LLM_KEYS = [
    CONF_LLM_PROVIDER, CONF_LLM_API_KEY, CONF_LLM_BASE_URL,
    CONF_LLM_MODEL, CONF_LLM_MAX_TOKENS, CONF_LLM_TEMPERATURE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """配置条目加载"""
    hass.data.setdefault(DOMAIN, {})

    # 旧配置迁移：将 entry.data 中的 LLM 字段移至 entry.options
    migrate = {k: v for k, v in entry.data.items() if k in _LLM_KEYS}
    if migrate:
        _LOGGER.info("检测到旧版 LLM 配置，迁移到 options...")
        hass.config_entries.async_update_entry(
            entry,
            data={k: v for k, v in entry.data.items() if k not in _LLM_KEYS},
            options={**migrate, **entry.options},  # options 优先级更高
        )

    # 创建 HABridge（生成内部 access token）
    try:
        bridge = await create_ha_bridge(hass, entry.entry_id)
    except Exception as e:
        _LOGGER.error("创建 HABridge 失败：%s", e)
        raise

    hass.data[DOMAIN][entry.entry_id] = {
        "bridge": bridge,
        "entry": entry,
    }

    # 注册静态前端文件
    if FRONTEND_DIR.exists():
        await hass.http.async_register_static_paths([
            StaticPathConfig(f"/{DOMAIN}/frontend", str(FRONTEND_DIR), cache_headers=False)
        ])

    # 注册侧边栏面板
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=DOMAIN,
        config={
            "_panel_custom": {
                "name": PANEL_NAME,
                "js_url": f"/{DOMAIN}/frontend/{PANEL_NAME}.js",
                "embed_iframe": False,
                "trust_external": False,
            }
        },
        require_admin=False,
    )

    # 注册 WebSocket 命令
    _register_websocket_commands(hass)

    # 监听配置更新
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """配置条目卸载"""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    frontend.async_remove_panel(hass, DOMAIN)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """配置更新时重载"""
    await hass.config_entries.async_reload(entry.entry_id)


def _send_log(hass: HomeAssistant, session_id: str, msg: str) -> None:
    """向前端推送一条日志消息"""
    async_dispatcher_send(
        hass,
        f"{WS_EVENT_LOG}_{session_id}",
        {"session_id": session_id, "message": msg},
    )


def _register_websocket_commands(hass: HomeAssistant) -> None:
    """注册全部 WebSocket 命令"""
    cmds = [
        ws_get_config,
        ws_save_config,
        ws_get_entities,
        ws_get_automations,
        ws_get_automation_config,
        ws_create_start,
        ws_create_refine,
        ws_create_save,
        ws_optimize_analyze,
        ws_optimize_generate,
        ws_optimize_refine,
        ws_optimize_save,
        ws_consolidate_analyze,
        ws_consolidate_refine,
        ws_consolidate_execute,
        ws_refresh_docs,
        ws_list_backups,
        ws_restore_backup,
        ws_subscribe_log,
        ws_get_areas,
        ws_get_labels,
        ws_get_integrations,
        ws_clear_backups,
        ws_preview_doc,
        ws_delete_inaccessible_automations,
        ws_batch_delete_automations,
        ws_backup_selected,
    ]
    for cmd in cmds:
        websocket_api.async_register_command(hass, cmd)


# ==================================================================
# 辅助：获取 entry
# ==================================================================

def _get_entry(hass: HomeAssistant) -> ConfigEntry | None:
    """获取唯一的配置条目"""
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _make_log_cb(hass: HomeAssistant, session_id: str):
    def cb(msg: str) -> None:
        _send_log(hass, session_id, msg)
    return cb


# ==================================================================
# WebSocket 命令：配置
# ==================================================================

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_config",
})
@callback
def ws_get_config(hass, connection, msg):
    """获取当前 LLM 配置（api_key 原文返回，前端用 password input 展示）"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    # 只返回 options 中的配置（新架构全部存在 options）
    connection.send_result(msg["id"], {"config": dict(entry.options)})


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/save_config",
    vol.Optional(CONF_LLM_PROVIDER): str,
    vol.Optional(CONF_LLM_API_KEY): str,
    vol.Optional(CONF_LLM_BASE_URL): str,
    vol.Optional(CONF_LLM_MODEL): str,
    vol.Optional(CONF_LLM_MAX_TOKENS): int,
    vol.Optional(CONF_LLM_TEMPERATURE): float,
    vol.Optional(CONF_EXTRA_VISIBLE_DOMAINS): str,
    vol.Optional(CONF_HIDDEN_DOMAINS): str,
    vol.Optional(CONF_LOG_PROMPT): bool,
    vol.Optional(CONF_USE_DOCS): bool,
    vol.Optional(CONF_AREA_FILTER): list,
    vol.Optional(CONF_LABEL_FILTER): list,
    vol.Optional(CONF_INTEGRATION_FILTER): list,
})
@callback
def ws_save_config(hass, connection, msg):
    """保存配置（写入 options，不需要重启）"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    keys = [
        CONF_LLM_PROVIDER, CONF_LLM_API_KEY, CONF_LLM_BASE_URL, CONF_LLM_MODEL,
        CONF_LLM_MAX_TOKENS, CONF_LLM_TEMPERATURE,
        CONF_EXTRA_VISIBLE_DOMAINS, CONF_HIDDEN_DOMAINS, CONF_LOG_PROMPT, CONF_USE_DOCS,
        CONF_AREA_FILTER, CONF_LABEL_FILTER, CONF_INTEGRATION_FILTER,
    ]
    new_options = {**entry.options}
    for k in keys:
        if k in msg:
            new_options[k] = msg[k]
    hass.config_entries.async_update_entry(entry, options=new_options)
    connection.send_result(msg["id"], {"ok": True})


# ==================================================================
# WebSocket 命令：实体 & 自动化查询
# ==================================================================

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_entities",
})
@websocket_api.async_response
async def ws_get_entities(hass, connection, msg):
    """获取实体列表（从 options 读取过滤参数）"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core.ha_bridge import HABridge
    bridge: HABridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    try:
        opts = entry.options
        entities = await bridge.get_entities(
            area_filter=opts.get(CONF_AREA_FILTER) or None,
            label_filter=opts.get(CONF_LABEL_FILTER) or None,
            integration_filter=opts.get(CONF_INTEGRATION_FILTER) or None,
        )
        connection.send_result(msg["id"], {"entities": entities})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_automations",
})
@websocket_api.async_response
async def ws_get_automations(hass, connection, msg):
    """获取自动化列表"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core.ha_bridge import HABridge
    bridge: HABridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    try:
        automations = await bridge.list_automations()
        # 预检哪些可以获取完整配置（存储型）
        accessible = []
        for a in automations:
            aid = a.get("id", "")
            if not aid or aid == "new":
                continue
            try:
                await bridge.get_automation_config(aid)
                accessible.append({**a, "accessible": True})
            except Exception:
                accessible.append({**a, "accessible": False})
        connection.send_result(msg["id"], {"automations": accessible})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/delete_inaccessible_automations",
})
@websocket_api.async_response
async def ws_delete_inaccessible_automations(hass, connection, msg):
    """后端自动探测 accessible=false 的自动化并删除（YAML型/GET失败的）"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core.ha_bridge import HABridge
    bridge: HABridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    try:
        automations = await bridge.list_automations()
        _LOGGER.info("delete_inaccessible: 共扫描到 %d 条自动化", len(automations))
        # 探测不可访问的自动化（GET失败 = YAML型）
        inaccessible = []  # list of {"id": ..., "alias": ..., "entity_id": ...}
        for a in automations:
            aid = a.get("id", "")
            alias = a.get("alias", aid)
            if not aid or aid == "new":
                _LOGGER.debug("delete_inaccessible: 跳过 id=%r alias=%r", aid, alias)
                continue
            try:
                await bridge.get_automation_config(aid)
            except Exception as e:
                _LOGGER.warning(
                    "delete_inaccessible: GET config 失败 id=%s alias=%r → 标记为不可访问 | 原因: %s",
                    aid, alias, e,
                )
                inaccessible.append({"id": aid, "alias": alias, "entity_id": a.get("entity_id", "")})
        _LOGGER.info("delete_inaccessible: 发现 %d 条不可访问自动化，准备删除", len(inaccessible))
        # 删除
        deleted = []
        failed = []
        for item in inaccessible:
            aid, alias, entity_id = item["id"], item["alias"], item["entity_id"]
            try:
                await bridge.delete_automation(aid)
                deleted.append({"id": aid, "alias": alias})
                _LOGGER.info("delete_inaccessible: 已删除 id=%s alias=%r", aid, alias)
            except Exception as e:
                err_str = str(e)
                is_not_found = "resource not found" in err_str.lower() or "not found" in err_str.lower()
                if is_not_found and entity_id:
                    # DELETE API 找不到此条目——可能是幽灵实体（曾经存在，现已从配置移除，但仍留在实体注册表）
                    # 尝试直接从实体注册表移除，彻底清除幽灵
                    try:
                        from homeassistant.helpers import entity_registry as er
                        reg = er.async_get(hass)
                        if reg.async_get(entity_id):
                            reg.async_remove(entity_id)
                            deleted.append({"id": aid, "alias": alias, "ghost": True})
                            _LOGGER.info(
                                "delete_inaccessible: 幽灵实体已从注册表清除 entity_id=%s alias=%r",
                                entity_id, alias,
                            )
                        else:
                            _LOGGER.warning(
                                "delete_inaccessible: entity_id=%s 不在注册表中，跳过 alias=%r",
                                entity_id, alias,
                            )
                            failed.append({"id": aid, "alias": alias, "error": err_str, "yaml_type": True})
                    except Exception as re:
                        _LOGGER.error(
                            "delete_inaccessible: 注册表移除失败 entity_id=%s alias=%r | 原因: %s",
                            entity_id, alias, re,
                        )
                        failed.append({"id": aid, "alias": alias, "error": str(re), "yaml_type": True})
                elif is_not_found:
                    # 没有 entity_id，无法走注册表路径，只能提示手动处理
                    _LOGGER.warning(
                        "delete_inaccessible: id=%s alias=%r 无 entity_id，无法清除 | HA返回: %s",
                        aid, alias, err_str,
                    )
                    failed.append({"id": aid, "alias": alias, "error": err_str, "yaml_type": True})
                else:
                    _LOGGER.error(
                        "delete_inaccessible: 删除失败 id=%s alias=%r | 原因: %s",
                        aid, alias, err_str,
                    )
                    failed.append({"id": aid, "alias": alias, "error": err_str, "yaml_type": False})
        if deleted:
            await bridge.reload_automations()
            _LOGGER.info("delete_inaccessible: reload 完成，成功 %d 条（含幽灵清除），失败 %d 条", len(deleted), len(failed))
        else:
            _LOGGER.info("delete_inaccessible: 无自动化被删除，失败 %d 条", len(failed))
        connection.send_result(msg["id"], {"deleted": deleted, "failed": failed, "scanned": len(automations)})
    except Exception as e:
        _LOGGER.exception("delete_inaccessible: 意外错误: %s", e)
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_automation_config",
    vol.Required("automation_id"): str,
})
@websocket_api.async_response
async def ws_get_automation_config(hass, connection, msg):
    """获取单条自动化完整配置"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core.ha_bridge import HABridge
    bridge: HABridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    try:
        config = await bridge.get_automation_config(msg["automation_id"])
        yaml_str = bridge.to_yaml(config)
        connection.send_result(msg["id"], {"config": config, "yaml_str": yaml_str})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


# ==================================================================
# WebSocket 命令：创建模式
# ==================================================================

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/create_start",
    vol.Required("requirement"): str,
    vol.Required("session_id"): str,
    vol.Optional("use_docs"): bool,  # None = 读取 config_entry.options
})
@websocket_api.async_response
async def ws_create_start(hass, connection, msg):
    """创建模式：可行性检查 + YAML 生成"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    session_id = msg["session_id"]
    log_cb = _make_log_cb(hass, session_id)
    try:
        result = await llm_service.run_create(
            hass, entry, msg["requirement"], log_cb, use_docs=msg.get("use_docs")
        )
        # automations 中 set 无法 JSON 序列化，转为 list
        result["valid_ids"] = list(result.get("valid_ids") or [])
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/create_refine",
    vol.Required("current_yaml"): str,
    vol.Required("feedback"): str,
    vol.Required("system_prompt"): str,
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_create_refine(hass, connection, msg):
    """创建模式：追问修改"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        result = await llm_service.run_create_refine(
            hass, entry,
            current_yaml=msg["current_yaml"],
            feedback=msg["feedback"],
            system_prompt=msg["system_prompt"],
            log_callback=log_cb,
        )
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/create_save",
    vol.Required("automations"): list,
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_create_save(hass, connection, msg):
    """创建模式：批量保存"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        results = await llm_service.run_create_save(
            hass, entry, msg["automations"], log_cb
        )
        connection.send_result(msg["id"], {"results": results})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


# ==================================================================
# WebSocket 命令：优化模式
# ==================================================================

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/optimize_analyze",
    vol.Required("automation_id"): str,
    vol.Required("session_id"): str,
    vol.Optional("user_direction"): str,
})
@websocket_api.async_response
async def ws_optimize_analyze(hass, connection, msg):
    """优化模式 Step 1：分析意图"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        result = await llm_service.run_optimize_analyze(
            hass, entry, msg["automation_id"], log_cb,
            user_direction=msg.get("user_direction", ""),
        )
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/optimize_generate",
    vol.Required("automation_yaml"): str,
    vol.Required("analysis"): dict,
    vol.Required("session_id"): str,
    vol.Optional("user_direction"): str,
})
@websocket_api.async_response
async def ws_optimize_generate(hass, connection, msg):
    """优化模式 Step 2：生成优化 YAML"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        result = await llm_service.run_optimize_generate(
            hass, entry,
            automation_yaml=msg["automation_yaml"],
            analysis=msg["analysis"],
            log_callback=log_cb,
            user_direction=msg.get("user_direction", ""),
        )
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/optimize_refine",
    vol.Required("current_yaml"): str,
    vol.Required("feedback"): str,
    vol.Required("system_prompt"): str,
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_optimize_refine(hass, connection, msg):
    """优化模式：追问修改"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        result = await llm_service.run_optimize_refine(
            hass, entry,
            current_yaml=msg["current_yaml"],
            feedback=msg["feedback"],
            system_prompt=msg["system_prompt"],
            log_callback=log_cb,
        )
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/optimize_save",
    vol.Required("automation_id"): str,
    vol.Required("parsed"): dict,
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_optimize_save(hass, connection, msg):
    """优化模式：保存"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        await llm_service.run_optimize_save(
            hass, entry, msg["automation_id"], msg["parsed"], log_cb
        )
        connection.send_result(msg["id"], {"ok": True})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


# ==================================================================
# WebSocket 命令：聚合模式
# ==================================================================

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/consolidate_analyze",
    vol.Required("session_id"): str,
    vol.Optional("automation_ids"): list,  # None = 分析全部，传入列表 = 只分析指定 ID
})
@websocket_api.async_response
async def ws_consolidate_analyze(hass, connection, msg):
    """聚合模式：分析"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        result = await llm_service.run_consolidate_analyze(
            hass, entry, log_cb,
            automation_ids=msg.get("automation_ids"),
        )
        # 构建 id -> yaml_str 映射，向前端提供原始 YAML 用于对比
        id_to_yaml = {d["id"]: d["yaml_str"] for d in result.get("automations_data", [])}

        # 为 merge_groups 附加各原始自动化的 YAML
        merge_groups_enriched = []
        for g in result.get("merge_groups", []):
            enriched = dict(g)
            enriched["original_yamls"] = [
                {"id": aid, "yaml": id_to_yaml.get(aid, "")}
                for aid in (g.get("ids") or [])
            ]
            merge_groups_enriched.append(enriched)

        # 为 fix_items 附加原始 YAML
        fix_items_enriched = []
        for f in result.get("fix_items", []):
            enriched = dict(f)
            enriched["original_yaml"] = id_to_yaml.get(f.get("id", ""), "")
            fix_items_enriched.append(enriched)

        result_safe = {
            "merge_groups": merge_groups_enriched,
            "fix_items": fix_items_enriched,
            "ok_items": result.get("ok_items", []),
        }
        connection.send_result(msg["id"], result_safe)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/consolidate_refine",
    vol.Required("item_type"): str,
    vol.Required("item_id"): str,
    vol.Required("current_yaml"): str,
    vol.Required("feedback"): str,
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_consolidate_refine(hass, connection, msg):
    """聚合模式：单条追问修改"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        new_yaml = await llm_service.run_consolidate_refine(
            hass, entry,
            item_type=msg["item_type"],
            item_id=msg["item_id"],
            current_yaml=msg["current_yaml"],
            feedback=msg["feedback"],
            log_callback=log_cb,
        )
        connection.send_result(msg["id"], {"yaml_str": new_yaml})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/consolidate_execute",
    vol.Required("approved_merges"): list,
    vol.Required("approved_fixes"): list,
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_consolidate_execute(hass, connection, msg):
    """聚合模式：执行"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        result = await llm_service.run_consolidate_execute(
            hass, entry,
            approved_merges=msg["approved_merges"],
            approved_fixes=msg["approved_fixes"],
            log_callback=log_cb,
        )
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


# ==================================================================
# WebSocket 命令：知识库 & 备份
# ==================================================================

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/refresh_docs",
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_refresh_docs(hass, connection, msg):
    """刷新 HA 文档缓存"""
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        succeeded = await llm_service.run_refresh_docs(hass, log_cb)
        connection.send_result(msg["id"], {"succeeded": succeeded})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/list_backups",
})
@websocket_api.async_response
async def ws_list_backups(hass, connection, msg):
    """获取备份列表"""
    from .core import llm_service
    try:
        backups = await llm_service.get_backups(hass)
        connection.send_result(msg["id"], {"backups": backups})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/restore_backup",
    vol.Required("backup_path"): str,
    vol.Required("session_id"): str,
    vol.Optional("restore_mode"): str,  # "incremental"（默认）| "overwrite"
})
@websocket_api.async_response
async def ws_restore_backup(hass, connection, msg):
    """恢复备份（支持增量/覆盖两种模式）"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    restore_mode = msg.get("restore_mode", "incremental")
    try:
        ok = await llm_service.run_restore_backup(hass, entry, msg["backup_path"], log_cb, restore_mode)
        connection.send_result(msg["id"], {"ok": ok})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/batch_delete_automations",
    vol.Required("automation_ids_csv"): str,  # 逗号分隔，规避 HA WS 框架数组兼容问题
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_batch_delete_automations(hass, connection, msg):
    """批量删除自动化"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    automation_ids = [i.strip() for i in msg["automation_ids_csv"].split(",") if i.strip()]
    if not automation_ids:
        connection.send_error(msg["id"], "invalid", "automation_ids_csv 为空")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        result = await llm_service.run_batch_delete_automations(hass, entry, automation_ids, log_cb)
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/backup_selected",
    vol.Required("automation_ids_csv"): str,  # 逗号分隔
})
@websocket_api.async_response
async def ws_backup_selected(hass, connection, msg):
    """备份选中的自动化（生成子集备份文件）"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    automation_ids = [i.strip() for i in msg["automation_ids_csv"].split(",") if i.strip()]
    if not automation_ids:
        connection.send_error(msg["id"], "invalid", "automation_ids_csv 为空")
        return
    from .core import llm_service
    try:
        result = await llm_service.run_backup_selected(hass, entry, automation_ids)
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


# ==================================================================
# WebSocket 命令：日志订阅
# ==================================================================

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/subscribe_log",
    vol.Required("session_id"): str,
})
@callback
def ws_subscribe_log(hass, connection, msg):
    """订阅指定 session_id 的日志推送"""
    from homeassistant.helpers.dispatcher import async_dispatcher_connect

    session_id = msg["session_id"]
    msg_id = msg["id"]

    @callback
    def _forward_log(data: dict) -> None:
        connection.send_event(msg_id, data)

    unsub = async_dispatcher_connect(
        hass,
        f"{WS_EVENT_LOG}_{session_id}",
        _forward_log,
    )
    connection.subscriptions[msg_id] = unsub
    connection.send_result(msg_id, {"subscribed": True, "session_id": session_id})


# ==================================================================
# WebSocket 命令：区域 / 标签 / 集成 / 备份清空 / 文档预览
# ==================================================================

@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_areas",
})
@websocket_api.async_response
async def ws_get_areas(hass, connection, msg):
    """返回区域注册表列表"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core.ha_bridge import HABridge
    bridge: HABridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    try:
        areas = await bridge.get_area_registry()
        connection.send_result(msg["id"], {"areas": areas})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_labels",
})
@websocket_api.async_response
async def ws_get_labels(hass, connection, msg):
    """返回标签注册表列表"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core.ha_bridge import HABridge
    bridge: HABridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    try:
        labels = await bridge.get_labels()
        connection.send_result(msg["id"], {"labels": labels})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/get_integrations",
})
@websocket_api.async_response
async def ws_get_integrations(hass, connection, msg):
    """返回所有集成平台名称列表"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core.ha_bridge import HABridge
    bridge: HABridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    try:
        integrations = await bridge.get_entity_platforms()
        connection.send_result(msg["id"], {"integrations": integrations})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/clear_backups",
    vol.Required("session_id"): str,
})
@websocket_api.async_response
async def ws_clear_backups(hass, connection, msg):
    """删除全部备份文件"""
    from .core import llm_service
    try:
        mgr = llm_service._get_backup_manager(hass)
        backup_dir = mgr.backup_dir if hasattr(mgr, "backup_dir") else None
        if backup_dir:
            import glob as globmod
            files = globmod.glob(str(backup_dir) + "/*.yaml") + globmod.glob(str(backup_dir) + "/*.json")
            for f in files:
                os.remove(f)
            connection.send_result(msg["id"], {"deleted": len(files)})
        else:
            connection.send_result(msg["id"], {"deleted": 0})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/preview_doc",
    vol.Required("doc_key"): str,
})
@websocket_api.async_response
async def ws_preview_doc(hass, connection, msg):
    """返回文档缓存原文内容（最多 5000 字符）"""
    from .core import llm_service
    from .knowledge.fetcher import HA_DOC_URLS
    try:
        doc_key = msg["doc_key"]
        url = HA_DOC_URLS.get(doc_key, "")
        if not url:
            connection.send_error(msg["id"], "not_found", f"未知的文档 key: {doc_key}")
            return
        fetcher = llm_service._get_doc_fetcher(hass)
        content = await hass.async_add_executor_job(
            lambda: fetcher.get_doc(url) or ""
        )
        connection.send_result(msg["id"], {"content": content[:5000], "truncated": len(content) > 5000})
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))
