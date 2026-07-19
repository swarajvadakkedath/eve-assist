"""Unit tests for the Vision Session."""

import pytest
from unittest.mock import AsyncMock, patch

from aios.vision.session import VisionSession
from aios.vision.models import VisionConfig, ObservationMode


@pytest.fixture
async def session():
    with patch("aios.vision.session.VisionEngine") as MockEngine:
        engine = MockEngine.return_value
        engine.full_observation = AsyncMock()
        engine.full_observation.return_value.summary = "Test screen"
        engine.ocr_image_from_bytes = AsyncMock()
        engine.ocr_image_from_bytes.return_value.text = "OCR text"
        engine.analyze_image = AsyncMock()
        engine.analyze_image.return_value.elements = []
        engine.get_screenshot_bytes = AsyncMock(return_value=b"captured")

        sess = VisionSession()
        yield sess


@pytest.mark.asyncio
async def test_session_start(session):
    state = await session.start("session-1")
    assert state.session_id == "session-1"
    assert state.is_observing
    assert state.observation_mode == ObservationMode.MANUAL


@pytest.mark.asyncio
async def test_session_start_live(session):
    state = await session.start("session-2", ObservationMode.LIVE)
    assert state.observation_mode == ObservationMode.LIVE


@pytest.mark.asyncio
async def test_session_stop(session):
    await session.start("session-1")
    state = await session.stop()
    assert not state.is_observing


@pytest.mark.asyncio
async def test_analyze_current_screen(session):
    await session.start("session-1")
    obs = await session.analyze_current_screen()
    assert obs is not None
    assert obs.session_id == "session-1"
    assert session.state.observation_count == 1


@pytest.mark.asyncio
async def test_analyze_uploaded_image(session):
    await session.start("session-1")
    obs = await session.analyze_uploaded_image(b"fake_image_data")
    assert obs is not None
    assert session.state.observation_count == 1
    assert "uploaded" in obs.summary


@pytest.mark.asyncio
async def test_get_state(session):
    state = await session.get_state()
    assert state is not None
    assert not state.is_observing


@pytest.mark.asyncio
async def test_update_config(session):
    config = VisionConfig()
    config.capture_quality = 50
    updated = await session.update_config(config)
    assert updated.capture_quality == 50


@pytest.mark.asyncio
async def test_analyze_current_screen_increments_count(session):
    await session.start("session-1")
    assert session.state.observation_count == 0
    await session.analyze_current_screen()
    assert session.state.observation_count == 1
    await session.analyze_current_screen()
    assert session.state.observation_count == 2
