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
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, PANEL_ICON, PANEL_NAME, PANEL_TITLE, WS_EVENT_LOG
from .core.ha_bridge import create_ha_bridge

_LOGGER = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """集成初始化（yaml 配置兼容）"""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """配置条目加载"""
    hass.data.setdefault(DOMAIN, {})

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
        hass.http.register_static_path(
            f"/{DOMAIN}/frontend",
            str(FRONTEND_DIR),
            cache_headers=False,
        )

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
    """获取当前 LLM 配置"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    data = {**entry.data, **entry.options}
    # 不返回 api_key 明文（用 *** 代替）
    safe_data = {k: ("***" if "key" in k.lower() else v) for k, v in data.items()}
    connection.send_result(msg["id"], {"config": safe_data})


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/save_config",
    vol.Optional("model"): str,
    vol.Optional("max_tokens"): int,
    vol.Optional("temperature"): float,
    vol.Optional("extra_visible_domains"): str,
    vol.Optional("hidden_domains"): str,
})
@callback
def ws_save_config(hass, connection, msg):
    """保存配置（写入 options，不需要重启）"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    keys = ["model", "max_tokens", "temperature", "extra_visible_domains", "hidden_domains"]
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
    """获取实体列表"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core.ha_bridge import HABridge
    bridge: HABridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    try:
        entities = await bridge.get_entities()
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
    vol.Optional("use_docs", default=True): bool,
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
            hass, entry, msg["requirement"], log_cb, use_docs=msg.get("use_docs", True)
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
            hass, entry, msg["automation_id"], log_cb
        )
        connection.send_result(msg["id"], result)
    except Exception as e:
        connection.send_error(msg["id"], "error", str(e))


@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/optimize_generate",
    vol.Required("automation_yaml"): str,
    vol.Required("analysis"): dict,
    vol.Required("session_id"): str,
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
        result = await llm_service.run_consolidate_analyze(hass, entry, log_cb)
        # automations_data 的 config 字段较大，前端不需要；只传摘要
        result_safe = {
            "merge_groups": result["merge_groups"],
            "fix_items": result["fix_items"],
            "ok_items": result["ok_items"],
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
})
@websocket_api.async_response
async def ws_restore_backup(hass, connection, msg):
    """恢复备份"""
    entry = _get_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "尚未配置")
        return
    from .core import llm_service
    log_cb = _make_log_cb(hass, msg["session_id"])
    try:
        ok = await llm_service.run_restore_backup(hass, entry, msg["backup_path"], log_cb)
        connection.send_result(msg["id"], {"ok": ok})
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
