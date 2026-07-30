"""Tests for SmartRouter."""

from aios.core.smart_router import SmartRouter, RoutingEntry, ROUTING_CATEGORIES
from aios.core.model_info import ModelInfo
from aios.core.health_monitor import HealthMonitor


def test_routing_categories_defined():
    ids = {c["id"] for c in ROUTING_CATEGORIES}
    assert "general_chat" in ids
    assert "coding" in ids
    assert "vision" in ids
    assert "reasoning" in ids
    assert "fallback" in ids


def test_routing_entry_defaults():
    entry = RoutingEntry(id="test", label="Test")
    assert entry.provider_id is None
    assert entry.model_id is None


def test_smart_router_init():
    router = SmartRouter()
    assert router.get_routing_config() == []


def test_smart_router_set_routing_config():
    router = SmartRouter()
    config = [
        {"id": "general_chat", "label": "General Chat", "provider_id": "p1", "model_id": "m1"},
    ]
    router.set_routing_config(config)
    entries = router.get_routing_config()
    assert len(entries) == 1
    assert entries[0].provider_id == "p1"
    assert entries[0].model_id == "m1"


def test_smart_router_register_adapter():
    router = SmartRouter()
    from aios.core.adapters.base import AIProviderAdapter
    from unittest.mock import MagicMock
    adapter = MagicMock(spec=AIProviderAdapter)
    adapter.provider_id = "test-provider"
    router.register_adapter("test-provider", adapter)
    assert router.get_adapter("test-provider") is adapter


def test_smart_router_set_provider_models():
    router = SmartRouter()
    from unittest.mock import MagicMock
    from aios.core.adapters.base import AIProviderAdapter
    adapter = MagicMock(spec=AIProviderAdapter)
    adapter.provider_id = "p1"
    router.register_adapter("p1", adapter)
    models = [
        ModelInfo(id="m1", display_name="M1", provider_id="p1", provider_name="P1"),
        ModelInfo(id="m2", display_name="M2", provider_id="p1", provider_name="P1", enabled=False),
    ]
    router.set_provider_models("p1", models)
    summary = router.get_capability_summary()
    assert "p1" in summary
    assert len(summary["p1"]["models"]) == 1  # only enabled


def test_smart_router_get_capability_summary():
    router = SmartRouter()
    from unittest.mock import MagicMock
    from aios.core.adapters.base import AIProviderAdapter
    adapter = MagicMock(spec=AIProviderAdapter)
    adapter.provider_id = "p1"
    router.register_adapter("p1", adapter)
    models = [
        ModelInfo(id="m1", display_name="M1", provider_id="p1", provider_name="P1",
                  supports_vision=True, supports_streaming=True),
    ]
    router.set_provider_models("p1", models)
    summary = router.get_capability_summary()
    assert "p1" in summary
    caps = summary["p1"]["capabilities"]
    assert "vision" in caps
    assert "streaming" in caps
