"""Context Providers — modular context sources for the Context Engine."""
from aios.core.context.providers.base import (
    ClipboardProvider,
    WindowProvider,
    WorkspaceProvider,
    GitProvider,
    BrowserProvider,
    DesktopProvider,
    VoiceProvider,
    MemoryProvider,
    ProviderHealthProvider,
    CalendarProvider,
    SelectionProvider,
    ApplicationProvider,
    ToolProvider,
    NotificationProvider,
)

__all__ = [
    "ClipboardProvider",
    "WindowProvider",
    "WorkspaceProvider",
    "GitProvider",
    "BrowserProvider",
    "DesktopProvider",
    "VoiceProvider",
    "MemoryProvider",
    "ProviderHealthProvider",
    "CalendarProvider",
    "SelectionProvider",
    "ApplicationProvider",
    "ToolProvider",
    "NotificationProvider",
]
