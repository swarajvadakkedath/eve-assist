"""Launcher status API — consumed by Tauri in Sprint 2."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LauncherStatus:
    state: str = "stopped"
    version: str = ""
    started_at: float = 0.0
    backend_url: str = ""
    frontend_url: str = ""
    frontend_type: str = "browser"
    services: dict[str, str] = field(default_factory=dict)
    providers: dict[str, dict] = field(default_factory=dict)
    uptime: float = 0.0


class LauncherAPI:
    def __init__(self, get_status_fn, get_health_fn, get_log_dir_fn):
        self._get_status = get_status_fn
        self._get_health = get_health_fn
        self._get_log_dir = get_log_dir_fn

    def status(self) -> LauncherStatus:
        return self._get_status()

    async def health(self) -> dict[str, Any]:
        return await self._get_health()

    def log_dir(self) -> str:
        return str(self._get_log_dir())
