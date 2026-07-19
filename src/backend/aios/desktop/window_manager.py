"""Window Management — window lifecycle, position, size persistence.

Sprint 12.6 — Window Management.
"""

from typing import Any
from aios.desktop.settings_store import SettingsStore
from aios.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import win32gui
    import win32con
    import win32api
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False


class WindowManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._settings_store = None
        self._window_handle = None
        self._window_title = "AIOS"
        self._position: tuple[int, int] | None = None
        self._size: tuple[int, int] | None = None
        self._initialized = True

    async def initialize(self, settings_store) -> None:
        self._settings_store = settings_store
        remember_pos = await settings_store.get("window.remember_position", True)
        remember_size = await settings_store.get("window.remember_size", True)
        if remember_pos:
            pos = await settings_store.get("window_position")
            if pos:
                self._position = tuple(pos)
        if remember_size:
            size = await settings_store.get("window_size")
            if size:
                self._size = tuple(size)

    def set_window_handle(self, hwnd: int) -> None:
        self._window_handle = hwnd

    def get_window_handle(self) -> int | None:
        return self._window_handle

    def show_window(self) -> None:
        if not _HAS_WIN32 or not self._window_handle:
            return
        import win32gui
        import win32con
        win32gui.ShowWindow(self._window_handle, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(self._window_handle)

    def hide_window(self) -> None:
        if not _HAS_WIN32 or not self._window_handle:
            return
        import win32gui
        import win32con
        win32gui.ShowWindow(self._window_handle, win32con.SW_HIDE)

    def minimize_window(self) -> None:
        if not _HAS_WIN32 or not self._window_handle:
            return
        import win32gui
        import win32con
        win32gui.ShowWindow(self._window_handle, win32con.SW_MINIMIZE)

    def restore_window(self) -> None:
        if not _HAS_WIN32 or not self._window_handle:
            return
        import win32gui
        import win32con
        win32gui.ShowWindow(self._window_handle, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(self._window_handle)

    def focus_window(self) -> None:
        if not _HAS_WIN32 or not self._window_handle:
            return
        import win32gui
        import win32con
        if win32gui.IsIconic(self._window_handle):
            win32gui.ShowWindow(self._window_handle, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(self._window_handle)

    def is_window_visible(self) -> bool:
        if not _HAS_WIN32 or not self._window_handle:
            return False
        import win32gui
        return win32gui.IsWindowVisible(self._window_handle)

    def get_window_rect(self) -> dict | None:
        if not _HAS_WIN32 or not self._window_handle:
            return None
        import win32gui
        rect = win32gui.GetWindowRect(self._window_handle)
        return {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3]}

    def save_window_state(self) -> None:
        if not self._settings_store:
            return
        rect = self.get_window_rect()
        if rect:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._settings_store.set("window_position", [rect["left"], rect["top"]]))
                    asyncio.ensure_future(self._settings_store.set("window_size", [rect["right"] - rect["left"], rect["bottom"] - rect["top"]]))
            except RuntimeError:
                pass