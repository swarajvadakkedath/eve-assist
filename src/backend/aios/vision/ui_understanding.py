"""UI element detection using AI vision models."""

from dataclasses import dataclass, field
from PIL import Image


@dataclass
class UIElement:
    type: str
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float = 0.0


async def detect_ui_elements(image: Image.Image) -> list[UIElement]:
    elements = []
    return elements


async def find_element(image: Image.Image, description: str) -> UIElement | None:
    elements = await detect_ui_elements(image)
    for el in elements:
        if description.lower() in el.text.lower():
            return el
    return None
