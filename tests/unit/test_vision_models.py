"""Unit tests for vision data models."""

import pytest
from datetime import datetime

from aios.vision.models import (
    VisionConfig,
    VisionProvider,
    OCREngine,
    ObservationMode,
    CaptureTarget,
    ScreenshotResult,
    OCRResult,
    UIElement,
    LayoutRegion,
    DetectionResult,
    VisionObservation,
    VisionSessionState,
    MonitorInfo,
)


def test_vision_provider_enum():
    assert VisionProvider.BUILTIN.value == "builtin"
    assert VisionProvider.OPENAI.value == "openai"
    assert VisionProvider.ANTHROPIC.value == "anthropic"
    assert VisionProvider.MOCK.value == "mock"


def test_ocr_engine_enum():
    assert OCREngine.TESSERACT.value == "tesseract"
    assert OCREngine.EASYOCR.value == "easyocr"
    assert OCREngine.MOCK.value == "mock"


def test_observation_mode_enum():
    assert ObservationMode.MANUAL.value == "manual"
    assert ObservationMode.LIVE.value == "live"


def test_capture_target_enum():
    assert CaptureTarget.FULL_SCREEN.value == "full_screen"
    assert CaptureTarget.ACTIVE_WINDOW.value == "active_window"
    assert CaptureTarget.REGION.value == "region"
    assert CaptureTarget.MONITOR.value == "monitor"


def test_screenshot_result_defaults():
    s = ScreenshotResult()
    assert s.id
    assert s.image_data == b""
    assert s.width == 0
    assert s.height == 0
    assert s.format == "png"
    assert s.timestamp is not None
    assert s.error is None


def test_screenshot_result_custom():
    s = ScreenshotResult(
        id="ss-1",
        image_data=b"data",
        width=1920,
        height=1080,
        format="jpg",
        error=None,
    )
    assert s.id == "ss-1"
    assert s.image_data == b"data"
    assert s.width == 1920
    assert s.height == 1080


def test_ocr_result_defaults():
    o = OCRResult()
    assert o.text == ""
    assert o.confidence == 0.0
    assert o.language == "eng"
    assert o.error is None


def test_ocr_result_custom():
    o = OCRResult(text="hello", confidence=0.95, language="fra")
    assert o.text == "hello"
    assert o.confidence == 0.95
    assert o.language == "fra"


def test_ui_element_defaults():
    e = UIElement()
    assert e.type == ""
    assert e.text == ""
    assert e.x == 0
    assert e.y == 0
    assert e.width == 0
    assert e.height == 0
    assert e.confidence == 0.0


def test_ui_element_custom():
    e = UIElement(type="button", text="Submit", x=10, y=20, width=100, height=40, confidence=0.9)
    assert e.type == "button"
    assert e.text == "Submit"
    assert e.x == 10
    assert e.y == 20
    assert e.width == 100
    assert e.height == 40
    assert e.confidence == 0.9


def test_layout_region_defaults():
    r = LayoutRegion()
    assert r.region_type == ""
    assert r.x == 0
    assert r.y == 0
    assert r.label == ""


def test_detection_result_defaults():
    d = DetectionResult()
    assert d.elements == []
    assert d.layout == []
    assert d.icons == []
    assert d.objects == []
    assert d.error is None


def test_vision_observation_defaults():
    o = VisionObservation()
    assert o.id
    assert o.session_id == ""
    assert o.summary == ""
    assert o.screenshot is None
    assert o.ocr is None
    assert o.detection is None
    assert o.timestamp is not None


def test_vision_observation_to_dict():
    o = VisionObservation(
        session_id="s-1",
        summary="Test observation",
        context={"key": "value"},
    )
    d = o.to_dict()
    assert d["session_id"] == "s-1"
    assert d["summary"] == "Test observation"
    assert d["context"]["key"] == "value"
    assert d["ocr_text"] == ""
    assert d["element_count"] == 0


def test_vision_observation_to_structured():
    o = VisionObservation(session_id="s-1", summary="Structured test")
    s = o.to_structured()
    assert s["observation_id"] == o.id
    assert s["summary"] == "Structured test"
    assert s["screen_text"] == ""
    assert s["ui_elements"] == []
    assert s["layout"] == []
    assert s["icons"] == []


def test_vision_config_defaults():
    c = VisionConfig()
    assert c.provider == VisionProvider.BUILTIN
    assert c.ocr_engine == OCREngine.TESSERACT
    assert c.capture_quality == 75
    assert c.privacy_filters_enabled
    assert c.auto_redact_sensitive
    assert c.observation_mode == ObservationMode.MANUAL
    assert c.max_image_size == 1920


def test_vision_config_custom():
    c = VisionConfig(
        provider=VisionProvider.MOCK,
        ocr_engine=OCREngine.MOCK,
        capture_quality=50,
        privacy_filters_enabled=False,
        auto_redact_sensitive=False,
        observation_mode=ObservationMode.LIVE,
    )
    assert c.provider == VisionProvider.MOCK
    assert c.ocr_engine == OCREngine.MOCK
    assert c.capture_quality == 50
    assert not c.privacy_filters_enabled
    assert not c.auto_redact_sensitive
    assert c.observation_mode == ObservationMode.LIVE


def test_vision_session_state_defaults():
    s = VisionSessionState()
    assert s.session_id
    assert not s.is_observing
    assert s.observation_mode == ObservationMode.MANUAL
    assert s.last_observation is None
    assert s.observation_count == 0
    assert s.started_at is not None


def test_vision_session_state_custom():
    s = VisionSessionState(
        session_id="s-1",
        is_observing=True,
        observation_mode=ObservationMode.LIVE,
        observation_count=5,
    )
    assert s.session_id == "s-1"
    assert s.is_observing
    assert s.observation_mode == ObservationMode.LIVE
    assert s.observation_count == 5


def test_monitor_info_defaults():
    m = MonitorInfo()
    assert m.id == 0
    assert m.name == ""
    assert m.width == 0
    assert m.height == 0
    assert not m.is_primary


def test_monitor_info_custom():
    m = MonitorInfo(id=1, name="Monitor 2", width=1920, height=1080, is_primary=True)
    assert m.id == 1
    assert m.name == "Monitor 2"
    assert m.width == 1920
    assert m.height == 1080
    assert m.is_primary
