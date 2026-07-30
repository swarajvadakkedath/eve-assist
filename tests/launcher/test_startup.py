"""Tests for startup orchestrator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from launcher.startup import StartupOrchestrator, wait_for_url
from launcher.process_manager import ProcessManager
from launcher.health_checker import HealthChecker
from launcher.config import LauncherConfig


@pytest.fixture
def orchestrator():
    pm = MagicMock(spec=ProcessManager)
    hc = MagicMock(spec=HealthChecker)
    config = MagicMock(spec=LauncherConfig)
    config.backend_url = "http://127.0.0.1:8456"
    config.health_url = "http://127.0.0.1:8456/api/v1/system/health"
    config.frontend_url = "http://localhost:5173"
    config.get.return_value = {}
    status_calls = []
    orch = StartupOrchestrator(pm, hc, config, status_calls.append)
    orch._status = status_calls.append
    return orch, pm, hc, config


@pytest.mark.asyncio
async def test_wait_for_url_timeout():
    ok, data = await wait_for_url("http://127.0.0.1:1", timeout=0.5, interval=0.1)
    assert ok is False
    assert data is None


@pytest.mark.asyncio
async def test_startup_backend_fails(orchestrator):
    orch, pm, hc, config = orchestrator
    pm.start_backend = AsyncMock()
    pm.start_backend.return_value = MagicMock(pid=999)
    with patch("launcher.startup.wait_for_url", AsyncMock(return_value=(False, None))):
        result = await orch.run()
        assert result is False
