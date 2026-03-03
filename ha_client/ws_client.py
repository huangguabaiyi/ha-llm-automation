from __future__ import annotations

import json
import ssl
import threading

import websocket


class HAWebSocketClient:
    """Home Assistant WebSocket API 客户端（同步）"""

    def __init__(self, config: dict):
        ha = config["ha"]
        url = ha["url"].rstrip("/")
        ws_url = url.replace("https://", "wss://").replace("http://", "ws://")
        self.ws_url = ws_url + "/api/websocket"
        self.token = ha["token"]
        self.verify_ssl = ha.get("verify_ssl", True)
        self._lock = threading.Lock()
        self._id = 1

    # ------------------------------------------------------------------
    # 自动化 CRUD
    # ------------------------------------------------------------------

    def list_automations(self) -> list[dict]:
        result = self._call("config/automation/config/list")
        return result.get("result", [])

    def get_automation(self, automation_id: str) -> dict:
        result = self._call("config/automation/config/get", config_id=automation_id)
        return result.get("result", {})

    def create_automation(self, config: dict) -> str:
        result = self._call("config/automation/config/create", **config)
        return result.get("result", {}).get("id", "")

    def update_automation(self, automation_id: str, config: dict) -> bool:
        self._call("config/automation/config/update", config_id=automation_id, **config)
        return True

    def delete_automation(self, automation_id: str) -> bool:
        self._call("config/automation/config/delete", config_id=automation_id)
        return True

    # ------------------------------------------------------------------
    # 注册表查询（区域/实体关联）
    # ------------------------------------------------------------------

    def get_area_registry(self) -> list[dict]:
        """获取区域注册表（area_id, name）"""
        result = self._call("config/area_registry/list")
        return result.get("result", [])

    def get_entity_registry(self) -> list[dict]:
        """获取实体注册表（entity_id, area_id, device_id, disabled_by 等）"""
        result = self._call("config/entity_registry/list")
        return result.get("result", [])

    def get_device_registry(self) -> list[dict]:
        """获取设备注册表（device_id, area_id 等）"""
        result = self._call("config/device_registry/list")
        return result.get("result", [])

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _build_ssl_opts(self) -> dict:
        if not self.verify_ssl:
            return {"cert_reqs": ssl.CERT_NONE}
        return {}

    def _call(self, msg_type: str, **kwargs) -> dict:
        """建立 WebSocket 连接，完成一次请求后关闭"""
        with self._lock:
            cmd_id = self._id
            self._id += 1

        ws = websocket.WebSocket(sslopt=self._build_ssl_opts())
        try:
            ws.connect(self.ws_url, timeout=15)

            # 1. 接收 auth_required
            msg = json.loads(ws.recv())
            if msg.get("type") != "auth_required":
                raise RuntimeError(f"预期 auth_required，收到: {msg}")

            # 2. 发送 token
            ws.send(json.dumps({"type": "auth", "access_token": self.token}))

            # 3. 接收 auth_ok
            msg = json.loads(ws.recv())
            if msg.get("type") == "auth_invalid":
                raise RuntimeError("WebSocket 认证失败，请检查 token")
            if msg.get("type") != "auth_ok":
                raise RuntimeError(f"预期 auth_ok，收到: {msg}")

            # 4. 发送命令
            cmd = {"id": cmd_id, "type": msg_type}
            cmd.update(kwargs)
            ws.send(json.dumps(cmd))

            # 5. 等待响应
            while True:
                raw = ws.recv()
                msg = json.loads(raw)
                if msg.get("id") == cmd_id:
                    if not msg.get("success", True):
                        error = msg.get("error", {})
                        raise RuntimeError(
                            f"WebSocket 命令失败: {error.get('code')} - {error.get('message')}"
                        )
                    return msg
        finally:
            ws.close()
