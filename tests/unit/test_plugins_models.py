"""Unit tests for plugin models."""

import pytest
from datetime import datetime, timezone
from aios.plugins.models import (
    Plugin,
    PluginMetadata,
    PluginCapability,
    PluginPermission,
    PluginDependency,
    PluginHealth,
    PluginContext,
    PluginConfiguration,
    PluginState,
    PluginResult,
    PluginVersion,
    PluginStatus,
    PluginScope,
    PluginHealthStatus,
    IsolationStrategy,
)
from aios.plugins.manifest import PluginManifest


class TestPluginStatus:
    def test_all_statuses_are_strings(self):
        for status in PluginStatus:
            assert isinstance(status.value, str)

    def test_key_statuses_exist(self):
        assert PluginStatus.ACTIVE
        assert PluginStatus.FAILED
        assert PluginStatus.LOADED
        assert PluginStatus.STOPPED
        assert PluginStatus.DISABLED


class TestPluginMetadata:
    def test_defaults(self):
        m = PluginMetadata()
        assert m.id == ""
        assert m.name == ""
        assert m.license == "MIT"
        assert m.platforms == ["windows"]

    def test_to_dict(self):
        m = PluginMetadata(id="p1", name="Plugin One", version="1.0.0")
        d = m.to_dict()
        assert d["id"] == "p1"
        assert d["name"] == "Plugin One"
        assert d["version"] == "1.0.0"


class TestPluginCapability:
    def test_required_fields(self):
        cap = PluginCapability(id="cap1", name="My Cap")
        assert cap.id == "cap1"
        assert cap.name == "My Cap"
        assert cap.permission_level == 1
        assert cap.timeout == 30

    def test_to_dict(self):
        cap = PluginCapability(id="cap1", name="My Cap", description="Does something")
        d = cap.to_dict()
        assert d["id"] == "cap1"
        assert d["description"] == "Does something"


class TestPluginPermission:
    def test_defaults(self):
        perm = PluginPermission(permission="read")
        assert perm.level == 1
        assert perm.granted is False

    def test_to_dict(self):
        perm = PluginPermission(permission="write", level=2, granted=True)
        d = perm.to_dict()
        assert d["permission"] == "write"
        assert d["level"] == 2
        assert d["granted"] is True


class TestPluginDependency:
    def test_defaults(self):
        dep = PluginDependency(plugin_id="other-plugin")
        assert dep.version_spec == ""
        assert dep.optional is False
        assert dep.resolved is False

    def test_to_dict(self):
        dep = PluginDependency(plugin_id="other-plugin", version_spec=">=1.0.0")
        d = dep.to_dict()
        assert d["plugin_id"] == "other-plugin"
        assert d["version_spec"] == ">=1.0.0"


class TestPluginHealth:
    def test_defaults(self):
        h = PluginHealth()
        assert h.status == PluginHealthStatus.STARTING
        assert h.startup_time_ms == 0.0
        assert h.error_count == 0
        assert h.restart_count == 0

    def test_to_dict(self):
        h = PluginHealth(status=PluginHealthStatus.RUNNING, error_count=2)
        d = h.to_dict()
        assert d["status"] == "running"
        assert d["error_count"] == 2
        assert d["last_heartbeat"] is None

    def test_to_dict_with_heartbeat(self):
        h = PluginHealth(last_heartbeat=datetime.now(timezone.utc))
        d = h.to_dict()
        assert d["last_heartbeat"] is not None


class TestPluginState:
    def test_defaults(self):
        s = PluginState()
        assert s.status == PluginStatus.DISCOVERED
        assert s.error is None
        assert s.started_at is None

    def test_to_dict(self):
        s = PluginState(status=PluginStatus.ACTIVE)
        d = s.to_dict()
        assert d["status"] == "active"
        assert d["error"] is None


class TestPluginConfiguration:
    def test_defaults(self):
        cfg = PluginConfiguration(plugin_id="p1")
        assert cfg.enabled is True
        assert cfg.auto_start is True
        assert cfg.isolation == IsolationStrategy.IN_PROCESS

    def test_to_dict(self):
        cfg = PluginConfiguration(plugin_id="p1", enabled=False)
        d = cfg.to_dict()
        assert d["plugin_id"] == "p1"
        assert d["enabled"] is False
        assert d["isolation"] == "in_process"


class TestPluginResult:
    def test_success(self):
        r = PluginResult(success=True, data={"result": 42})
        assert r.success is True
        assert r.data == {"result": 42}
        assert r.error is None

    def test_failure(self):
        r = PluginResult(success=False, error="something broke")
        assert r.success is False
        assert r.error == "something broke"


class TestPlugin:
    def test_auto_id_generation(self):
        p = Plugin()
        assert p.id != ""
        assert len(p.id) > 0

    def test_explicit_id(self):
        p = Plugin(id="my-plugin")
        assert p.id == "my-plugin"

    def test_is_active(self):
        p = Plugin(id="p1")
        assert p.is_active is False
        p.state.status = PluginStatus.ACTIVE
        assert p.is_active is True

    def test_is_failed(self):
        p = Plugin(id="p1")
        assert p.is_failed is False
        p.state.status = PluginStatus.FAILED
        assert p.is_failed is True

    def test_status_property(self):
        p = Plugin(id="p1")
        assert p.status == PluginStatus.DISCOVERED

    def test_health_property(self):
        p = Plugin(id="p1")
        assert isinstance(p.health, PluginHealth)

    def test_to_dict(self):
        p = Plugin(id="p1", scope=PluginScope.BUILTIN)
        d = p.to_dict()
        assert d["id"] == "p1"
        assert d["scope"] == "builtin"
        assert "state" in d
        assert "capabilities" in d
        assert "dependencies" in d
