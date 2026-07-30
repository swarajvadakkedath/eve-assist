"""Plugin sandbox — delegates to PluginIsolator for execution isolation."""

from aios.plugins.isolator import PluginIsolator
from aios.plugins.models import IsolationStrategy, PluginResult


class PluginSandbox:
    def __init__(self, memory_limit_mb: int = 256, timeout: int = 30):
        self._isolator = PluginIsolator()
        self._memory_limit_mb = memory_limit_mb
        self._timeout = timeout

    async def execute(self, plugin_id: str, tool_id: str, params: dict, timeout: int | None = None) -> PluginResult:
        return await self._isolator.execute(
            plugin_id=plugin_id,
            tool_id=tool_id,
            params=params,
            timeout=timeout or self._timeout,
            strategy=IsolationStrategy.IN_PROCESS,
        )

    async def execute_subprocess(self, plugin_id: str, tool_id: str, params: dict, timeout: int | None = None) -> PluginResult:
        return await self._isolator.execute(
            plugin_id=plugin_id,
            tool_id=tool_id,
            params=params,
            timeout=timeout or self._timeout,
            strategy=IsolationStrategy.SUBPROCESS,
        )
