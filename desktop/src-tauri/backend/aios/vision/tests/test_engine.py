"""Unit tests for VisionEngine (using mock substitutes for capture/OCR)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from aios.vision.engine import VisionEngine
from aios.vision.models import VisionConfig, VisionProvider, OCREngine, CaptureTarget, OCRResult, DetectionResult
from aios.vision.screenshot import ScreenshotResult


@pytest.fixture
def engine():
    return VisionEngine()


@pytest.mark.asyncio
async def test_engine_initialization(engine):
    assert engine.config.provider == VisionProvider.BUILTIN
    assert engine.config.ocr_engine == OCREngine.TESSERACT


@pytest.mark.asyncio
async def test_get_providers(engine):
    providers = await engine.get_providers()
    assert len(providers) >= 1
    assert any(p["id"] == "builtin" for p in providers)


@pytest.mark.asyncio
async def test_get_monitors(engine):
    monitors = await engine.get_monitors()
    assert len(monitors) >= 1


@pytest.mark.asyncio
async def test_ocr_screenshot_returns_ocr_result(engine):
    with (
        patch("aios.vision.engine.extract_text_with_details", new=AsyncMock()) as mock_ocr,
        patch("aios.vision.screenshot.capture_screen", new=AsyncMock()) as mock_cap,
    ):
        mock_ocr.return_value = OCRResult(text="Hello World", confidence=0.95)
        mock_cap.return_value = None
        result = await engine.ocr_screenshot()
        assert result.text == "Hello World"
        assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_ocr_image_from_bytes(engine):
    with patch("aios.vision.engine.extract_text_from_bytes", new=AsyncMock()) as mock_ocr:
        mock_ocr.return_value = OCRResult(text="Extracted text", confidence=0.8)
        result = await engine.ocr_image_from_bytes(b"fake_image_data")
        assert result.text == "Extracted text"


@pytest.mark.asyncio
async def test_full_observation(engine):
    with (
        patch("aios.vision.engine.capture_target", new=AsyncMock()) as mock_cap,
        patch("aios.vision.engine.extract_text_with_details", new=AsyncMock()) as mock_ocr,
        patch("aios.vision.engine.analyze_layout", new=AsyncMock()) as mock_layout,
    ):
        mock_cap.return_value = ScreenshotResult(id="ss-1", image_data=b"captured", width=1920, height=1080, format="png")
        mock_ocr.return_value = OCRResult(text="Screen text", confidence=0.9)
        mock_layout.return_value = DetectionResult(elements=[], layout=[], icons=[], objects=[], text_regions=[])

        obs = await engine.full_observation()
        assert obs.screenshot is not None
        assert obs.ocr is not None
        assert obs.detection is not None
        assert "UI elements" in obs.summary


@pytest.mark.asyncio
async def test_inspect_active_window(engine):
    with (
        patch("aios.vision.engine.capture_target", new=AsyncMock()) as mock_cap,
        patch("aios.vision.engine.extract_text_from_bytes", new=AsyncMock()) as mock_ocr,
        patch("aios.vision.engine.analyze_layout_from_bytes", new=AsyncMock()) as mock_layout,
    ):
        mock_cap.return_value = ScreenshotResult(id="ss-win", image_data=b"window_capture", width=800, height=600, format="png")
        mock_ocr.return_value = OCRResult(text="Window text", confidence=0.85)
        mock_layout.return_value = DetectionResult(elements=[])

        result = await engine.inspect_active_window()
        assert "screenshot" in result
        assert "ocr" in result
        assert "elements" in result


@pytest.mark.asyncio
async def test_capture_methods_exist(engine):
    with (
        patch("aios.vision.engine.capture_target", new=AsyncMock()) as mock_cap,
    ):
        mock_cap.return_value = ScreenshotResult(id="ss-cap", image_data=b"data", width=1920, height=1080, format="png")
        screen = await engine.capture_screen()
        assert screen.image_data == b"data"
