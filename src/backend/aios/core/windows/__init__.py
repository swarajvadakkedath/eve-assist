"""Windows Adapter package — platform-independent wrappers for Windows APIs."""

from .adapter import WindowsAdapter
from .clipboard import ClipboardService
from .filesystem import FileSystemService
from .process import ProcessService
from .active_window import ActiveWindowService
from .monitor import MonitorService
from .ui_automation import UIAutomationService
from .system_info import SystemInfoService
from .exceptions import (
    WindowsAdapterError,
    ClipboardError,
    FileOperationError,
    FileNotFoundError_,
    PathTraversalError,
    ProcessError,
    ProcessNotFoundError,
    ProcessTerminationError,
    ActiveWindowError,
    MonitorError,
    UIAutomationError,
    SystemInfoError,
    ValidationError,
)

__all__ = [
    "WindowsAdapter",
    "ClipboardService",
    "FileSystemService",
    "ProcessService",
    "ActiveWindowService",
    "MonitorService",
    "UIAutomationService",
    "SystemInfoService",
    "WindowsAdapterError",
    "ClipboardError",
    "FileOperationError",
    "FileNotFoundError_",
    "PathTraversalError",
    "ProcessError",
    "ProcessNotFoundError",
    "ProcessTerminationError",
    "ActiveWindowError",
    "MonitorError",
    "UIAutomationError",
    "SystemInfoError",
    "ValidationError",
]
