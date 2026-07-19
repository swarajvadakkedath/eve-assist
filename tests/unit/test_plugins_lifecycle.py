"""Unit tests for plugin lifecycle state machine."""

import pytest
from aios.plugins.lifecycle import PluginLifecycle, LifecycleStage, VALID_TRANSITIONS
from aios.plugins.models import PluginStatus


class TestLifecycleStage:
    def test_all_stages_exist(self):
        stages = {s.value for s in LifecycleStage}
        assert "initialize" in stages
        assert "start" in stages
        assert "register" in stages
        assert "health" in stages
        assert "stop" in stages
        assert "shutdown" in stages
        assert "dispose" in stages


class TestPluginLifecycle:
    def setup_method(self):
        self.lifecycle = PluginLifecycle()

    # --- Valid transitions ---

    def test_discovered_to_validated(self):
        self.lifecycle.validate_transition(PluginStatus.DISCOVERED, PluginStatus.VALIDATED)

    def test_validated_to_verified(self):
        self.lifecycle.validate_transition(PluginStatus.VALIDATED, PluginStatus.VERIFIED)

    def test_verified_to_loading(self):
        self.lifecycle.validate_transition(PluginStatus.VERIFIED, PluginStatus.LOADING)

    def test_loading_to_loaded(self):
        self.lifecycle.validate_transition(PluginStatus.LOADING, PluginStatus.LOADED)

    def test_loaded_to_initializing(self):
        self.lifecycle.validate_transition(PluginStatus.LOADED, PluginStatus.INITIALIZING)

    def test_initializing_to_starting(self):
        self.lifecycle.validate_transition(PluginStatus.INITIALIZING, PluginStatus.STARTING)

    def test_starting_to_active(self):
        self.lifecycle.validate_transition(PluginStatus.STARTING, PluginStatus.ACTIVE)

    def test_active_to_stopping(self):
        self.lifecycle.validate_transition(PluginStatus.ACTIVE, PluginStatus.STOPPING)

    def test_stopping_to_stopped(self):
        self.lifecycle.validate_transition(PluginStatus.STOPPING, PluginStatus.STOPPED)

    def test_stopped_to_unloaded(self):
        self.lifecycle.validate_transition(PluginStatus.STOPPED, PluginStatus.UNLOADED)

    def test_failed_to_loading(self):
        self.lifecycle.validate_transition(PluginStatus.FAILED, PluginStatus.LOADING)

    def test_any_to_removed(self):
        for status in PluginStatus:
            transitions = VALID_TRANSITIONS.get(status, set())
            if status != PluginStatus.REMOVED:
                assert PluginStatus.REMOVED in transitions or status == PluginStatus.REMOVED, \
                    f"{status} should allow transition to REMOVED"

    # --- Invalid transitions ---

    def test_active_to_loading_invalid(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            self.lifecycle.validate_transition(PluginStatus.ACTIVE, PluginStatus.LOADING)

    def test_discovered_to_active_invalid(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            self.lifecycle.validate_transition(PluginStatus.DISCOVERED, PluginStatus.ACTIVE)

    def test_removed_has_no_transitions(self):
        with pytest.raises(ValueError, match="Invalid transition"):
            self.lifecycle.validate_transition(PluginStatus.REMOVED, PluginStatus.DISCOVERED)

    # --- can_transition ---

    def test_can_transition_valid(self):
        assert self.lifecycle.can_transition(PluginStatus.DISCOVERED, PluginStatus.VALIDATED) is True

    def test_can_transition_invalid(self):
        assert self.lifecycle.can_transition(PluginStatus.ACTIVE, PluginStatus.DISCOVERED) is False

    def test_can_transition_removed_to_any(self):
        assert self.lifecycle.can_transition(PluginStatus.REMOVED, PluginStatus.DISCOVERED) is False

    # --- get_allowed_transitions ---

    def test_get_allowed_transitions_active(self):
        allowed = self.lifecycle.get_allowed_transitions(PluginStatus.ACTIVE)
        assert PluginStatus.STOPPING in allowed
        assert PluginStatus.DEGRADED in allowed
        assert PluginStatus.FAILED in allowed
        assert PluginStatus.REMOVED in allowed

    def test_get_allowed_transitions_removed_is_empty(self):
        allowed = self.lifecycle.get_allowed_transitions(PluginStatus.REMOVED)
        assert len(allowed) == 0
