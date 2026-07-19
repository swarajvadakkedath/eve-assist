"""Unit tests for PluginHealthMonitor."""

import asyncio
import pytest
from aios.plugins.health import PluginHealthMonitor
from aios.plugins.models import PluginHealthStatus


@pytest.mark.asyncio
class TestPluginHealthMonitor:
    async def test_initialize_creates_health(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        health = await monitor.get_health("p1")
        assert health is not None
        assert health.status == PluginHealthStatus.STARTING

    async def test_mark_running(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.mark_running("p1")
        health = await monitor.get_health("p1")
        assert health.status == PluginHealthStatus.RUNNING
        assert health.startup_time_ms >= 0

    async def test_mark_failed(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.mark_failed("p1", "out of memory")
        health = await monitor.get_health("p1")
        assert health.status == PluginHealthStatus.FAILED
        assert health.error_count == 1
        assert health.last_error == "out of memory"

    async def test_mark_failed_increments_error_count(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.mark_failed("p1", "err1")
        await monitor.mark_failed("p1", "err2")
        health = await monitor.get_health("p1")
        assert health.error_count == 2
        assert health.last_error == "err2"

    async def test_mark_degraded(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.mark_degraded("p1", "slow response")
        health = await monitor.get_health("p1")
        assert health.status == PluginHealthStatus.DEGRADED
        assert health.last_error == "slow response"

    async def test_mark_stopped(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.mark_running("p1")
        await monitor.mark_stopped("p1")
        health = await monitor.get_health("p1")
        assert health.status == PluginHealthStatus.STOPPED

    async def test_heartbeat_updates_timestamp(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.mark_running("p1")
        health1 = await monitor.get_health("p1")
        ts1 = health1.last_heartbeat

        await asyncio.sleep(0.01)
        await monitor.heartbeat("p1")
        health2 = await monitor.get_health("p1")
        assert health2.last_heartbeat >= ts1

    async def test_restart_tracked(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.restart_tracked("p1")
        health = await monitor.get_health("p1")
        assert health.restart_count == 1

    async def test_restart_tracked_multiple(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.restart_tracked("p1")
        await monitor.restart_tracked("p1")
        await monitor.restart_tracked("p1")
        health = await monitor.get_health("p1")
        assert health.restart_count == 3

    async def test_remove_clears_health(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.remove("p1")
        health = await monitor.get_health("p1")
        assert health is None

    async def test_operations_on_unknown_plugin_are_no_ops(self):
        monitor = PluginHealthMonitor()
        # These should not raise
        await monitor.mark_running("ghost")
        await monitor.mark_failed("ghost", "err")
        await monitor.mark_stopped("ghost")
        await monitor.heartbeat("ghost")
        health = await monitor.get_health("ghost")
        assert health is None

    async def test_uptime_increases_over_time(self):
        monitor = PluginHealthMonitor()
        await monitor.initialize("p1")
        await monitor.mark_running("p1")
        health1 = await monitor.get_health("p1")
        uptime1 = health1.uptime_seconds

        await asyncio.sleep(0.05)
        health2 = await monitor.get_health("p1")
        uptime2 = health2.uptime_seconds

        assert uptime2 > uptime1
