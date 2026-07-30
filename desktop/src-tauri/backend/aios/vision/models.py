"""Data models for the vision interface."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class VisionProvider(str, Enum):
    BUILTIN = "builtin"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class OCREngine(str, Enum):
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    MOCK = "mock"


class ObservationMode(str, Enum):
    MANUAL = "manual"
    LIVE = "live"


class CaptureTarget(str, Enum):
    FULL_SCREEN = "full_screen"
    ACTIVE_WINDOW = "active_window"
    REGION = "region"
    MONITOR = "monitor"


@dataclass
class ScreenshotResult:
    id: str = ""
    image_data: bytes = b""
    width: int = 0
    height: int = 0
    format: str = "png"
    monitor: int = 0
    region: tuple[int, int, int, int] | None = None
    timestamp: datetime | None = None
    error: str | None = None

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class OCRResult:
    text: str = ""
    confidence: float = 0.0
    language: str = "eng"
    blocks: list[dict] = field(default_factory=list)
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class UIElement:
    type: str = ""
    text: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    attributes: dict = field(default_factory=dict)


@dataclass
class LayoutRegion:
    region_type: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    label: str = ""
    children: list[dict] = field(default_factory=list)


@dataclass
class DetectionResult:
    elements: list[UIElement] = field(default_factory=list)
    layout: list[LayoutRegion] = field(default_factory=list)
    icons: list[UIElement] = field(default_factory=list)
    objects: list[UIElement] = field(default_factory=list)
    text_regions: list[LayoutRegion] = field(default_factory=list)
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class VisionObservation:
    id: str = ""
    session_id: str = ""
    screenshot: ScreenshotResult | None = None
    ocr: OCRResult | None = None
    detection: DetectionResult | None = None
    summary: str = ""
    context: dict = field(default_factory=dict)
    timestamp: datetime | None = None

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "summary": self.summary,
            "context": self.context,
            "ocr_text": self.ocr.text if self.ocr else "",
            "ocr_confidence": self.ocr.confidence if self.ocr else 0.0,
            "element_count": len(self.detection.elements) if self.detection else 0,
            "timestamp": self.timestamp.isoformat() if self.timestamp else "",
        }

    def to_structured(self) -> dict:
        return {
            "observation_id": self.id,
            "summary": self.summary,
            "screen_text": self.ocr.text if self.ocr else "",
            "ui_elements": [
                {"type": e.type, "text": e.text, "position": {"x": e.x, "y": e.y, "w": e.width, "h": e.height}, "confidence": e.confidence}
                for e in (self.detection.elements if self.detection else [])
            ],
            "layout": [
                {"type": r.region_type, "position": {"x": r.x, "y": r.y, "w": r.width, "h": r.height}, "label": r.label}
                for r in (self.detection.layout if self.detection else [])
            ],
            "icons": [
                {"type": i.type, "position": {"x": i.x, "y": i.y, "w": i.width, "h": i.height}}
                for i in (self.detection.icons if self.detection else [])
            ],
        }


@dataclass
class VisionConfig:
    provider: VisionProvider = VisionProvider.BUILTIN
    ocr_engine: OCREngine = OCREngine.TESSERACT
    capture_quality: int = 75
    monitor: int = 0
    privacy_filters_enabled: bool = True
    auto_redact_sensitive: bool = True
    observation_mode: ObservationMode = ObservationMode.MANUAL
    max_image_size: int = 1920
    supported_formats: list[str] = field(default_factory=lambda: ["png", "jpg", "jpeg", "bmp", "webp"])


@dataclass
class VisionSessionState:
    session_id: str = ""
    is_observing: bool = False
    observation_mode: ObservationMode = ObservationMode.MANUAL
    last_observation: VisionObservation | None = None
    observation_count: int = 0
    started_at: datetime | None = None

    def __post_init__(self):
        if not self.session_id:
            self.session_id = uuid4().hex
        if not self.started_at:
            self.started_at = datetime.now(timezone.utc)


@dataclass
class MonitorInfo:
    id: int = 0
    name: str = ""
    width: int = 0
    height: int = 0
    is_primary: bool = False
    x: int = 0
    y: int = 0


@dataclass
class WorkspaceInspection:
    active_window: dict = field(default_factory=dict)
    window_title: str = ""
    application: str = ""
    screenshot: ScreenshotResult | None = None
    ocr: OCRResult | None = None
    elements: list[UIElement] = field(default_factory=list)
