"""Unit tests for the Vision Event Publisher."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from aios.vision.events import VisionEventPublisher
from aios.vision.events import (
    VISION_EVENT_CAPTURE_START,
    VISION_EVENT_CAPTURE_COMPLETE,
    VISION_EVENT_ANALYSIS_START,
    VISION_EVENT_ANALYSIS_COMPLETE,
    VISION_EVENT_OBSERVATION,
    VISION_EVENT_ERROR,
    VISION_EVENT_SESSION_START,
    VISION_EVENT_SESSION_STOP,
)


@pytest.fixture
def event_bus():
    bus = MagicMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def publisher(event_bus):
    return VisionEventPublisher(event_bus)


@pytest.mark.asyncio
async def test_publish_capture_start(publisher, event_bus):
    await publisher.publish_capture_start("screen")
    event_bus.publish.assert_called_once_with(
        VISION_EVENT_CAPTURE_START, {"target": "screen"}
    )


@pytest.mark.asyncio
async def test_publish_capture_complete(publisher, event_bus):
    await publisher.publish_capture_complete("window", 1024)
    event_bus.publish.assert_called_once_with(
        VISION_EVENT_CAPTURE_COMPLETE, {"target": "window", "size_bytes": 1024}
    )


@pytest.mark.asyncio
async def test_publish_analysis_start(publisher, event_bus):
    await publisher.publish_analysis_start("screen")
    event_bus.publish.assert_called_once_with(
        VISION_EVENT_ANALYSIS_START, {"source": "screen"}
    )


@pytest.mark.asyncio
async def test_publish_analysis_complete(publisher, event_bus):
    await publisher.publish_analysis_complete("screen", 5, 123.4)
    event_bus.publish.assert_called_once_with(
        VISION_EVENT_ANALYSIS_COMPLETE,
        {"source": "screen", "element_count": 5, "duration_ms": 123.4},
    )


@pytest.mark.asyncio
async def test_publish_observation(publisher, event_bus):
    await publisher.publish_observation({"id": "obs-1", "summary": "Test"})
    event_bus.publish.assert_called_once_with(
        VISION_EVENT_OBSERVATION, {"id": "obs-1", "summary": "Test"},
    )


@pytest.mark.asyncio
async def test_publish_error(publisher, event_bus):
    await publisher.publish_error("test error", {"detail": "info"})
    event_bus.publish.assert_called_once_with(
        VISION_EVENT_ERROR, {"error": "test error", "details": {"detail": "info"}},
    )


@pytest.mark.asyncio
async def test_publish_session_start(publisher, event_bus):
    await publisher.publish_session_start("session-1")
    event_bus.publish.assert_called_once_with(
        VISION_EVENT_SESSION_START, {"session_id": "session-1"},
    )


@pytest.mark.asyncio
async def test_publish_session_stop(publisher, event_bus):
    await publisher.publish_session_stop("session-1")
    event_bus.publish.assert_called_once_with(
        VISION_EVENT_SESSION_STOP, {"session_id": "session-1"},
    )


@pytest.mark.asyncio
async def test_publisher_without_event_bus():
    publisher = VisionEventPublisher()
    await publisher.publish_capture_start()
    assert True


@pytest.mark.asyncio
async def test_all_event_names_defined():
    assert VISION_EVENT_CAPTURE_START == "vision:capture:start"
    assert VISION_EVENT_CAPTURE_COMPLETE == "vision:capture:complete"
    assert VISION_EVENT_ANALYSIS_START == "vision:analysis:start"
    assert VISION_EVENT_ANALYSIS_COMPLETE == "vision:analysis:complete"
    assert VISION_EVENT_OBSERVATION == "vision:observation"
    assert VISION_EVENT_ERROR == "vision:error"
    assert VISION_EVENT_SESSION_START == "vision:session:start"
    assert VISION_EVENT_SESSION_STOP == "vision:session:stop"
