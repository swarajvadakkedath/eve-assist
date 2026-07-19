"""UI element detection — identifies buttons, inputs, icons, and layout regions."""

from io import BytesIO

from PIL import Image

from aios.vision.models import UIElement, LayoutRegion, DetectionResult


async def detect_ui_elements(image: Image.Image) -> list[UIElement]:
    elements = []
    try:
        import pyautogui
        import pytesseract
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        for i in range(len(data["text"])):
            if not data["text"][i].strip():
                continue
            conf = int(data["conf"][i]) if data["conf"][i] != "-1" else 0
            if conf < 30:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            element_type = _infer_element_type(data["text"][i], x, y, w, h)
            elements.append(UIElement(
                type=element_type,
                text=data["text"][i],
                x=x, y=y, width=w, height=h,
                confidence=conf / 100.0,
            ))
    except Exception:
        pass
    return elements


async def detect_ui_elements_from_bytes(image_data: bytes) -> list[UIElement]:
    img = Image.open(BytesIO(image_data))
    return await detect_ui_elements(img)


async def detect_layout(image: Image.Image) -> list[LayoutRegion]:
    regions = []
    try:
        import pytesseract
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        current_block = None
        for i in range(len(data["text"])):
            block_num = data["block_num"][i]
            if block_num != current_block:
                current_block = block_num
                if data["text"][i].strip():
                    regions.append(LayoutRegion(
                        region_type="text_block",
                        x=data["left"][i],
                        y=data["top"][i],
                        width=data["width"][i],
                        height=data["height"][i],
                        label=data["text"][i][:50],
                    ))
    except Exception:
        pass
    return regions


async def detect_icons(image: Image.Image) -> list[UIElement]:
    return []


async def detect_objects(image: Image.Image) -> list[UIElement]:
    return []


async def analyze_layout(image: Image.Image) -> DetectionResult:
    elements, layout, icons, objects = await _run_detections(image)
    text_regions = [r for r in layout if r.region_type == "text_block"]
    return DetectionResult(
        elements=elements,
        layout=layout,
        icons=icons,
        objects=objects,
        text_regions=text_regions,
    )


async def analyze_layout_from_bytes(image_data: bytes) -> DetectionResult:
    img = Image.open(BytesIO(image_data))
    return await analyze_layout(img)


async def _run_detections(image: Image.Image) -> tuple:
    import asyncio
    elements_task = asyncio.create_task(detect_ui_elements(image))
    layout_task = asyncio.create_task(detect_layout(image))
    icons_task = asyncio.create_task(detect_icons(image))
    objects_task = asyncio.create_task(detect_objects(image))
    results = await asyncio.gather(elements_task, layout_task, icons_task, objects_task, return_exceptions=True)
    elements = results[0] if not isinstance(results[0], Exception) else []
    layout = results[1] if not isinstance(results[1], Exception) else []
    icons = results[2] if not isinstance(results[2], Exception) else []
    objects = results[3] if not isinstance(results[3], Exception) else []
    return elements, layout, icons, objects


def _infer_element_type(text: str, x: int, y: int, w: int, h: int) -> str:
    upper = text.upper()
    keywords = {
        "button|click|submit|cancel|ok|save|delete|add|create|edit|remove|search|send|upload|download": "button",
        "input|textfield|search box|enter|type": "input",
        "checkbox|check box|toggle|switch": "checkbox",
        "radio|option": "radio",
        "dropdown|select|choose": "dropdown",
        "link|hyperlink|click here|more info": "link",
        "icon|symbol|→|←|↑|↓": "icon",
        "heading|title|header": "heading",
        "label|note|info|status": "label",
        "menu|nav|navigation|tab|section": "navigation",
    }
    for pattern, etype in keywords.items():
        import re
        if re.search(pattern, upper):
            return etype
    if h > 40 and w > 200:
        return "heading"
    if h < 20:
        return "label"
    return "text"
