"""Plugin runtime — lifecycle management, health monitoring, crash recovery.

The Runtime invokes the actual plugin instance lifecycle methods (initialize, start,
stop, shutdown, dispose) on the AIOSPlugin instance, not just state transitions.
"""

from datetime import datetime, timezone

from aios.plugins.models import Plugin, PluginStatus, PluginHealthStatus
from aios.plugins.lifecycle import PluginLifecycle
from aios.plugins.registry import PluginRegistry
from aios.plugins.health import PluginHealthMonitor
from aios.plugins.events import PluginEventPublisher
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class PluginRuntime:
    def __init__(
        self,
        registry: PluginRegistry,
        lifecycle: PluginLifecycle,
        health: PluginHealthMonitor,
        event_publisher: PluginEventPublisher | None = None,
        permission_manager=None,
        tool_manager=None,
        capability_registry=None,
        event_bus=None,
    ):
        self._registry = registry
        self._lifecycle = lifecycle
        self._health = health
        self._events = event_publisher
        self._pm = permission_manager
        self._tm = tool_manager
        self._capability_registry = capability_registry
        self._eb = event_bus

    async def initialize_plugin(self, plugin_id: str) -> Plugin:
        plugin = self._registry.get(plugin_id)
        self._lifecycle.validate_transition(plugin.state.status, PluginStatus.INITIALIZING)
        plugin.state.status = PluginStatus.INITIALIZING
        await self._health.initialize(plugin_id)
        return plugin

    async def start_plugin(self, plugin_id: str) -> Plugin:
        plugin = self._registry.get(plugin_id)
        self._lifecycle.validate_transition(plugin.state.status, PluginStatus.STARTING)
        plugin.state.status = PluginStatus.STARTING
        plugin.state.started_at = datetime.now(timezone.utc)

        instance = getattr(plugin, "instance", None)
        if instance is not None and hasattr(instance, "start"):
            try:
                result = instance.start()
                if hasattr(result, "__await__"):
                    await result
                logger.info("runtime.plugin_started", plugin_id=plugin_id)
            except Exception as e:
                logger.error("runtime.start_failed", plugin_id=plugin_id, error=str(e))
                plugin.state.status = PluginStatus.FAILED
                await self._health.mark_failed(plugin_id, str(e))
                if self._events:
                    await self._events.failed(plugin_id, str(e))
                return plugin

        plugin.state.status = PluginStatus.ACTIVE
        await self._health.mark_running(plugin_id)
        if self._events:
            await self._events.started(plugin_id)
        return plugin

    async def stop_plugin(self, plugin_id: str) -> Plugin:
        plugin = self._registry.get(plugin_id)
        if plugin.state.status not in (PluginStatus.ACTIVE, PluginStatus.DEGRADED, PluginStatus.STARTING):
            return plugin

        self._lifecycle.validate_transition(plugin.state.status, PluginStatus.STOPPING)
        plugin.state.status = PluginStatus.STOPPING

        instance = getattr(plugin, "instance", None)
        if instance is not None and hasattr(instance, "stop"):
            try:
                result = instance.stop()
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.warning("runtime.stop_failed", plugin_id=plugin_id, error=str(e))

        plugin.state.status = PluginStatus.STOPPED
        plugin.state.stopped_at = datetime.now(timezone.utc)
        await self._health.mark_stopped(plugin_id)
        if self._events:
            await self._events.stopped(plugin_id)
        return plugin

    async def unload_plugin(self, plugin_id: str) -> None:
        plugin = self._registry.get(plugin_id)
        self._lifecycle.validate_transition(plugin.state.status, PluginStatus.UNLOADED)

        instance = getattr(plugin, "instance", None)
        if instance is not None:
            try:
                result = instance.shutdown()
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.warning("runtime.shutdown_failed", plugin_id=plugin_id, error=str(e))
            try:
                result = instance.dispose()
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.warning("runtime.dispose_failed", plugin_id=plugin_id, error=str(e))

        plugin.state.status = PluginStatus.UNLOADED
        await self._health.remove(plugin_id)
        if self._events:
            await self._events.unloaded(plugin_id)

    async def remove_plugin(self, plugin_id: str) -> Plugin:
        plugin = self._registry.get(plugin_id)
        self._lifecycle.validate_transition(plugin.state.status, PluginStatus.REMOVED)
        await self.unload_plugin(plugin_id)
        self._registry.remove(plugin_id)
        return plugin

    async def recover_plugin(self, plugin_id: str) -> Plugin:
        plugin = self._registry.get(plugin_id)
        if not plugin.is_failed:
            return plugin

        await self._health.restart_tracked(plugin_id)
        try:
            plugin.state.status = PluginStatus.LOADING
            plugin.state.status = PluginStatus.STARTING
            plugin.state.started_at = datetime.now(timezone.utc)

            instance = getattr(plugin, "instance", None)
            if instance is not None and hasattr(instance, "start"):
                result = instance.start()
                if hasattr(result, "__await__"):
                    await result

            plugin.state.status = PluginStatus.ACTIVE
            await self._health.mark_running(plugin_id)
            if self._events:
                await self._events.started(plugin_id)
            logger.info("runtime.plugin_recovered", plugin_id=plugin_id)
        except Exception as e:
            plugin.state.status = PluginStatus.FAILED
            await self._health.mark_failed(plugin_id, str(e))
            if self._events:
                await self._events.failed(plugin_id, str(e))
            logger.error("runtime.recover_failed", plugin_id=plugin_id, error=str(e))
        return plugin

    async def get_plugin_status(self, plugin_id: str) -> PluginStatus:
        return self._registry.get(plugin_id).state.status

    async def get_plugin_health(self, plugin_id: str):
        return await self._health.get_health(plugin_id)
