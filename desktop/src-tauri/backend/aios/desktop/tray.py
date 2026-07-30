"""System Tray Integration — tray icon, menu, status updates.

Sprint 12.2 — System Tray Integration.
"""

import asyncio
import threading
from typing import Callable, Any

from aios.desktop.status_service import StatusService, AppStatus
from aios.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_PYSTRAY = True
except ImportError:
    _HAS_PYSTRAY = False


STATUS_ICONS: dict[AppStatus, str] = {
    AppStatus.READY: "●",
    AppStatus.THINKING: "◌",
    AppStatus.EXECUTING: "⚡",
    AppStatus.OFFLINE: "○",
    AppStatus.ERROR: "✕",
    AppStatus.STARTING: "◌",
    AppStatus.LISTENING: "🎤",
    AppStatus.PLANNING: "📋",
    AppStatus.WAITING: "⏳",
    AppStatus.UPDATING: "⬆",
}


class SystemTray:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._status_service = StatusService()
        self._icon = None
        self._menu_items: dict = {}
        self._callbacks: dict = {}
        self._initialized = True

    def set_callbacks(self, callbacks: dict[str, Callable]) -> None:
        self._callbacks = callbacks

    def run(self) -> None:
        if not _HAS_PYSTRAY:
            return
        from PIL import Image, ImageDraw

        def create_icon_image(status: AppStatus) -> Image.Image:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            color = {
                AppStatus.READY: (99, 102, 241, 255),
                AppStatus.THINKING: (251, 191, 36, 255),
                AppStatus.EXECUTING: (52, 211, 153, 255),
                AppStatus.OFFLINE: (156, 163, 175, 255),
                AppStatus.ERROR: (239, 68, 68, 255),
                AppStatus.STARTING: (156, 163, 175, 255),
            }.get(self._status_service.get_status(), (156, 163, 175, 255))
            draw.ellipse([8, 8, 56, 56], fill=color)
            return img

        self._icon = pystray.Icon(
            "aios",
            create_icon_image(AppStatus.READY),
            "AIOS",
            menu=pystray.Menu(
                pystray.MenuItem("Open AIOS", lambda: self._call("open")),
                pystray.MenuItem("New Conversation", lambda: self._call("new_conversation")),
                pystray.MenuItem("Settings", lambda: self._call("settings")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Restart AIOS", lambda: self._call("restart")),
                pystray.MenuItem("Check Status", lambda: self._call("check_status")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit", lambda: self._call("exit")),
            ),
        )

    def run(self) -> None:
        if not _HAS_PYSTRAY:
            return
        self._icon.run()