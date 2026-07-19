"""Screenshot capture using PyAutoGUI."""

from io import BytesIO

from PIL import Image


async def capture_screen(region: tuple[int, int, int, int] | None = None) -> Image.Image:
    import pyautogui
    if region:
        screenshot = pyautogui.screenshot(region=region)
    else:
        screenshot = pyautogui.screenshot()
    return screenshot


async def capture_screen_bytes(region: tuple[int, int, int, int] | None = None) -> bytes:
    img = await capture_screen(region)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
