"""Screen capture — full screen, active window, region, multi-monitor support."""

from io import BytesIO

from PIL import Image

from aios.vision.models import ScreenshotResult, MonitorInfo, CaptureTarget


async def capture_screen(region: tuple[int, int, int, int] | None = None) -> Image.Image:
    import pyautogui
    screenshot = pyautogui.screenshot(region=region)
    return screenshot


async def capture_screen_bytes(region: tuple[int, int, int, int] | None = None) -> bytes:
    img = await capture_screen(region)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def capture_monitor(monitor_id: int = 0) -> Image.Image:
    monitors = await get_monitors()
    if monitor_id < 0 or monitor_id >= len(monitors):
        monitor_id = 0
    m = monitors[monitor_id]
    region = (m.x, m.y, m.width, m.height)
    return await capture_screen(region)


async def capture_active_window() -> tuple[Image.Image, str]:
    import pygetwindow as gw
    try:
        window = gw.getActiveWindow()
        if window and window.visible:
            region = (window.left, window.top, window.width, window.height)
            img = await capture_screen(region)
            return img, window.title
    except Exception:
        pass
    return await capture_screen(), ""


async def get_monitors() -> list[MonitorInfo]:
    monitors = []
    try:
        import screeninfo
        for i, m in enumerate(screeninfo.get_monitors()):
            monitors.append(MonitorInfo(
                id=i,
                name=m.name or f"Monitor {i + 1}",
                width=m.width,
                height=m.height,
                is_primary=m.is_primary,
                x=m.x,
                y=m.y,
            ))
    except ImportError:
        monitors.append(MonitorInfo(
            id=0, name="Primary Monitor",
            width=1920, height=1080, is_primary=True,
        ))
    except Exception:
        monitors.append(MonitorInfo(
            id=0, name="Primary Monitor",
            width=1920, height=1080, is_primary=True,
        ))
    return monitors


async def capture_target(target: CaptureTarget, **kwargs) -> ScreenshotResult:
    if target == CaptureTarget.ACTIVE_WINDOW:
        img, title = await capture_active_window()
    elif target == CaptureTarget.MONITOR:
        monitor_id = kwargs.get("monitor_id", 0)
        img = await capture_monitor(monitor_id)
    elif target == CaptureTarget.REGION:
        region = kwargs.get("region")
        img = await capture_screen(region)
    else:
        img = await capture_screen()

    buf = BytesIO()
    fmt = kwargs.get("format", "png").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    img.save(buf, format=fmt.upper())
    quality = kwargs.get("quality", 75)
    if fmt in ("jpeg", "webp"):
        buf = BytesIO()
        img.save(buf, format=fmt.upper(), quality=quality)

    return ScreenshotResult(
        image_data=buf.getvalue(),
        width=img.width,
        height=img.height,
        format=fmt,
    )


async def resize_image(image_data: bytes, max_size: int = 1920) -> bytes:
    img = Image.open(BytesIO(image_data))
    if max(img.width, img.height) <= max_size:
        return image_data
    ratio = max_size / max(img.width, img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img = img.resize(new_size, Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def is_supported_format(file_path: str) -> bool:
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    return ext in ("png", "jpg", "jpeg", "bmp", "webp", "gif", "tiff")
