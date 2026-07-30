"""Desktop integration module for AIOS native Windows experience."""

from aios.desktop.status_service import StatusService, AppStatus, StatusObserver
from aios.desktop.settings_store import SettingsStore
from aios.desktop.app_shell import AppShell
from aios.desktop.tray import SystemTray
from aios.desktop.hotkeys import HotkeyManager
from aios.desktop.notifications import NotificationService
from aios.desktop.window_manager import WindowManager
from aios.desktop.startup import StartupManager

__all__ = [
    "StatusService",
    "AppStatus",
    "StatusObserver",
    "SettingsStore",
    "AppShell",
    "SystemTray",
    "HotkeyManager",
    "NotificationService",
    "WindowManager",
    "StartupManager",
]
