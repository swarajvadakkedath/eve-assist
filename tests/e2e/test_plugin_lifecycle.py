"""End-to-end tests for plugin lifecycle: discover → load → start → stop → unload."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

from aios.plugins.plugin_manager import PluginManager
from aios.plugins.models import PluginStatus


def create_plugin_package(base: Path, plugin_id: str) -> Path:
    pkg = base / plugin_id
    pkg.mkdir()
    (pkg / "plugin.yaml").write_text(
        f"id: {plugin_id}\n"
        f"name: {plugin_id.replace('-', ' ').title()}\n"
        "version: 1.0.0\n"
        "sdk_version: 1.0.0\n"
        "author: E2E Test\n"
        "description: End-to-end test plugin\n"
        "entry_point: plugin.py\n"
        "platforms: [all]\n"
        "minimum_aios_version: 1.0.0\n"
        "capabilities:\n"
        "  - id: test.hello\n"
        "    name: Say Hello\n"
        "    permission_level: 0\n"
    )
    (pkg / "plugin.py").write_text(
        "from aios.plugins.sdk import AIOSPlugin\n"
        "from aios.plugins.models import PluginCapability\n"
        "class E2ETestPlugin(AIOSPlugin):\n"
        "    async def initialize(self):\n"
        "        self._started = False\n"
        "    async def register(self):\n"
        "        cap = PluginCapability(id='test.hello', name='Say Hello')\n"
        "        await self.register_capability(cap)\n"
        "    async def start(self):\n"
        "        self._started = True\n"
        "    async def stop(self):\n"
        "        self._started = False\n"
        "    async def shutdown(self):\n"
        "        self._started = False\n"
        "    async def dispose(self):\n"
        "        pass\n"
    )
    return pkg


@pytest.mark.asyncio
class TestPluginLifecycleE2E:
    async def test_full_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_plugin_package(Path(tmpdir), "e2e-plugin")
            pm = PluginManager(base_path=tmpdir)
            pm._discovery.add_search_directory(tmpdir)

            manifests = await pm.scan_plugins()
            assert len(manifests) >= 1
            manifest = next(m for m in manifests if m.id == "e2e-plugin")
            assert manifest is not None

            loaded = await pm.load_plugin(manifest)
            assert loaded, "Plugin should load successfully"

            plugin = await pm.get_plugin("e2e-plugin")
            assert plugin is not None
            assert plugin.state.status == PluginStatus.ACTIVE
            assert plugin.instance is not None
            assert plugin.instance._started is True

            stopped = await pm.disable_plugin("e2e-plugin")
            assert stopped, "Plugin should disable"

            plugin = await pm.get_plugin("e2e-plugin")
            assert plugin.state.status == PluginStatus.DISABLED

            enabled = await pm.enable_plugin("e2e-plugin")
            assert enabled, "Plugin should re-enable"

            plugin = await pm.get_plugin("e2e-plugin")
            assert plugin.state.status == PluginStatus.ACTIVE

            unloaded = await pm.unload_plugin("e2e-plugin")
            assert unloaded, "Plugin should unload"

    async def test_install_and_remove(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_plugin_package(Path(tmpdir), "install-test")
            pm = PluginManager(base_path=tmpdir)

            manifests = await pm.scan_plugins(tmpdir)
            assert len(manifests) == 1
            manifest = manifests[0]
            assert manifest.id == "install-test"

            loaded = await pm.load_plugin(manifest)
            assert loaded

            plugin = await pm.get_plugin("install-test")
            assert plugin is not None
            assert plugin.state.status == PluginStatus.ACTIVE

            removed = await pm.unload_plugin("install-test")
            assert removed

            plugin = await pm.get_plugin("install-test")
            assert plugin is None or plugin.state.status == PluginStatus.UNLOADED

    async def test_reload_plugin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_plugin_package(Path(tmpdir), "reload-e2e")
            pm = PluginManager(base_path=tmpdir)
            pm._discovery.add_search_directory(tmpdir)

            manifests = await pm.scan_plugins()
            manifest = next(m for m in manifests if m.id == "reload-e2e")
            await pm.load_plugin(manifest)
            plugin = await pm.get_plugin("reload-e2e")
            assert plugin is not None
            assert plugin.state.status == PluginStatus.ACTIVE

            reloaded = await pm.reload_plugin("reload-e2e")
            assert reloaded

            plugin = await pm.get_plugin("reload-e2e")
            assert plugin is not None
            assert plugin.state.status == PluginStatus.ACTIVE

    async def test_health_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_plugin_package(Path(tmpdir), "health-plugin")
            pm = PluginManager(base_path=tmpdir)
            pm._discovery.add_search_directory(tmpdir)
            manifests = await pm.scan_plugins()
            manifest = next(m for m in manifests if m.id == "health-plugin")
            await pm.load_plugin(manifest)

            summary = await pm.get_health_summary()
            assert summary["total"] >= 1
            assert summary["active"] >= 1

            health = await pm.get_plugin_health("health-plugin")
            assert health is not None