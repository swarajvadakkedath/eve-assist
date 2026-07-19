"""Tests for plugin manifest parsing."""

import json
import tempfile
from pathlib import Path

import pytest
from aios.plugins.manifest import PluginManifest


class TestPluginManifest:
    def test_manifest_defaults(self):
        m = PluginManifest(id="test-plugin", name="Test Plugin", version="1.0.0")
        assert m.id == "test-plugin"
        assert m.name == "Test Plugin"
        assert m.version == "1.0.0"
        assert m.sdk_version == "1.0.0"
        assert m.author == ""
        assert m.license == "MIT"
        assert m.platforms == ["windows"]
        assert m.permissions == []
        assert m.dependencies == {}
        assert m.entry_point == "plugin.py"

    def test_manifest_from_dict(self):
        data = {
            "id": "my-plugin",
            "name": "My Plugin",
            "version": "2.0.0",
            "author": "AIOS",
            "description": "A test plugin",
            "platforms": ["windows", "linux"],
            "capabilities": [{"id": "hello", "name": "Say Hello"}],
        }
        m = PluginManifest.from_dict(data)
        assert m.id == "my-plugin"
        assert m.name == "My Plugin"
        assert m.version == "2.0.0"
        assert m.author == "AIOS"
        assert m.platforms == ["windows", "linux"]
        assert len(m.capabilities) == 1

    def test_manifest_from_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"id": "json-plugin", "name": "JSON Plugin", "version": "1.0.0"}, f)
            f.flush()
            m = PluginManifest.from_json(f.name)
            assert m.id == "json-plugin"
            assert m.name == "JSON Plugin"
            Path(f.name).unlink()

    def test_manifest_from_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("id: yaml-plugin\nname: YAML Plugin\nversion: 1.0.0\n")
            f.flush()
            m = PluginManifest.from_yaml(f.name)
            assert m.id == "yaml-plugin"
            assert m.name == "YAML Plugin"
            Path(f.name).unlink()

    def test_manifest_load_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"id": "load-json", "name": "Load JSON", "version": "1.0.0"}, f)
            f.flush()
            m = PluginManifest.load(f.name)
            assert m.id == "load-json"
            Path(f.name).unlink()

    def test_manifest_load_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            f.write("id: load-yml\nname: Load YML\nversion: 1.0.0\n")
            f.flush()
            m = PluginManifest.load(f.name)
            assert m.id == "load-yml"
            Path(f.name).unlink()

    def test_manifest_to_dict(self):
        m = PluginManifest(id="dict-test", name="Dict Test", version="1.0.0")
        d = m.to_dict()
        assert d["id"] == "dict-test"
        assert d["name"] == "Dict Test"
        assert d["version"] == "1.0.0"
        assert d["license"] == "MIT"

    def test_manifest_invalid_format(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("[package]\nname = \"test\"\n")
            f.flush()
            with pytest.raises(ValueError):
                PluginManifest.load(f.name)
            Path(f.name).unlink()
