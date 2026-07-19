"""Vision tools for the tool manager — 9 tools for capture, analysis, and inspection."""

import base64
import json
from io import BytesIO

from PIL import Image

from aios.core.tool_manager import ToolManager
from aios.core.permission_manager import PermissionLevel
from aios.vision.engine import VisionEngine
from aios.vision.session import VisionSession
from aios.vision.models import VisionConfig


def register_vision_tools(tool_manager: ToolManager, vision_engine: VisionEngine, vision_session: VisionSession):
    """Register all vision tools with the ToolManager."""

    @tool_manager.tool(
        name="vision_capture_screen",
        description="Capture the full screen and return image metadata and base64-encoded data. Use to get a visual of what's on the user's screen.",
        parameters={
            "type": "object",
            "properties": {},
        },
    )
    async def capture_screen(params: dict) -> str:
        result = await vision_engine.capture_screen()
        b64 = base64.b64encode(result.image_data).decode("utf-8")
        return json.dumps({
            "width": result.width,
            "height": result.height,
            "format": result.format,
            "size_bytes": len(result.image_data),
            "image_base64": b64,
        })

    @tool_manager.tool(
        name="vision_capture_window",
        description="Capture the active window. Returns screenshot of the currently focused application window.",
        parameters={
            "type": "object",
            "properties": {},
        },
    )
    async def capture_window(params: dict) -> str:
        result = await vision_engine.capture_window()
        b64 = base64.b64encode(result.image_data).decode("utf-8")
        return json.dumps({
            "width": result.width,
            "height": result.height,
            "size_bytes": len(result.image_data),
            "image_base64": b64,
        })

    @tool_manager.tool(
        name="vision_capture_region",
        description="Capture a specific region of the screen by coordinates. e.g. {'x':100,'y':100,'width':500,'height':400}",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate of the region"},
                "y": {"type": "integer", "description": "Y coordinate of the region"},
                "width": {"type": "integer", "description": "Width of the region"},
                "height": {"type": "integer", "description": "Height of the region"},
            },
            "required": ["x", "y", "width", "height"],
        },
    )
    async def capture_region(params: dict) -> str:
        region = (params["x"], params["y"], params["width"], params["height"])
        result = await vision_engine.capture_region(region)
        b64 = base64.b64encode(result.image_data).decode("utf-8")
        return json.dumps({
            "width": result.width,
            "height": result.height,
            "region": list(region),
            "size_bytes": len(result.image_data),
            "image_base64": b64,
        })

    @tool_manager.tool(
        name="vision_capture_monitor",
        description="Capture a specific monitor by ID (0 = primary). Use vision_list_monitors first to see available monitors.",
        parameters={
            "type": "object",
            "properties": {
                "monitor_id": {"type": "integer", "description": "Monitor ID (0 = primary)"},
            },
            "required": [],
        },
    )
    async def capture_monitor(params: dict) -> str:
        monitor_id = params.get("monitor_id", 0)
        result = await vision_engine.capture_monitor(monitor_id)
        b64 = base64.b64encode(result.image_data).decode("utf-8")
        return json.dumps({
            "monitor_id": monitor_id,
            "width": result.width,
            "height": result.height,
            "size_bytes": len(result.image_data),
            "image_base64": b64,
        })

    @tool_manager.tool(
        name="vision_analyze_image",
        description="Analyze an image (base64) for UI elements, text, and layout. Provide the base64-encoded image data.",
        parameters={
            "type": "object",
            "properties": {
                "image": {"type": "string", "description": "Base64-encoded image data"},
            },
            "required": ["image"],
        },
    )
    async def analyze_image(params: dict) -> str:
        image_data = base64.b64decode(params["image"])
        observation = await vision_session.analyze_uploaded_image(image_data)
        return json.dumps(observation.to_structured(), default=str)

    @tool_manager.tool(
        name="vision_extract_text",
        description="Extract text from the screen using OCR. Returns all visible text with confidence scores.",
        parameters={
            "type": "object",
            "properties": {
                "lang": {"type": "string", "description": "Language code (default: eng)"},
            },
            "required": [],
        },
    )
    async def extract_text(params: dict) -> str:
        lang = params.get("lang", "eng")
        result = await vision_engine.ocr_screenshot(lang)
        return json.dumps({
            "text": result.text,
            "confidence": result.confidence,
            "language": result.language,
            "blocks": result.blocks,
        })

    @tool_manager.tool(
        name="vision_detect_ui_elements",
        description="Detect all UI elements on the screen — buttons, inputs, labels, headings, links, etc.",
        parameters={
            "type": "object",
            "properties": {},
        },
    )
    async def detect_ui_elements(params: dict) -> str:
        detection = await vision_engine.analyze_screen()
        elements = [
            {"type": e.type, "text": e.text, "x": e.x, "y": e.y, "width": e.width, "height": e.height, "confidence": e.confidence}
            for e in detection.elements
        ]
        return json.dumps({"elements": elements, "count": len(elements)})

    @tool_manager.tool(
        name="vision_detect_objects",
        description="Detect objects in the screen capture (limited — uses OCR-based detection).",
        parameters={
            "type": "object",
            "properties": {},
        },
    )
    async def detect_objects(params: dict) -> str:
        detection = await vision_engine.analyze_screen()
        objects = [
            {"type": o.type, "text": o.text, "x": o.x, "y": o.y, "width": o.width, "height": o.height}
            for o in (detection.objects or [])
        ]
        return json.dumps({"objects": objects, "count": len(objects)})

    @tool_manager.tool(
        name="vision_inspect_active_window",
        description="Inspect the currently active window — capture, OCR, and detect UI elements in one call.",
        parameters={
            "type": "object",
            "properties": {},
        },
    )
    async def inspect_active_window(params: dict) -> str:
        result = await vision_engine.inspect_active_window()
        b64 = base64.b64encode(result["screenshot"].image_data).decode("utf-8")
        elements = [
            {"type": e.type, "text": e.text, "x": e.x, "y": e.y}
            for e in result["elements"]
        ]
        return json.dumps({
            "window_title": result["window_title"],
            "application": result["application"],
            "ocr_text": result["ocr"].text if result["ocr"] else "",
            "elements": elements,
            "image_base64": b64,
            "width": result["screenshot"].width,
            "height": result["screenshot"].height,
        })
