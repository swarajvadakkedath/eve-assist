"""Tests for W3 — SmartRouter FREE_ONLY default + commercial policy persistence."""

import json

import pytest

from aios.core.provider_manager import ProviderManager
from aios.core.routing_types import CommercialPolicy


@pytest.fixture
def manager_factory(tmp_path):
    def make(routing_json):
        (tmp_path / "providers.json").write_text(json.dumps([]), "utf-8")
        (tmp_path / "routing.json").write_text(json.dumps(routing_json), "utf-8")
        return ProviderManager(config_dir=str(tmp_path))
    return make


class TestDefaultPolicy:
    def test_smart_router_default_is_free_only(self):
        from aios.core.smart_router import SmartRouter
        assert SmartRouter().commercial_policy == CommercialPolicy.FREE_ONLY

    def test_fresh_manager_defaults_to_free_only(self, manager_factory):
        m = manager_factory([])
        assert m.get_commercial_policy() == "free_only"


class TestLegacyMigration:
    def test_legacy_list_migrates_to_free_only(self, manager_factory):
        legacy = [
            {"id": "general_chat", "label": "General Chat", "provider_id": None, "model_id": None},
        ]
        m = manager_factory(legacy)
        assert m.get_commercial_policy() == "free_only"
        # routing.json rewritten to new dict format
        raw = json.loads((m._routing_file).read_text("utf-8"))
        assert isinstance(raw, dict)
        assert raw["commercial_policy"] == "free_only"
        assert raw["routing"][0]["id"] == "general_chat"


class TestPolicyPersistence:
    def test_set_policy_round_trips(self, manager_factory):
        m = manager_factory([])
        m.set_commercial_policy(CommercialPolicy.NO_DIRECT_PAID)
        m2 = ProviderManager(config_dir=str(m._config_dir))
        assert m2.get_commercial_policy() == "no_direct_paid"

    def test_set_policy_persists_in_file(self, manager_factory):
        m = manager_factory([])
        m.set_commercial_policy("allow_paid")
        raw = json.loads((m._routing_file).read_text("utf-8"))
        assert raw["commercial_policy"] == "allow_paid"

    def test_invalid_policy_raises(self, manager_factory):
        m = manager_factory([])
        with pytest.raises(ValueError):
            m.set_commercial_policy("not_a_policy")
