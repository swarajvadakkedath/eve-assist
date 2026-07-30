"""Tests for LauncherService orchestration engine."""


import pytest

from launcher.launcher_service import LauncherService
from launcher.launcher_api import LauncherStatus
from launcher.launcher_events import (
    LauncherEvent,
)


@pytest.fixture
def service():
    svc = LauncherService()
    return svc


@pytest.mark.asyncio
async def test_initialize(service):
    ok = await service.initialize()
    assert ok is True
    assert service.state == "initialized"


@pytest.mark.asyncio
async def test_initialize_sets_loop(service):
    ok = await service.initialize()
    assert ok is True
    assert service._loop is not None


@pytest.mark.asyncio
async def test_status_before_initialize(service):
    status = service.status()
    assert status.state == "stopped"
    assert status.version == "1.1.0"
    assert status.uptime == 0.0


@pytest.mark.asyncio
async def test_status_after_initialize(service):
    await service.initialize()
    status = service.status()
    assert status.state in ("initialized", "stopped")


@pytest.mark.asyncio
async def test_event_subscription(service):
    await service.initialize()
    events = []

    def handler(event):
        events.append(event.type)

    sub_id = service.on_event(handler)
    assert sub_id is not None
    service._emit(LauncherEvent(type="test:event"))
    assert "test:event" in events
    service.off_event(sub_id)
    service._emit(LauncherEvent(type="test:after"))
    assert "test:after" not in events


@pytest.mark.asyncio
async def test_start_fails_if_not_initialized(service):
    ok = await service.start()
    assert ok is False


@pytest.mark.asyncio
async def test_stop_when_stopped(service):
    await service.stop()


@pytest.mark.asyncio
async def test_initialize_creates_health_service(service):
    await service.initialize()
    assert service._health is not None
    assert service._providers is not None
    assert service._startup is not None
    assert service._shutdown is not None


@pytest.mark.asyncio
async def test_property_accessors(service):
    await service.initialize()
    assert service.config is not None
    assert service.backend is not None
    assert service.frontend is not None
    assert service.tray is not None


@pytest.mark.asyncio
async def test_running_property(service):
    assert service.running is False
    await service.initialize()
    assert service.running is False


def test_launcher_status_dataclass():
    status = LauncherStatus(state="running", version="1.1.0")
    assert status.state == "running"
    assert status.version == "1.1.0"
    assert status.uptime == 0.0


def test_launcher_event_defaults():
    event = LauncherEvent(type="test:event")
    assert event.type == "test:event"
    assert event.data == {}
    assert event.id != ""
    assert event.timestamp != ""


@pytest.mark.asyncio
async def test_health_check(service):
    await service.initialize()
    health = await service.health()
    assert isinstance(health, dict)
