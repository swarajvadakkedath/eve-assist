"""Settings Persistence — expand settings system with full persistence.

Sprint 12.8 — Settings Persistence.
"""

import json
import os
from pathlib import Path
from typing import Any
from threading import Lock

from aios.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SETTINGS: dict = {
    "theme": "dark",
    "accent_color": "#6366f1",
    "ai_provider": "openai",
    "ai_model": "gpt-4o",
    "startup_behavior": "restore",
    "window_position": None,
    "window_size": None,
    "global_shortcuts": {
        "toggle_eve": "ctrl+space",
        "quick_command": "ctrl+shift+space",
        "new_conversation": "ctrl+alt+e",
    },
    "notifications": {
        "permission_requests": True,
        "task_completed": True,
        "ai_finished": True,
        "plugin_installed": True,
        "update_available": True,
        "warnings": True,
        "errors": True,
    },
    "privacy": {
        "analytics_enabled": False,
        "crash_reporting": True,
    },
    "startup": {
        "launch_at_startup": False,
        "start_minimized": False,
        "background_mode": False,
        "minimize_to_tray_on_close": True,
    },
    "window": {
        "remember_position": True,
        "remember_size": True,
        "always_on_top": False,
    },
    "ui": {
        "theme": "dark",
        "accent_color": "#6366f1",
    },
    "ai": {
        "provider": "openai",
        "model": "gpt-4o",
    },
    "voice": {
        "stt_provider": "whisper",
        "tts_provider": "pyttsx3",
        "input_device": None,
        "output_device": None,
        "language": "en-US",
        "voice_id": "",
        "speaking_rate": 1.0,
        "pitch": 1.0,
        "push_to_talk_key": "v",
        "wake_word_enabled": False,
        "wake_word": "hey eve",
        "continuous_listening": False,
    },
}


class SettingsStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._settings: dict = dict(DEFAULT_SETTINGS)
        self._file_path = None
        self._initialized = True

    async def initialize(self, file_path: str | None = None) -> None:
        if file_path:
            self._file_path = file_path
        await self._load()

    async def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self._settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    async def set(self, key: str, value: Any) -> None:
        keys = key.split(".")
        target = self._settings
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        await self._save()

    async def get_all(self) -> dict:
        return dict(self._settings)

    async def update(self, updates: dict) -> None:
        self._deep_merge(self._settings, updates)
        await self._save()

    async def _load(self) -> None:
        if not self._file_path:
            return
        try:
            with open(self._file_path, "r") as f:
                data = json.load(f)
            self._deep_merge(self._settings, data)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    async def _save(self) -> None:
        if not self._file_path:
            return
        try:
            with open(self._file_path, "w") as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            logger.error("settings.save_failed", error=str(e))

    def _deep_merge(self, base: dict, override: dict) -> None:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
