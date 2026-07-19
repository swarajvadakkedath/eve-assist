"""Global Hotkeys — configurable system-wide keyboard shortcuts.

Sprint 12.3 — Global Hotkeys.
"""

import threading
from typing import Callable, Any
from dataclasses import dataclass, field

from aios.desktop.settings_store import SettingsStore
from aios.utils.logger import get_logger

logger = get_logger(__name__)

try:
    import keyboard as kb
    _HAS_KEYBOARD = True
except ImportError:
    _HAS_KEYBOARD = False


DEFAULT_HOTKEYS: dict[str, str] = {
    "toggle_eve": "ctrl+space",
    "quick_command": "ctrl+shift+space",
    "new_conversation": "ctrl+alt+e",
}


@dataclass
class HotkeyBinding:
    action: str
    combination: str
    callback: Callable | None = None
    enabled: bool = True


class HotkeyManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._bindings: dict[str, HotkeyBinding] = {}
        self._registered: set[str] = set()
        self._initialized = True

    async def initialize(self, settings_store) -> None:
        shortcuts = await settings_store.get("global_shortcuts", {})
        for action, combination in shortcuts.items():
            self._bindings[action] = HotkeyBinding(
                action=action, combination=combination
            )

    def register(self, action: str, combination: str, callback: Callable) -> None:
        if not _HAS_KEYBOARD:
            return
        self._bindings[action] = HotkeyBinding(
            action=action, combination=combination, callback=callback
        )
        if action in self._registered:
            self.unregister(action)
        try:
            kb.add_hotkey(combination, callback)
            self._registered.add(action)
        except Exception as e:
            logger.error("hotkey.register_failed", action=action, error=str(e))

    def unregister(self, action: str) -> None:
        if not _HAS_KEYBOARD:
            return
        binding = self._bindings.get(action)
        if binding and action in self._registered:
            try:
                kb.remove_hotkey(binding.combination)
                self._registered.discard(action)
            except Exception as e:
                logger.error("hotkey.unregister_failed", action=action, error=str(e))

    def unregister_all(self) -> None:
        for action in list(self._registered):
            self.unregister(action)

    def get_binding(self, action: str) -> HotkeyBinding | None:
        return self._bindings.get(action)

    def get_all_bindings(self) -> list[HotkeyBinding]:
        return list(self._bindings.values())

    def is_registered(self, action: str) -> bool:
        return action in self._registered

    def check_conflicts(self, combination: str) -> list[str]:
        conflicts = []
        for action, binding in self._bindings.items():
            if binding.combination == combination:
                conflicts.append(action)
        return conflicts