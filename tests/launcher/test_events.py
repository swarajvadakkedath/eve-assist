"""Tests for launcher lifecycle events."""

from launcher.launcher_events import (
    LauncherEvent,
    LAUNCHER_STARTING,
    LAUNCHER_READY,
    LAUNCHER_ERROR,
    BACKEND_STARTED,
    BACKEND_STOPPED,
    BACKEND_FAILED,
    FRONTEND_STARTED,
    FRONTEND_STOPPED,
    PROVIDER_CONNECTED,
    PROVIDER_DISCONNECTED,
    SHUTDOWN_REQUESTED,
    SHUTDOWN_COMPLETED,
)


def test_event_constants_are_strings():
    assert isinstance(LAUNCHER_STARTING, str)
    assert isinstance(LAUNCHER_READY, str)
    assert isinstance(LAUNCHER_ERROR, str)
    assert isinstance(BACKEND_STARTED, str)
    assert isinstance(BACKEND_STOPPED, str)
    assert isinstance(BACKEND_FAILED, str)
    assert isinstance(FRONTEND_STARTED, str)
    assert isinstance(FRONTEND_STOPPED, str)
    assert isinstance(PROVIDER_CONNECTED, str)
    assert isinstance(PROVIDER_DISCONNECTED, str)
    assert isinstance(SHUTDOWN_REQUESTED, str)
    assert isinstance(SHUTDOWN_COMPLETED, str)


def test_event_creation():
    event = LauncherEvent(type=BACKEND_STARTED, data={"pid": 1234})
    assert event.type == BACKEND_STARTED
    assert event.data["pid"] == 1234


def test_event_auto_fields():
    event = LauncherEvent(type=LAUNCHER_STARTING)
    assert event.id != ""
    assert event.timestamp != ""


def test_event_custom_id():
    event = LauncherEvent(type=LAUNCHER_READY, id="custom-id")
    assert event.id == "custom-id"


def test_event_custom_timestamp():
    event = LauncherEvent(type=LAUNCHER_ERROR, timestamp="2024-01-01T00:00:00")
    assert event.timestamp == "2024-01-01T00:00:00"


def test_event_default_data():
    event = LauncherEvent(type=SHUTDOWN_REQUESTED)
    assert event.data == {}


def test_event_backend_started():
    event = LauncherEvent(type=BACKEND_STARTED, data={"pid": 999, "restart": False})
    assert event.data["pid"] == 999
    assert event.data["restart"] is False


def test_event_provider_connected():
    event = LauncherEvent(type=PROVIDER_CONNECTED, data={"provider": "ollama"})
    assert event.data["provider"] == "ollama"


def test_event_provider_disconnected():
    event = LauncherEvent(type=PROVIDER_DISCONNECTED, data={"provider": "gemini", "error": "timeout"})
    assert event.data["error"] == "timeout"


def test_event_shutdown():
    event = LauncherEvent(type=SHUTDOWN_COMPLETED)
    assert event.type == "shutdown:completed"
