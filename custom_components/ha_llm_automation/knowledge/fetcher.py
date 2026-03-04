"""HA 文档抓取与缓存（适配 HA 插件路径）"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify

# 预设的 HA 文档 URL
HA_DOC_URLS: dict[str, str] = {
    "automation_basic": "https://www.home-assistant.io/docs/automation/",
    "automation_trigger": "https://www.home-assistant.io/docs/automation/trigger/",
    "automation_condition": "https://www.home-assistant.io/docs/automation/condition/",
    "automation_action": "https://www.home-assistant.io/docs/automation/action/",
    "templating": "https://www.home-assistant.io/docs/configuration/templating/",
    "scripts": "https://www.home-assistant.io/docs/scripts/",
    "service_calls": "https://www.home-assistant.io/docs/scripts/service-calls/",
}

_DEFAULT_TTL_DAYS = 7


class DocFetcher:
    """HA 官方文档抓取与缓存管理"""

    def __init__(self, cache_dir: str, ttl_days: int = _DEFAULT_TTL_DAYS):
        """
        cache_dir: 缓存目录，插件中传 hass.config.path("custom_components/ha_llm_automation/cache")
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_days * 86400

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def get_doc(self, url: str) -> str:
        """获取文档 Markdown（优先读缓存）"""
        cache_file = self._cache_path(url)
        if self._is_cache_valid(cache_file):
            return self._read_cache(cache_file)

        content = self._fetch(url)
        self._write_cache(cache_file, url, content)
        return content

    def get_preset_docs(self, keys: list[str] | None = None) -> dict[str, str]:
        """批量获取预设文档，返回 {key: markdown} 字典"""
        targets = {k: v for k, v in HA_DOC_URLS.items() if keys is None or k in keys}
        return {key: self.get_doc(url) for key, url in targets.items()}

    def refresh_all_docs(self) -> list[str]:
        """强制刷新所有预设文档，返回成功刷新的 key 列表"""
        succeeded = []
        for key, url in HA_DOC_URLS.items():
            try:
                cache_file = self._cache_path(url)
                content = self._fetch(url)
                self._write_cache(cache_file, url, content)
                succeeded.append(key)
            except Exception:
                pass
        return succeeded

    def list_cached(self) -> list[dict]:
        """列出所有缓存文件信息"""
        result = []
        for f in sorted(self.cache_dir.glob("*.json")):
            try:
                meta = json.loads(f.read_text(encoding="utf-8"))
                age_hours = (time.time() - meta.get("fetched_at", 0)) / 3600
                # 查找 key 名称
                url = meta.get("url", "")
                key = next((k for k, v in HA_DOC_URLS.items() if v == url), f.stem)
                result.append({
                    "key": key,
                    "url": url,
                    "fetched_at": meta.get("fetched_at", 0),
                    "age_hours": round(age_hours, 1),
                    "expired": age_hours * 3600 > self.ttl_seconds,
                    "chars": len(meta.get("content", "")),
                })
            except Exception:
                continue
        return result

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _cache_path(self, url: str) -> Path:
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return self.cache_dir / f"{url_hash}.json"

    def _is_cache_valid(self, cache_file: Path) -> bool:
        if not cache_file.exists():
            return False
        try:
            meta = json.loads(cache_file.read_text(encoding="utf-8"))
            age = time.time() - meta.get("fetched_at", 0)
            return age < self.ttl_seconds
        except Exception:
            return False

    def _read_cache(self, cache_file: Path) -> str:
        meta = json.loads(cache_file.read_text(encoding="utf-8"))
        return meta.get("content", "")

    def _write_cache(self, cache_file: Path, url: str, content: str) -> None:
        meta = {"url": url, "fetched_at": time.time(), "content": content}
        cache_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def _fetch(self, url: str) -> str:
        """抓取 URL 并提取正文 Markdown"""
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "HA-LLM-Tool/1.0"})
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 提取主内容区域
        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_="content")
            or soup.find("div", {"id": "main"})
            or soup.body
        )
        if main is None:
            return resp.text[:5000]

        # 移除导航、页脚等无关元素
        for tag in main.find_all(["nav", "footer", "aside", "script", "style"]):
            tag.decompose()

        md = markdownify(str(main), heading_style="ATX", bullets="-")
        lines = [line for line in md.splitlines() if line.strip() or True]
        return "\n".join(lines).strip()
