"""Unit tests for PluginRegistry."""

import pytest
from aios.plugins.registry import PluginRegistry
from aios.plugins.models import Plugin, PluginStatus
from aios.plugins.exceptions import PluginNotFoundError


def make_plugin(pid: str, status: PluginStatus = PluginStatus.LOADED) -> Plugin:
    p = Plugin(id=pid)
    p.state.status = status
    return p


class TestPluginRegistry:
    def setup_method(self):
        self.registry = PluginRegistry()

    def test_register_and_get(self):
        p = make_plugin("p1")
        self.registry.register(p)
        result = self.registry.get("p1")
        assert result is p

    def test_get_nonexistent_raises(self):
        with pytest.raises(PluginNotFoundError):
            self.registry.get("ghost")

    def test_get_safe_returns_none(self):
        result = self.registry.get_safe("ghost")
        assert result is None

    def test_get_safe_returns_plugin(self):
        p = make_plugin("p1")
        self.registry.register(p)
        result = self.registry.get_safe("p1")
        assert result is p

    def test_list_empty(self):
        assert self.registry.list() == []

    def test_list_returns_all(self):
        self.registry.register(make_plugin("p1"))
        self.registry.register(make_plugin("p2"))
        plugins = self.registry.list()
        assert len(plugins) == 2
        ids = {p.id for p in plugins}
        assert "p1" in ids
        assert "p2" in ids

    def test_list_active_filters_correctly(self):
        self.registry.register(make_plugin("p1", PluginStatus.ACTIVE))
        self.registry.register(make_plugin("p2", PluginStatus.FAILED))
        self.registry.register(make_plugin("p3", PluginStatus.ACTIVE))
        active = self.registry.list_active()
        assert len(active) == 2
        ids = {p.id for p in active}
        assert "p1" in ids
        assert "p3" in ids

    def test_remove_existing(self):
        self.registry.register(make_plugin("p1"))
        removed = self.registry.remove("p1")
        assert removed is not None
        assert self.registry.get_safe("p1") is None

    def test_remove_nonexistent_returns_none(self):
        result = self.registry.remove("ghost")
        assert result is None

    def test_exists_true(self):
        self.registry.register(make_plugin("p1"))
        assert self.registry.exists("p1") is True

    def test_exists_false(self):
        assert self.registry.exists("ghost") is False

    def test_count(self):
        assert self.registry.count == 0
        self.registry.register(make_plugin("p1"))
        self.registry.register(make_plugin("p2"))
        assert self.registry.count == 2

    def test_clear(self):
        self.registry.register(make_plugin("p1"))
        self.registry.register(make_plugin("p2"))
        self.registry.clear()
        assert self.registry.count == 0

    def test_register_without_id_raises(self):
        p = Plugin()
        p.id = ""
        with pytest.raises(ValueError):
            self.registry.register(p)

    def test_overwrite_existing(self):
        p1a = make_plugin("p1")
        p1b = make_plugin("p1")
        self.registry.register(p1a)
        self.registry.register(p1b)
        # Latest registration wins
        assert self.registry.get("p1") is p1b
        assert self.registry.count == 1
