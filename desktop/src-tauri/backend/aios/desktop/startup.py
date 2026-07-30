"""Startup & Background Mode — Windows startup registration, background operation.

Sprint 12.7 — Startup & Background Mode.
"""

import os
import sys
from typing import Any

from aios.desktop.settings_store import SettingsStore
from aios.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import winreg
    _HAS_WINREG = True
except ImportError:
    _HAS_WINREG = False


class StartupManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._settings_store = None
        self._app_path = None
        self._initialized = True

    async def initialize(self, settings_store, app_path: str | None = None) -> None:
        self._settings_store = settings_store
        self._app_path = app_path or self._detect_app_path()

    def _detect_app_path(self) -> str:
        import sys
        if getattr(sys, "frozen", False):
            return sys.executable
        return sys.executable

    def enable_startup(self) -> bool:
        if not _HAS_WINREG:
            return False
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "AIOS", 0, winreg.REG_SZ, self._app_path)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            logger.error("startup.enable_failed", error=str(e))
            return False

    def disable_startup(self) -> bool:
        if not _HAS_WINREG:
            return False
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "AIOS")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            logger.error("startup.disable_failed", error=str(e))
            return False

    def is_startup_enabled(self) -> bool:
        if not _HAS_WINREG:
            return False
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "AIOS")
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def get_startup_path(self) -> str | None:
        if not _HAS_WINREG:
            return None
        import winreg
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, "AIOS")
                return value
            except FileNotFoundError:
                return None
            finally:
                winreg.CloseKey(key)
        except Exception:
            return None