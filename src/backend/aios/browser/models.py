"""Browser automation data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BrowserInstance:
    instance_id: str
    browser_type: str
    headless: bool
    created_at: datetime = field(default_factory=datetime.utcnow)
    active_page_id: str | None = None
    page_count: int = 0


@dataclass
class TabInfo:
    page_id: str
    title: str
    url: str
    index: int


@dataclass
class NavigationResult:
    url: str
    title: str
    status_code: int | None = None
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class ExtractionResult:
    text: str = ""
    items: list = field(default_factory=list)
    count: int = 0
    error: str | None = None


@dataclass
class ScreenshotResult:
    image_data: bytes = b""
    width: int = 0
    height: int = 0
    format: str = "png"
    error: str | None = None


@dataclass
class DownloadResult:
    file_path: str = ""
    file_name: str = ""
    file_size: int = 0
    mime_type: str = ""
    success: bool = False
    error: str | None = None


@dataclass
class UploadResult:
    success: bool = False
    file_name: str = ""
    error: str | None = None


@dataclass
class ExecutionResult:
    success: bool = False
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class FormInfo:
    selector: str
    inputs: list[dict] = field(default_factory=list)
    buttons: list[dict] = field(default_factory=list)
    method: str = "get"
    action: str = ""


@dataclass
class LinkInfo:
    text: str
    href: str
    title: str = ""
    selector: str = ""
