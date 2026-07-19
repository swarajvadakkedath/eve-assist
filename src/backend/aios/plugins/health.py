"""Plugin health monitoring — status, metrics, heartbeat."""

import time
from datetime import datetime, timezone

from aios.plugins.models import PluginHealth, PluginHealthStatus


class PluginHealthMonitor:
    def __init__(self):
        self._health: dict[str, PluginHealth] = {}
        self._start_times: dict[str, float] = {}

    async def initialize(self, plugin_id: str) -> None:
        health = PluginHealth(status=PluginHealthStatus.STARTING)
        health.last_heartbeat = datetime.now(timezone.utc)
        self._health[plugin_id] = health
        self._start_times[plugin_id] = time.monotonic()

    async def mark_running(self, plugin_id: str) -> None:
        health = self._health.get(plugin_id)
        if not health:
            return
        health.status = PluginHealthStatus.RUNNING
        health.last_heartbeat = datetime.now(timezone.utc)
        if plugin_id in self._start_times:
            health.startup_time_ms = (time.monotonic() - self._start_times[plugin_id]) * 1000
            health.uptime_seconds = time.monotonic() - self._start_times[plugin_id]

    async def mark_degraded(self, plugin_id: str, reason: str = "") -> None:
        health = self._health.get(plugin_id)
        if not health:
            return
        health.status = PluginHealthStatus.DEGRADED
        health.last_error = reason
        health.last_heartbeat = datetime.now(timezone.utc)

    async def mark_failed(self, plugin_id: str, error: str) -> None:
        health = self._health.get(plugin_id)
        if not health:
            return
        health.status = PluginHealthStatus.FAILED
        health.error_count += 1
        health.last_error = error
        health.last_heartbeat = datetime.now(timezone.utc)

    async def mark_stopped(self, plugin_id: str) -> None:
        health = self._health.get(plugin_id)
        if not health:
            return
        health.status = PluginHealthStatus.STOPPED
        health.last_heartbeat = datetime.now(timezone.utc)

    async def heartbeat(self, plugin_id: str) -> None:
        health = self._health.get(plugin_id)
        if not health:
            return
        health.last_heartbeat = datetime.now(timezone.utc)
        if plugin_id in self._start_times:
            health.uptime_seconds = time.monotonic() - self._start_times[plugin_id]

    async def get_health(self, plugin_id: str) -> PluginHealth | None:
        health = self._health.get(plugin_id)
        if health and plugin_id in self._start_times:
            health.uptime_seconds = time.monotonic() - self._start_times[plugin_id]
        return health

    async def restart_tracked(self, plugin_id: str) -> None:
        health = self._health.get(plugin_id)
        if health:
            health.restart_count += 1
        self._start_times[plugin_id] = time.monotonic()

    async def remove(self, plugin_id: str) -> None:
        self._health.pop(plugin_id, None)
        self._start_times.pop(plugin_id, None)
