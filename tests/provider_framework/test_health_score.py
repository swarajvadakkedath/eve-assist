"""Tests for W5 — health score + success_rate in HealthMonitor."""

import asyncio

import pytest

from aios.core.health_monitor import HealthMonitor, HealthState, ProviderHealth
from aios.core.adapters.base import ProviderStatus


class TestSuccessRate:
    def test_initial_values(self):
        h = ProviderHealth(provider_id="x")
        assert h.total_checks == 0
        assert h.successful_checks == 0
        assert h.success_rate == 1.0
        assert h.health_score == 100.0

    def test_all_success_rate_is_1(self):
        h = ProviderHealth(provider_id="x")
        h.record_success(100)
        h.record_success(150)
        assert h.success_rate == 1.0
        assert h.successful_checks == 2
        assert h.total_checks == 2

    def test_mixed_success_rate(self):
        h = ProviderHealth(provider_id="x")
        h.record_success(100)
        h.record_success(100)
        h.record_failure(ProviderStatus.ERROR, "boom")
        assert h.success_rate == pytest.approx(0.6667, abs=1e-4)
        assert h.total_checks == 3
        assert h.successful_checks == 2

    def test_all_failures_rate_is_0(self):
        h = ProviderHealth(provider_id="x")
        h.record_failure(ProviderStatus.ERROR, "boom")
        h.record_failure(ProviderStatus.ERROR, "boom")
        assert h.success_rate == 0.0


class TestHealthScore:
    def test_score_100_after_successes(self):
        h = ProviderHealth(provider_id="x")
        h.record_success(100)
        h.record_success(100)
        assert h.health_score == 100.0

    def test_score_drops_with_failures(self):
        h = ProviderHealth(provider_id="x")
        h.record_success(100)
        h.record_failure(ProviderStatus.ERROR, "boom")
        assert h.health_score < 100.0

    def test_unreachable_state_scores_zero(self):
        h = ProviderHealth(provider_id="x")
        h.record_failure(ProviderStatus.OFFLINE, "offline")
        h.record_failure(ProviderStatus.OFFLINE, "offline")
        assert h.state == HealthState.UNREACHABLE
        assert h.health_score == 0.0

    def test_invalid_key_scores_zero(self):
        h = ProviderHealth(provider_id="x")
        h.record_failure(ProviderStatus.INVALID_KEY, "401")
        assert h.state == HealthState.INVALID_KEY
        assert h.health_score == 0.0

    def test_timeout_is_degraded_not_zero(self):
        h = ProviderHealth(provider_id="x")
        h.record_success(100)
        h.record_failure(ProviderStatus.TIMEOUT, "timeout")
        assert h.state == HealthState.DEGRADED
        assert 0 < h.health_score < 100


class TestHealthMonitorIntegration:
    async def test_check_all_records_scores(self):
        adapter = _FakeHealthAdapter("ok")

        class _HM:
            def __init__(self):
                self._h = {}

            def get_health(self, pid):
                return self._h.get(pid)

            def register_provider(self, pid):
                self._h[pid] = ProviderHealth(provider_id=pid)

        hm = _HM()
        monitor = HealthMonitor()
        monitor.register_provider("ok")
        results = await monitor.check_all({"ok": adapter})
        health = results["ok"]
        assert health.success_rate == 1.0
        assert health.health_score == 100.0
        assert health.total_checks == 1

    def test_to_dict_includes_new_fields(self):
        h = ProviderHealth(provider_id="x")
        h.record_success(50)
        d = h.to_dict()
        for key in ("success_rate", "health_score", "total_checks", "successful_checks"):
            assert key in d


class _FakeHealthAdapter:
    def __init__(self, provider_id):
        self._provider_id = provider_id

    @property
    def provider_id(self):
        return self._provider_id

    async def health(self):
        return ProviderStatus.CONNECTED
