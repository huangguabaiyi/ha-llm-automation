from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


class HAConnection:
    """Home Assistant REST API 连接管理"""

    def __init__(self, config: dict):
        ha = config["ha"]
        self.base_url = ha["url"].rstrip("/")
        self.token = ha["token"]
        self.timeout = ha.get("timeout", 30)
        self.verify_ssl = ha.get("verify_ssl", True)
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            headers=self._headers,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )

    def test_connection(self) -> dict:
        """测试连接，返回 HA 基本信息"""
        with self._client() as client:
            resp = client.get(f"{self.base_url}/api/")
            resp.raise_for_status()
            return resp.json()

    def get(self, path: str) -> Any:
        with self._client() as client:
            resp = client.get(f"{self.base_url}/api/{path.lstrip('/')}")
            resp.raise_for_status()
            return resp.json()

    def post(self, path: str, data: dict | None = None) -> Any:
        with self._client() as client:
            resp = client.post(
                f"{self.base_url}/api/{path.lstrip('/')}",
                content=json.dumps(data or {}),
            )
            resp.raise_for_status()
            if resp.content:
                return resp.json()
            return {}

    def put(self, path: str, data: dict) -> Any:
        with self._client() as client:
            resp = client.put(
                f"{self.base_url}/api/{path.lstrip('/')}",
                content=json.dumps(data),
            )
            resp.raise_for_status()
            if resp.content:
                return resp.json()
            return {}

    def delete(self, path: str) -> bool:
        with self._client() as client:
            resp = client.delete(f"{self.base_url}/api/{path.lstrip('/')}")
            resp.raise_for_status()
            return True


def load_config(config_path: str = "config.json") -> dict:
    """加载配置文件"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"配置文件 {config_path} 不存在，请先复制 config.example.json 并填写配置"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)
