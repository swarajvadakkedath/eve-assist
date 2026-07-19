"""Integration tests for the Vision Pipeline — end-to-end flow with mock engine."""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aios.vision.models import (
    VisionConfig, VisionProvider, OCREngine, ObservationMode,
    VisionObservation, ScreenshotResult, OCRResult, DetectionResult, UIElement,
)
from aios.vision.engine import VisionEngine
from aios.vision.session import VisionSession
from aios.vision.pipeline import VisionPipeline
from aios.vision.events import VisionEventPublisher
from aios.conversation.manager import ConversationManager
from aios.core.event_bus import EventBus


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def integration_pipeline(event_bus):
    vision_config = VisionConfig(provider=VisionProvider.MOCK, ocr_engine=OCREngine.MOCK)

    engine = MagicMock(spec=VisionEngine)
    engine.config = vision_config
    engine.capture_screen = AsyncMock(return_value=ScreenshotResult(
        id="ss-int-1", image_data=b"screen", width=1920, height=1080,
    ))
    engine.capture_window = AsyncMock(return_value=ScreenshotResult(
        id="ss-int-2", image_data=b"window", width=800, height=600,
    ))
    engine.ocr_screenshot = AsyncMock(return_value=OCRResult(text="Integration OCR", confidence=0.95))
    engine.ocr_image_from_bytes = AsyncMock(return_value=OCRResult(text="Image OCR", confidence=0.9))
    engine.analyze_screen = AsyncMock(return_value=DetectionResult(elements=[]))
    engine.analyze_image = AsyncMock(return_value=DetectionResult(elements=[]))
    engine.full_observation = AsyncMock(return_value=VisionObservation(
        id="obs-int-1",
        session_id="session-int-1",
        screenshot=ScreenshotResult(id="ss-int-1", image_data=b"screen", width=1920, height=1080),
        ocr=OCRResult(text="Integration OCR", confidence=0.95),
        detection=DetectionResult(elements=[UIElement(type="button", text="OK", x=10, y=10, width=80, height=30)]),
        summary="Integration test screen",
    ))
    engine.inspect_active_window = AsyncMock(return_value={
        "window_title": "Test App",
        "application": "test.exe",
        "screenshot": ScreenshotResult(id="ss-window", image_data=b"win", width=800, height=600),
        "ocr": OCRResult(text="Window text"),
        "elements": [UIElement(type="input", text="search", x=0, y=0, width=200, height=30)],
    })
    engine.get_providers = AsyncMock(return_value=[
        {"id": "builtin", "name": "Built-in"},
        {"id": "mock", "name": "Mock"},
    ])
    engine.get_monitors = AsyncMock(return_value=[
        {"id": 0, "name": "Monitor 1", "width": 1920, "height": 1080, "is_primary": True},
    ])

    conv_manager = MagicMock(spec=ConversationManager)
    conv_manager.add_system_message = AsyncMock()

    session = VisionSession(engine=engine, config=vision_config)
    await session.start("session-int-1")

    events = VisionEventPublisher(event_bus)
    pipeline = VisionPipeline(
        vision_session=session,
        conversation_manager=conv_manager,
        event_publisher=events,
        config=vision_config,
    )

    yield pipeline, session, engine, events, conv_manager

    await session.stop()


@pytest.mark.asyncio
async def test_vision_observe_screen(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline
    obs = await pipeline.observe_screen("session-int-1")
    assert obs is not None
    assert obs.session_id == "session-int-1"
    assert obs.screenshot is not None
    assert obs.ocr is not None
    assert obs.detection is not None


@pytest.mark.asyncio
async def test_vision_observe_image(integration_pipeline):
    pipeline, session, engine, events, obs_manager = integration_pipeline
    obs = await pipeline.observe_image("session-int-1", b"fake_image_bytes")
    assert obs is not None
    assert obs.session_id == "session-int-1"


@pytest.mark.asyncio
async def test_vision_session_lifecycle(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline
    state = await session.get_state()
    assert state.is_observing
    assert state.session_id == "session-int-1"

    await session.stop()
    state = await session.get_state()
    assert not state.is_observing


@pytest.mark.asyncio
async def test_vision_analyze_current_screen(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline
    obs = await session.analyze_current_screen()
    assert obs is not None
    assert session.state.observation_count >= 1


@pytest.mark.asyncio
async def test_vision_analyze_uploaded_image(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline
    obs = await session.analyze_uploaded_image(b"uploaded_image")
    assert obs is not None


@pytest.mark.asyncio
async def test_vision_inspect_active_window(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline
    result = await engine.inspect_active_window()
    assert result["window_title"] == "Test App"
    assert len(result["elements"]) == 1
    assert result["elements"][0].type == "input"


@pytest.mark.asyncio
async def test_vision_events_published(event_bus, integration_pipeline):
    pipeline, session, engine, events, obs_manager = integration_pipeline

    received = []

    async def collector(event):
        received.append(event.type)

    await event_bus.subscribe("vision:capture:start", collector)
    await event_bus.subscribe("vision:capture:complete", collector)
    await event_bus.subscribe("vision:analysis:start", collector)
    await event_bus.subscribe("vision:analysis:complete", collector)
    await event_bus.subscribe("vision:observation", collector)

    await pipeline.observe_screen("session-int-1")

    await asyncio.sleep(0.3)

    assert "vision:capture:start" in received
    assert "vision:capture:complete" in received
    assert "vision:analysis:start" in received
    assert "vision:analysis:complete" in received
    assert "vision:observation" in received


@pytest.mark.asyncio
async def test_vision_observation_fed_to_conversation(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline

    await pipeline.observe_screen("session-int-1")

    conv_manager.add_system_message.assert_called_once()
    call_args = conv_manager.add_system_message.call_args
    metadata = call_args.kwargs.get("metadata", {})
    assert "vision_observation" in metadata
    assert metadata["vision_observation"]["summary"] == "Integration test screen"


@pytest.mark.asyncio
async def test_vision_config_update(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline
    config = VisionConfig(capture_quality=50)
    await session.update_config(config)
    assert session.config.capture_quality == 50


@pytest.mark.asyncio
async def test_vision_get_providers(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline
    providers = await engine.get_providers()
    assert len(providers) >= 1


@pytest.mark.asyncio
async def test_vision_get_monitors(integration_pipeline):
    pipeline, session, engine, events, conv_manager = integration_pipeline
    monitors = await engine.get_monitors()
    assert len(monitors) >= 1


@pytest.mark.asyncio
async def test_vision_event_bus_integration(event_bus):
    events = VisionEventPublisher(event_bus)
    received = []

    async def collector(event):
        received.append(event.type)

    await event_bus.subscribe("vision:capture:start", collector)
    await event_bus.subscribe("vision:capture:complete", collector)
    await event_bus.subscribe("vision:analysis:start", collector)
    await event_bus.subscribe("vision:analysis:complete", collector)
    await event_bus.subscribe("vision:observation", collector)
    await event_bus.subscribe("vision:error", collector)

    await events.publish_capture_start("screen")
    await events.publish_capture_complete("screen", 2048)
    await events.publish_analysis_start("screen")
    await events.publish_analysis_complete("screen", 10, 150.5)
    await events.publish_observation({"id": "o1"})
    await events.publish_error("test error")

    await asyncio.sleep(0.3)

    assert "vision:capture:start" in received
    assert "vision:capture:complete" in received
    assert "vision:analysis:start" in received
    assert "vision:analysis:complete" in received
    assert "vision:observation" in received
    assert "vision:error" in received
