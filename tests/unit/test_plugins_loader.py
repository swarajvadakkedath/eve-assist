"""Unit tests for PluginLoader — discovery, validation, and instantiation."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from aios.plugins.loader import PluginLoader
from aios.plugins.manifest import PluginManifest
from aios.plugins.registry import PluginRegistry
from aios.plugins.discovery import PluginDiscovery
from aios.plugins.validator import PluginValidator
from aios.plugins.verifier import PluginVerifier
from aios.plugins.lifecycle import PluginLifecycle
from aios.plugins.events import PluginEventPublisher
from aios.plugins.models import Plugin, PluginStatus


def create_plugin_package(base: Path, plugin_id: str, extra_code: str = "") -> Path:
    pkg = base / plugin_id
    pkg.mkdir()
    (pkg / "plugin.yaml").write_text(
        f"id: {plugin_id}\n"
        f"name: {plugin_id.replace('-', ' ').title()}\n"
        "version: 1.0.0\n"
        "sdk_version: 1.0.0\n"
        "author: Tester\n"
        "description: A test plugin\n"
        "entry_point: plugin.py\n"
        "platforms: [all]\n"
        "minimum_aios_version: 1.0.0\n"
    )
    (pkg / "plugin.py").write_text(
        "from aios.plugins.sdk import AIOSPlugin\n"
        "from aios.plugins.models import PluginResult, PluginCapability\n"
        "class TestPlugin(AIOSPlugin):\n"
        "    async def initialize(self): pass\n"
        "    async def register(self): pass\n"
        f"{extra_code}\n"
        "async def execute(params):\n"
        "    return PluginResult(success=True, data=params)\n"
    )
    return pkg


@pytest.fixture
def loader():
    registry = PluginRegistry()
    discovery = PluginDiscovery()
    validator = PluginValidator()
    verifier = PluginVerifier()
    lifecycle = PluginLifecycle()
    events = PluginEventPublisher(event_bus=AsyncMock())
    return PluginLoader(
        registry=registry,
        discovery=discovery,
        validator=validator,
        verifier=verifier,
        lifecycle=lifecycle,
        event_publisher=events,
    )


@pytest.mark.asyncio
class TestPluginLoader:
    async def test_load_all_empty(self, loader):
        plugins = await loader.load_all()
        assert plugins == []

    async def test_load_single_not_found(self, loader):
        plugin = await loader.load_single("nonexistent")
        assert plugin is None

    async def test_load_single_valid_plugin(self, loader):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_plugin_package(Path(tmpdir), "test-plugin")
            loader._discovery.add_search_directory(tmpdir)
            plugin = await loader.load_single("test-plugin")
            assert plugin is not None
            assert plugin.id == "test-plugin"
            assert plugin.state.status == PluginStatus.LOADED
            assert plugin.instance is not None

    async def test_load_all_discovers_and_loads(self, loader):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            create_plugin_package(base, "plugin-a")
            create_plugin_package(base, "plugin-b")
            loader._discovery.add_search_directory(tmpdir)
            plugins = await loader.load_all()
            assert len(plugins) == 2
            ids = {p.id for p in plugins}
            assert "plugin-a" in ids
            assert "plugin-b" in ids
            for p in plugins:
                assert p.state.status == PluginStatus.LOADED
                assert p.instance is not None

    async def test_load_plugin_with_capabilities(self, loader):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "cap-plugin"
            pkg.mkdir()
            (pkg / "plugin.yaml").write_text(
                "id: cap-plugin\n"
                "name: Cap Plugin\n"
                "version: 1.0.0\n"
                "author: Tester\n"
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
                "class CapPlugin(AIOSPlugin):\n"
                "    async def initialize(self): pass\n"
                "    async def register(self): pass\n"
            )
            loader._discovery.add_search_directory(tmpdir)
            plugin = await loader.load_single("cap-plugin")
            assert plugin is not None
            assert len(plugin.capabilities) == 1
            assert plugin.capabilities[0].id == "test.hello"

    async def test_load_without_plugin_class(self, loader):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "simple-plugin"
            pkg.mkdir()
            (pkg / "plugin.yaml").write_text(
                "id: simple-plugin\n"
                "name: Simple\n"
                "version: 1.0.0\n"
                "author: Tester\n"
                "entry_point: plugin.py\n"
                "platforms: [all]\n"
                "minimum_aios_version: 1.0.0\n"
            )
            (pkg / "plugin.py").write_text(
                "async def execute(params): return {'done': True}\n"
            )
            loader._discovery.add_search_directory(tmpdir)
            plugin = await loader.load_single("simple-plugin")
            assert plugin is not None
            assert plugin.instance is None  # No AIOSPlugin subclass found
            assert plugin.state.status == PluginStatus.LOADED

    async def test_validation_failure_stops_load(self, loader):
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = Path(tmpdir) / "bad-plugin"
            pkg.mkdir()
            (pkg / "plugin.yaml").write_text(
                "id: ''\n"  # Invalid: empty id
                "name: Bad\n"
                "version: 1.0.0\n"
                "entry_point: plugin.py\n"
            )
            (pkg / "plugin.py").write_text("# empty")
            loader._discovery.add_search_directory(tmpdir)
            plugin = await loader.load_single("bad-plugin")
            assert plugin is None  # Validation failure is caught and logged

    async def test_reload_after_load(self, loader):
        with tempfile.TemporaryDirectory() as tmpdir:
            create_plugin_package(Path(tmpdir), "reload-plugin")
            loader._discovery.add_search_directory(tmpdir)
            p1 = await loader.load_single("reload-plugin")
            assert p1 is not None
            p2 = await loader.reload("reload-plugin")
            assert p2 is not None
            assert p2.id == "reload-plugin"