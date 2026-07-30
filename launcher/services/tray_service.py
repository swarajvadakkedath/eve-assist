"""Tray service — abstracted system tray interface.

Current implementation: pystray.
Future Tauri tray replaces this without changing launcher logic.
"""

import logging
import threading
from typing import Protocol

logger = logging.getLogger("eve.launcher")

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


class TrayProtocol(Protocol):
    def start(self): ...
    def stop(self): ...


def _create_icon_image():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill="#e94560")
    draw.ellipse([12, 12, size - 12, size - 12], fill="#1a1a2e")
    draw.text((size // 2 - 8, size // 2 - 6), "E", fill="#e94560", font=None)
    return img


class TrayService:
    def __init__(
        self,
        on_open: callable = None,
        on_restart: callable = None,
        on_devtools: callable = None,
        on_health: callable = None,
        on_logs: callable = None,
        on_settings: callable = None,
        on_exit: callable = None,
        on_show: callable = None,
    ):
        self._on_open = on_open
        self._on_restart = on_restart
        self._on_devtools = on_devtools
        self._on_health = on_health
        self._on_logs = on_logs
        self._on_settings = on_settings
        self._on_exit = on_exit
        self._on_show = on_show
        self._icon = None
        self._thread = None

    def _build_menu(self):
        if not HAS_TRAY:
            return None
        items = [
            pystray.MenuItem("Open Eve", lambda: self._call(self._on_open)),
            pystray.MenuItem("Show Window", lambda: self._call(self._on_show)),
            pystray.MenuItem("Restart", lambda: self._call(self._on_restart)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Developer Tools", lambda: self._call(self._on_devtools)),
            pystray.MenuItem("Health Dashboard", lambda: self._call(self._on_health)),
            pystray.MenuItem("Logs", lambda: self._call(self._on_logs)),
            pystray.MenuItem("Settings", lambda: self._call(self._on_settings)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", lambda: self._call(self._on_exit)),
        ]
        return pystray.Menu(*items)

    def _call(self, handler):
        if handler:
            handler()

    def _run(self):
        if not HAS_TRAY:
            return
        icon = pystray.Icon(
            "eve_os",
            _create_icon_image(),
            "Eve OS",
            self._build_menu(),
        )
        self._icon = icon
        icon.run()

    def start(self):
        if not HAS_TRAY:
            logger.warning("pystray not installed — system tray unavailable")
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._icon:
            self._icon.stop()

    def is_available(self) -> bool:
        return HAS_TRAY

    def get_type(self) -> str:
        return "pystray" if HAS_TRAY else "none"
