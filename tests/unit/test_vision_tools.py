"""Unit tests for vision tool registration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aios.vision.tools import register_vision_tools
from aios.vision.engine import VisionEngine
from aios.vision.session import VisionSession


@pytest.fixture
def tool_manager():
    mgr = MagicMock()
    mgr.register_tool = MagicMock(return_value=lambda f: f)
    return mgr


@pytest.fixture
def engine():
    eng = MagicMock(spec=VisionEngine)
    eng.capture_screen = AsyncMock()
    eng.capture_screen.return_value.width = 1920
    eng.capture_screen.return_value.height = 1080
    eng.capture_screen.return_value.image_data = b"screen_data"
    eng.capture_screen.return_value.format = "png"
    eng.capture_window = AsyncMock()
    eng.capture_window.return_value.width = 800
    eng.capture_window.return_value.height = 600
    eng.capture_window.return_value.image_data = b"window_data"
    eng.capture_region = AsyncMock()
    eng.capture_region.return_value.width = 400
    eng.capture_region.return_value.height = 300
    eng.capture_region.return_value.image_data = b"region_data"
    eng.capture_monitor = AsyncMock()
    eng.capture_monitor.return_value.width = 1920
    eng.capture_monitor.return_value.height = 1080
    eng.capture_monitor.return_value.image_data = b"monitor_data"
    eng.ocr_screenshot = AsyncMock()
    eng.ocr_screenshot.return_value.text = "OCR text"
    eng.ocr_screenshot.return_value.confidence = 0.9
    eng.ocr_screenshot.return_value.blocks = []
    eng.analyze_screen = AsyncMock()
    eng.analyze_screen.return_value.elements = []
    eng.analyze_screen.return_value.objects = []
    eng.inspect_active_window = AsyncMock()
    eng.inspect_active_window.return_value = {
        "window_title": "Test Window",
        "application": "test.exe",
        "screenshot": MagicMock(image_data=b"window_data", width=800, height=600),
        "ocr": MagicMock(text="Window text"),
        "elements": [],
    }
    eng.get_providers = AsyncMock(return_value=[{"id": "builtin", "name": "Built-in"}])
    eng.get_monitors = AsyncMock(return_value=[{"id": 0, "name": "Monitor 1"}])
    return eng


@pytest.fixture
def session():
    sess = MagicMock(spec=VisionSession)
    sess.analyze_uploaded_image = AsyncMock()
    sess.analyze_uploaded_image.return_value.summary = "Analyzed image"
    sess.analyze_uploaded_image.return_value.to_structured = MagicMock(return_value={
        "observation_id": "obs-1",
        "summary": "Analyzed image",
        "screen_text": "",
        "ui_elements": [],
        "layout": [],
        "icons": [],
    })
    return sess


def test_register_vision_tools(tool_manager, engine, session):
    register_vision_tools(tool_manager, engine, session)
    names = [call.kwargs.get("name") for call in tool_manager.register_tool.call_args_list]
    expected_tools = [
        "vision_capture_screen",
        "vision_capture_window",
        "vision_capture_region",
        "vision_capture_monitor",
        "vision_analyze_image",
        "vision_extract_text",
        "vision_detect_ui_elements",
        "vision_detect_objects",
        "vision_inspect_active_window",
    ]
    for tool_name in expected_tools:
        assert tool_name in names, f"Missing tool: {tool_name}"
    assert len(names) >= 9


def test_register_vision_tools_descriptions(tool_manager, engine, session):
    register_vision_tools(tool_manager, engine, session)
    for call in tool_manager.register_tool.call_args_list:
        name = call.kwargs.get("name", "")
        desc = call.kwargs.get("description", "")
        assert desc, f"Tool {name} has no description"
        assert call.kwargs.get("parameters"), f"Tool {name} has no parameters"
