"""Integration tests for PluginDiscovery."""

import pytest
import tempfile
import json
from pathlib import Path
from aios.plugins.discovery import PluginDiscovery
from aios.plugins.models import PluginScope


def create_plugin_package(base: Path, plugin_id: str, manifest_format: str = "yaml") -> Path:
    """Create a valid plugin package directory."""
    pkg_dir = base / plugin_id
    pkg_dir.mkdir()
    # Create entry point
    (pkg_dir / "plugin.py").write_text(f"# {plugin_id}\n")

    if manifest_format == "yaml":
        (pkg_dir / "plugin.yaml").write_text(
            f"id: {plugin_id}\n"
            f"name: {plugin_id.replace('-', ' ').title()}\n"
            "version: 1.0.0\n"
            "author: Test\n"
            "entry_point: plugin.py\n"
            "platforms: [all]\n"
        )
    else:
        manifest_data = {
            "id": plugin_id,
            "name": plugin_id.replace("-", " ").title(),
            "version": "1.0.0",
            "author": "Test",
            "entry_point": "plugin.py",
            "platforms": ["all"],
        }
        (pkg_dir / "plugin.json").write_text(json.dumps(manifest_data))

    return pkg_dir


@pytest.mark.asyncio
class TestPluginDiscovery:
    async def test_empty_discovery_returns_nothing(self):
        discovery = PluginDiscovery()
        results = await discovery.discover_all()
        assert results == []

    async def test_discover_yaml_plugin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            create_plugin_package(base, "my-plugin", "yaml")
            discovery = PluginDiscovery(user_dir=tmpdir)
            results = await discovery.discover_all()
            assert len(results) == 1
            manifest, path, scope = results[0]
            assert manifest.id == "my-plugin"
            assert scope == PluginScope.USER

    async def test_discover_json_plugin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            create_plugin_package(base, "json-plugin", "json")
            discovery = PluginDiscovery(user_dir=tmpdir)
            results = await discovery.discover_all()
            assert len(results) == 1
            manifest, path, scope = results[0]
            assert manifest.id == "json-plugin"

    async def test_discover_multiple_plugins(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            create_plugin_package(base, "plugin-a")
            create_plugin_package(base, "plugin-b")
            create_plugin_package(base, "plugin-c")
            discovery = PluginDiscovery(user_dir=tmpdir)
            results = await discovery.discover_all()
            assert len(results) == 3
            ids = {m.id for m, _, _ in results}
            assert "plugin-a" in ids
            assert "plugin-b" in ids
            assert "plugin-c" in ids

    async def test_builtin_scope_assigned(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            create_plugin_package(base, "builtin-plugin")
            discovery = PluginDiscovery(builtin_dirs=[tmpdir])
            results = await discovery.discover_all()
            assert len(results) == 1
            _, _, scope = results[0]
            assert scope == PluginScope.BUILTIN

    async def test_system_scope_assigned(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            create_plugin_package(base, "system-plugin")
            discovery = PluginDiscovery(system_dir=tmpdir)
            results = await discovery.discover_all()
            assert len(results) == 1
            _, _, scope = results[0]
            assert scope == PluginScope.SYSTEM

    async def test_directory_without_manifest_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Directory without any manifest
            (base / "not-a-plugin").mkdir()
            (base / "not-a-plugin" / "main.py").write_text("# just python")
            discovery = PluginDiscovery(user_dir=tmpdir)
            results = await discovery.discover_all()
            assert len(results) == 0

    async def test_add_search_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            create_plugin_package(Path(tmpdir1), "plugin-1")
            create_plugin_package(Path(tmpdir2), "plugin-2")
            discovery = PluginDiscovery(user_dir=tmpdir1)
            discovery.add_search_directory(tmpdir2)
            results = await discovery.discover_all()
            ids = {m.id for m, _, _ in results}
            assert "plugin-1" in ids
            assert "plugin-2" in ids

    async def test_get_search_paths(self):
        discovery = PluginDiscovery(user_dir="/tmp/user", system_dir="/tmp/system")
        paths = discovery.get_search_paths()
        assert "/tmp/user" in paths
        assert "/tmp/system" in paths

    async def test_nonexistent_directory_is_skipped(self):
        discovery = PluginDiscovery(user_dir="/nonexistent/path/12345")
        results = await discovery.discover_all()
        assert results == []

    async def test_malformed_manifest_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            bad_plugin = base / "bad-plugin"
            bad_plugin.mkdir()
            # Write invalid YAML
            (bad_plugin / "plugin.yaml").write_text("{{{{invalid yaml")
            discovery = PluginDiscovery(user_dir=tmpdir)
            # Should not raise, just skip
            results = await discovery.discover_all()
            assert len(results) == 0
