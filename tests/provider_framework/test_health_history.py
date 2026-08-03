"""Tests for ProviderHealth history augmentation and GET /providers/health/history endpoint."""

import asyncio
import pytest
import time
from unittest.mock import MagicMock
from aios.core.health_monitor import ProviderHealth, HealthMonitor, HealthState
from aios.core.adapters.base import ProviderStatus


class TestHealthHistoryAugmentation:
    """Verify that history entries include health_score and success_rate."""

    def test_record_success_includes_score_fields(self):
        h = ProviderHealth(provider_id="test-1")
        h.record_success(120.0)
        entries = h.history
        assert len(entries) == 1
        e = entries[0]
        assert e["type"] == "success"
        assert e["latency_ms"] == 120.0
        assert "health_score" in e
        assert "success_rate" in e
        assert e["health_score"] >= 0
        assert e["success_rate"] >= 0

    def test_record_failure_includes_score_fields(self):
        h = ProviderHealth(provider_id="test-2")
        h.record_failure(ProviderStatus.OFFLINE, "unreachable", 50.0)
        entries = h.history
        assert len(entries) == 1
        e = entries[0]
        assert e["type"] == "failure"
        assert e["status"] == "offline"
        assert "health_score" in e
        assert "success_rate" in e
        assert e["error"] == "unreachable"

    def test_history_capped_at_100(self):
        h = ProviderHealth(provider_id="test-3")
        for i in range(120):
            h.record_success(10.0 + i)
        assert len(h.history) == 100

    def test_success_then_failure_history_order(self):
        h = ProviderHealth(provider_id="test-4")
        h.record_success(10.0)
        h.record_failure(ProviderStatus.TIMEOUT, "timeout", 5000.0)
        h.record_success(20.0)
        assert len(h.history) == 3
        assert h.history[0]["type"] == "success"
        assert h.history[1]["type"] == "failure"
        assert h.history[1]["status"] == "timeout"
        assert h.history[2]["type"] == "success"

    def test_health_score_decreases_after_failures(self):
        h = ProviderHealth(provider_id="test-5")
        h.record_success(10.0)
        score_after_success = h.health_score
        h.record_failure(ProviderStatus.OFFLINE, "down", 0.0)
        score_after_failure = h.health_score
        assert score_after_failure < score_after_success


class TestHealthHistoryEndpointShape:
    """Test the /providers/health/history endpoint via mocked request."""

    def _mock_request(self, health_monitor: HealthMonitor) -> MagicMock:
        manager = MagicMock()
        manager.health_monitor = health_monitor
        req = MagicMock()
        req.app = MagicMock()
        req.app.state = MagicMock()
        req.app.state.provider_manager = manager
        return req

    def test_empty_history_returns_empty(self):
        from aios.api.providers import get_health_history
        monitor = HealthMonitor()
        req = self._mock_request(monitor)
        result = asyncio.run(get_health_history(req, limit=60))
        assert result == {"history": {}}

    def test_single_provider_history(self):
        from aios.api.providers import get_health_history
        monitor = HealthMonitor()
        monitor.register_provider("p1")
        h = monitor.get_health("p1")
        h.record_success(150.0)
        h.record_failure(ProviderStatus.RATE_LIMITED, "429", 0.0, retry_after=60.0)
        h.record_success(200.0)

        req = self._mock_request(monitor)
        result = asyncio.run(get_health_history(req, limit=60))
        assert "history" in result
        assert "p1" in result["history"]
        entries = result["history"]["p1"]
        assert len(entries) == 3
        assert entries[0]["type"] == "success"
        assert entries[0]["state"] == "healthy"
        assert entries[1]["type"] == "failure"
        assert entries[1]["state"] == "rate_limited"
        assert entries[1]["status"] == "rate_limited"
        assert entries[2]["type"] == "success"
        assert entries[2]["state"] == "healthy"

    def test_limit_caps_entries(self):
        from aios.api.providers import get_health_history
        monitor = HealthMonitor()
        monitor.register_provider("p2")
        h = monitor.get_health("p2")
        for _ in range(50):
            h.record_success(10.0)

        req = self._mock_request(monitor)
        result = asyncio.run(get_health_history(req, limit=10))
        assert len(result["history"]["p2"]) == 10

    def test_limit_capped_at_100(self):
        from aios.api.providers import get_health_history
        monitor = HealthMonitor()
        monitor.register_provider("p3")
        h = monitor.get_health("p3")
        for _ in range(120):
            h.record_success(10.0)

        req = self._mock_request(monitor)
        result = asyncio.run(get_health_history(req, limit=200))
        assert len(result["history"]["p3"]) == 100

    def test_failure_state_mapping(self):
        from aios.api.providers import _failure_state
        assert _failure_state("auth_failed") == "invalid_key"
        assert _failure_state("invalid_key") == "invalid_key"
        assert _failure_state("rate_limited") == "rate_limited"
        assert _failure_state("quota_exceeded") == "quota_exceeded"
        assert _failure_state("timeout") == "degraded"
        assert _failure_state("offline") == "unreachable"
        assert _failure_state("disconnected") == "unreachable"
        assert _failure_state("error") == "degraded"
        assert _failure_state("something_else") == "degraded"

    def test_multiple_providers(self):
        from aios.api.providers import get_health_history
        monitor = HealthMonitor()
        for pid in ["p1", "p2", "p3"]:
            monitor.register_provider(pid)
            h = monitor.get_health(pid)
            h.record_success(10.0 + hash(pid) % 100)

        req = self._mock_request(monitor)
        result = asyncio.run(get_health_history(req, limit=60))
        assert len(result["history"]) == 3
        for pid in ["p1", "p2", "p3"]:
            assert pid in result["history"]
            assert len(result["history"][pid]) == 1
