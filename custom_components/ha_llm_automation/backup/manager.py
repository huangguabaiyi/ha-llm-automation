"""自动化配置备份管理（适配 HA 插件路径）"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import yaml


class BackupManager:
    """自动化配置备份管理"""

    def __init__(self, backup_dir: str, max_versions: int = 10):
        """
        backup_dir: 备份目录，插件中传 hass.config.path("custom_components/ha_llm_automation/backup")
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_versions = max_versions

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def create_backup(self, automations: list[dict]) -> Path:
        """
        备份全量自动化配置（YAML 格式，可直接导入 HA）。
        返回备份文件路径。
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"automations_backup_{ts}.yaml"
        backup_file = self.backup_dir / filename
        backup_file.write_text(
            yaml.dump(automations, allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        self._cleanup_old_backups()
        return backup_file

    def list_backups(self) -> list[dict]:
        """列出所有备份（按时间倒序，兼容旧 .json 格式）"""
        files = sorted(
            list(self.backup_dir.glob("automations_backup_*.yaml"))
            + list(self.backup_dir.glob("automations_backup_*.json")),
            key=lambda f: f.name,
            reverse=True,
        )
        result = []
        for f in files:
            try:
                stat = f.stat()
                data = self._load_file(f)
                result.append({
                    "file": str(f),
                    "name": f.name,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "count": len(data),
                    "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                })
            except Exception:
                continue
        return result

    def restore_backup(self, backup_path: str) -> list[dict]:
        """
        从备份文件读取自动化配置，返回配置列表（支持 .yaml / .json）。
        调用方负责将列表写回 HA。
        """
        path = Path(backup_path)
        if not path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        data = self._load_file(path)
        if not isinstance(data, list):
            raise ValueError("备份文件格式错误：顶层应为列表")
        return data

    def get_latest_backup(self) -> Path | None:
        """返回最新备份文件路径，无备份时返回 None"""
        files = sorted(
            list(self.backup_dir.glob("automations_backup_*.yaml"))
            + list(self.backup_dir.glob("automations_backup_*.json")),
            key=lambda f: f.name,
            reverse=True,
        )
        return files[0] if files else None

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _load_file(self, path: Path) -> list:
        """读取备份文件，自动识别 .yaml / .json 格式"""
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".yaml":
            return yaml.safe_load(text) or []
        return json.loads(text)

    def _cleanup_old_backups(self) -> None:
        """删除超出 max_versions 的旧备份（yaml + json 合并计算）"""
        files = sorted(
            list(self.backup_dir.glob("automations_backup_*.yaml"))
            + list(self.backup_dir.glob("automations_backup_*.json")),
            key=lambda f: f.name,
            reverse=True,
        )
        for old in files[self.max_versions:]:
            old.unlink(missing_ok=True)
