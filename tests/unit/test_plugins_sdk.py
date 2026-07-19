"""Unit tests for the AIOSPlugin SDK base class."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.plugins.sdk import AIOSPlugin
from aios.plugins.manifest import PluginManifest
from aios.plugins.models import PluginCapability, PluginResult


class ConcretePlugin(AIOSPlugin):
    async def initialize(self):
        self._initialized = True
    async def register(self):
        self._registered = True
    async def start(self):
        self._started = True
    async def stop(self):
        self._stopped = True
    async def health(self):
        return {"status": "custom_alive"}
    async def shutdown(self):
        self._shutdown = True
    async def dispose(self):
        self._disposed = True


@pytest.fixture
def plugin():
    p = ConcretePlugin()
    p.metadata = PluginManifest(id="test-p", name="Test Plugin", version="1.0.0")
    return p


@pytest.mark.asyncio
class TestAIOSPlugin:
    async def test_abstract_methods_require_implementation(self):
        class IncompletePlugin(AIOSPlugin):
            pass
        with pytest.raises(TypeError):
            IncompletePlugin()

    async def test_initialize_and_register(self, plugin):
        await plugin.initialize()
        assert plugin._initialized
        await plugin.register()
        assert plugin._registered

    async def test_lifecycle_methods(self, plugin):
        await plugin.start()
        assert plugin._started
        await plugin.stop()
        assert plugin._stopped
        await plugin.shutdown()
        assert plugin._shutdown
        await plugin.dispose()
        assert plugin._disposed

    async def test_health_default(self):
        p = ConcretePlugin()
        result = await p.health()
        assert result["status"] == "custom_alive"

    async def test_plugin_id_property(self, plugin):
        assert plugin.plugin_id == "test-p"

    async def test_plugin_id_unknown(self):
        p = ConcretePlugin()
        assert p.plugin_id == "unknown"

    async def test_plugin_name_property(self, plugin):
        assert plugin.plugin_name == "Test Plugin"

    async def test_plugin_name_unknown(self):
        p = ConcretePlugin()
        assert p.plugin_name == "Unknown Plugin"

    async def test_publish_event_without_bus_is_noop(self, plugin):
        result = await plugin.publish_event("test.event", {"key": "val"})
        assert result is None

    async def test_request_permission_without_manager(self, plugin):
        granted = await plugin.request_permission("filesystem.read", level=1)
        assert granted is False

    async def test_register_tool_without_manager(self, plugin):
        result = await plugin.register_tool({"id": "test-tool", "name": "Test"})
        assert result is False

    async def test_register_capability_without_registry(self, plugin):
        cap = PluginCapability(id="test.cap", name="Test Cap")
        result = await plugin.register_capability(cap)
        assert result is False

    async def test_get_setting_without_settings(self, plugin):
        val = await plugin.get_setting("key", "default")
        assert val == "default"

    async def test_log_methods_dont_raise(self, plugin):
        plugin.log_info("test info")
        plugin.log_error("test error")
        plugin.log_warning("test warning")
        plugin.log_debug("test debug")

    async def test_inject_services(self, plugin):
        event_bus = MagicMock()
        perm_mgr = MagicMock()
        tool_mgr = MagicMock()
        cap_reg = MagicMock()
        settings = MagicMock()
        plugin._inject_services(event_bus, perm_mgr, tool_mgr, cap_reg, settings)
        assert plugin._event_bus is event_bus
        assert plugin._permission_manager is perm_mgr
        assert plugin._tool_manager is tool_mgr
        assert plugin._capability_registry is cap_reg
        assert plugin._settings is settings