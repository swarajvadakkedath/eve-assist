"""Tests for health checker."""

from unittest.mock import patch

import pytest

from launcher.health_checker import HealthChecker, ServiceHealth, ProviderStatus


@pytest.fixture
def health_checker():
    return HealthChecker(
        backend_url="http://127.0.0.1:8456",
        health_url="http://127.0.0.1:8456/api/v1/system/health",
        interval=1.0,
    )


def test_init_services(health_checker):
    assert "backend" in health_checker.services
    assert "frontend" in health_checker.services
    assert "memory" in health_checker.services
    assert "planner" in health_checker.services
    assert "voice" in health_checker.services
    assert "vision" in health_checker.services


def test_init_providers(health_checker):
    assert "gemini" in health_checker.providers
    assert "groq" in health_checker.providers
    assert "openrouter" in health_checker.providers
    assert "ollama" in health_checker.providers


def test_service_health_defaults():
    sh = ServiceHealth(name="test")
    assert sh.status == "unknown"
    assert sh.restart_count == 0
    assert sh.details == {}


def test_provider_status_defaults():
    ps = ProviderStatus(name="test")
    assert ps.connected is False
    assert ps.error == ""


@pytest.mark.asyncio
async def test_check_backend_down(health_checker):
    with patch("httpx.AsyncClient.get", side_effect=Exception("connection refused")):
        await health_checker._check_backend()
        assert health_checker.services["backend"].status == "down"


@pytest.mark.asyncio
async def test_ai_provider_missing_key(health_checker):
    ps = await health_checker._check_ai_provider("gemini", key="", url="")
    assert ps.connected is False
    assert "Missing API Key" in ps.error


@pytest.mark.asyncio
async def test_ai_provider_ollama_offline(health_checker):
    ps = await health_checker._check_ai_provider("ollama", url="http://127.0.0.1:99999")
    assert ps.connected is False
    assert ps.error == "Offline" or "ConnectError" in ps.error or "connection" in ps.error.lower()


@pytest.mark.asyncio
async def test_monitor_lifecycle(health_checker):
    health_checker.start_monitoring()
    assert health_checker._running is True
    assert health_checker._task is not None
    await health_checker.stop_monitoring()
    assert health_checker._running is False


def test_needs_restart(health_checker):
    health_checker.services["backend"].status = "down"
    assert health_checker.needs_restart("backend") is True
    health_checker.services["backend"].status = "healthy"
    assert health_checker.needs_restart("backend") is False


def test_get_backend_modules(health_checker):
    health_checker.services["backend"].details = {"event_bus": "healthy"}
    assert health_checker.get_backend_modules() == {"event_bus": "healthy"}
