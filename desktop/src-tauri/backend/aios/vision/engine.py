"""VisionEngine — orchestrates capture, OCR, UI analysis, and observation generation."""

import time
from io import BytesIO

from PIL import Image

from aios.vision.models import (
    VisionConfig, ScreenshotResult, OCRResult, DetectionResult,
    VisionObservation, CaptureTarget,
)
from aios.vision.screenshot import capture_target, get_monitors, capture_active_window
from aios.vision.ocr import extract_text_with_details, extract_text_from_bytes, redact_sensitive
from aios.vision.ui_understanding import analyze_layout, analyze_layout_from_bytes
from aios.error_intelligence import get_error_intelligence


class VisionEngine:
    """Core vision engine — capture, OCR, UI analysis, observation."""

    def __init__(self, config: VisionConfig | None = None):
        self.config = config or VisionConfig()

    async def capture_screen(self, region: tuple[int, int, int, int] | None = None) -> ScreenshotResult:
        return await capture_target(CaptureTarget.FULL_SCREEN)

    async def capture_window(self) -> ScreenshotResult:
        return await capture_target(CaptureTarget.ACTIVE_WINDOW)

    async def capture_region(self, region: tuple[int, int, int, int]) -> ScreenshotResult:
        return await capture_target(CaptureTarget.REGION, region=region)

    async def capture_monitor(self, monitor_id: int = 0) -> ScreenshotResult:
        return await capture_target(CaptureTarget.MONITOR, monitor_id=monitor_id)

    async def get_screenshot_bytes(self) -> bytes:
        from aios.vision.screenshot import capture_screen_bytes
        return await capture_screen_bytes()

    async def get_screenshot_pil(self) -> Image.Image:
        from aios.vision.screenshot import capture_screen
        return await capture_screen()

    async def ocr_screenshot(self, lang: str = "eng") -> OCRResult:
        img = await self.get_screenshot_pil()
        result = await extract_text_with_details(img, lang)
        if self.config.auto_redact_sensitive:
            result.text = await redact_sensitive(result.text)
        return result

    async def ocr_image_from_bytes(self, image_data: bytes, lang: str = "eng") -> OCRResult:
        result = await extract_text_from_bytes(image_data, lang)
        if self.config.auto_redact_sensitive:
            result.text = await redact_sensitive(result.text)
        return result

    async def analyze_screen(self) -> DetectionResult:
        try:
            img = await self.get_screenshot_pil()
            return await self._analyze_image(img)
        except Exception as e:
            try:
                svc = get_error_intelligence()
                svc.capture_exception(e, module="vision.engine", message=f"Screen analysis failed: {e}")
            except Exception:
                pass
            raise

    async def analyze_image(self, image_data: bytes) -> DetectionResult:
        return await analyze_layout_from_bytes(image_data)

    async def full_observation(self) -> VisionObservation:
        start = time.monotonic()
        try:
            screenshot = await capture_target(CaptureTarget.FULL_SCREEN)
            ocr = await self.ocr_screenshot()
            detection = await self.analyze_screen()
        except Exception as e:
            try:
                svc = get_error_intelligence()
                svc.capture_exception(e, module="vision.engine", message=f"Vision observation failed: {e}")
            except Exception:
                pass
            raise
        duration = (time.monotonic() - start) * 1000
        if detection:
            detection.duration_ms = duration

        summary = f"Screen contains {len(detection.elements) if detection else 0} UI elements"
        if ocr and ocr.text:
            summary += f", text: {ocr.text[:100]}"

        return VisionObservation(
            screenshot=screenshot,
            ocr=ocr,
            detection=detection,
            summary=summary,
            context={
                "provider": self.config.provider.value,
                "ocr_engine": self.config.ocr_engine.value,
                "duration_ms": duration,
            },
        )

    async def inspect_active_window(self) -> dict:
        screenshot = await self.capture_window()
        ocr = await self.ocr_image_from_bytes(screenshot.image_data)
        detection = await self.analyze_image(screenshot.image_data)
        return {
            "window_title": "",
            "application": "",
            "screenshot": screenshot,
            "ocr": ocr,
            "elements": detection.elements if detection else [],
        }

    async def get_providers(self) -> list[dict]:
        return [
            {"id": "builtin", "name": "Built-in", "capabilities": ["capture", "ocr", "ui_detection"]},
            {"id": "openai", "name": "OpenAI Vision", "capabilities": ["analysis", "description"]},
            {"id": "anthropic", "name": "Anthropic Claude", "capabilities": ["analysis", "description"]},
        ]

    async def get_monitors(self) -> list[dict]:
        monitors = await get_monitors()
        return [m.__dict__ for m in monitors]

    async def _analyze_image(self, img: Image.Image) -> DetectionResult:
        return await analyze_layout(img)
