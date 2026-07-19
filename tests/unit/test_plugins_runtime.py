"""Unit tests for PluginRuntime — lifecycle invocation on plugin instances."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aios.plugins.runtime import PluginRuntime
from aios.plugins.registry import PluginRegistry
from aios.plugins.lifecycle import PluginLifecycle
from aios.plugins.health import PluginHealthMonitor
from aios.plugins.events import PluginEventPublisher
from aios.plugins.models import Plugin, PluginStatus, PluginState


class MockPluginInstance:
    def __init__(self):
        self.initialize = AsyncMock()
        self.register = AsyncMock()
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.shutdown = AsyncMock()
        self.dispose = AsyncMock()
        self.health = AsyncMock(return_value={"status": "alive"})


def make_plugin(pid: str, status: PluginStatus = PluginStatus.LOADED, instance=None) -> Plugin:
    p = Plugin(id=pid)
    p.state.status = status
    p.instance = instance
    return p


@pytest.fixture
def runtime():
    registry = PluginRegistry()
    lifecycle = PluginLifecycle()
    health = PluginHealthMonitor()
    events = PluginEventPublisher(event_bus=AsyncMock())
    return PluginRuntime(
        registry=registry,
        lifecycle=lifecycle,
        health=health,
        event_publisher=events,
    )


@pytest.mark.asyncio
class TestPluginRuntime:
    async def test_initialize_plugin_state(self, runtime):
        plugin = make_plugin("p1", PluginStatus.LOADED)
        runtime._registry.register(plugin)
        result = await runtime.initialize_plugin("p1")
        assert result.state.status == PluginStatus.INITIALIZING

    async def test_start_plugin_calls_instance_start(self, runtime):
        instance = MockPluginInstance()
        plugin = make_plugin("p1", PluginStatus.INITIALIZING, instance=instance)
        runtime._registry.register(plugin)
        await runtime._health.initialize("p1")
        result = await runtime.start_plugin("p1")
        assert result.state.status == PluginStatus.ACTIVE
        instance.start.assert_awaited_once()

    async def test_start_plugin_without_instance(self, runtime):
        plugin = make_plugin("p1", PluginStatus.INITIALIZING)
        runtime._registry.register(plugin)
        await runtime._health.initialize("p1")
        result = await runtime.start_plugin("p1")
        assert result.state.status == PluginStatus.ACTIVE

    async def test_start_plugin_handles_instance_failure(self, runtime):
        instance = MockPluginInstance()
        instance.start.side_effect = RuntimeError("start failed")
        plugin = make_plugin("p1", PluginStatus.INITIALIZING, instance=instance)
        runtime._registry.register(plugin)
        await runtime._health.initialize("p1")
        result = await runtime.start_plugin("p1")
        assert result.state.status == PluginStatus.FAILED

    async def test_stop_plugin_calls_instance_stop(self, runtime):
        instance = MockPluginInstance()
        plugin = make_plugin("p1", PluginStatus.ACTIVE, instance=instance)
        runtime._registry.register(plugin)
        result = await runtime.stop_plugin("p1")
        assert result.state.status == PluginStatus.STOPPED
        instance.stop.assert_awaited_once()

    async def test_stop_plugin_when_not_active(self, runtime):
        plugin = make_plugin("p1", PluginStatus.STOPPED)
        runtime._registry.register(plugin)
        result = await runtime.stop_plugin("p1")
        assert result.state.status == PluginStatus.STOPPED

    async def test_unload_plugin_calls_shutdown_and_dispose(self, runtime):
        instance = MockPluginInstance()
        plugin = make_plugin("p1", PluginStatus.STOPPED, instance=instance)
        runtime._registry.register(plugin)
        await runtime.unload_plugin("p1")
        instance.shutdown.assert_awaited_once()
        instance.dispose.assert_awaited_once()
        assert plugin.state.status == PluginStatus.UNLOADED

    async def test_unload_plugin_without_instance(self, runtime):
        plugin = make_plugin("p1", PluginStatus.STOPPED)
        runtime._registry.register(plugin)
        await runtime.unload_plugin("p1")
        assert plugin.state.status == PluginStatus.UNLOADED

    async def test_remove_plugin_unloads_and_removes(self, runtime):
        instance = MockPluginInstance()
        plugin = make_plugin("p1", PluginStatus.STOPPED, instance=instance)
        runtime._registry.register(plugin)
        result = await runtime.remove_plugin("p1")
        assert result is plugin
        assert runtime._registry.get_safe("p1") is None
        instance.shutdown.assert_awaited_once()

    async def test_recover_plugin_restarts(self, runtime):
        instance = MockPluginInstance()
        plugin = make_plugin("p1", PluginStatus.FAILED, instance=instance)
        runtime._registry.register(plugin)
        result = await runtime.recover_plugin("p1")
        assert result.state.status == PluginStatus.ACTIVE
        instance.start.assert_awaited_once()

    async def test_recover_plugin_when_not_failed(self, runtime):
        plugin = make_plugin("p1", PluginStatus.ACTIVE)
        runtime._registry.register(plugin)
        result = await runtime.recover_plugin("p1")
        assert result.state.status == PluginStatus.ACTIVE

    async def test_recover_plugin_handles_failure(self, runtime):
        instance = MockPluginInstance()
        instance.start.side_effect = RuntimeError("recover failed")
        plugin = make_plugin("p1", PluginStatus.FAILED, instance=instance)
        runtime._registry.register(plugin)
        result = await runtime.recover_plugin("p1")
        assert result.state.status == PluginStatus.FAILED

    async def test_get_plugin_status(self, runtime):
        plugin = make_plugin("p1", PluginStatus.ACTIVE)
        runtime._registry.register(plugin)
        status = await runtime.get_plugin_status("p1")
        assert status == PluginStatus.ACTIVE

    async def test_get_plugin_health(self, runtime):
        plugin = make_plugin("p1", PluginStatus.ACTIVE)
        runtime._registry.register(plugin)
        await runtime._health.initialize("p1")
        health = await runtime.get_plugin_health("p1")
        assert health is not None