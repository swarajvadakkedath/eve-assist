"""Voice Preferences — persistent user voice preferences."""

from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Optional

from .models import IdentityPreferences


class PreferenceManager:
    """Manages persistent voice preferences.

    Stores user preferences for voice, speed, pitch, personality, etc.
    Supports file-based persistence and in-memory fallback.
    """

    def __init__(self, *, storage_path: Optional[str] = None):
        self._storage_path = storage_path
        self._preferences = IdentityPreferences()
        self._lock = threading.Lock()
        self._loaded = False
        self._modified = False

    @property
    def preferences(self) -> IdentityPreferences:
        return self._preferences

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def modified(self) -> bool:
        return self._modified

    def load(self) -> bool:
        if self._storage_path:
            try:
                path = Path(self._storage_path)
                if path.exists():
                    data = json.loads(path.read_text())
                    self._preferences = IdentityPreferences.from_dict(data)
                    self._loaded = True
                    self._modified = False
                    return True
            except Exception:
                pass
        self._loaded = True
        return False

    def save(self) -> bool:
        if self._storage_path:
            try:
                path = Path(self._storage_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(self._preferences.to_dict(), indent=2))
                self._modified = False
                return True
            except Exception:
                pass
        return False

    def update(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._preferences, key):
                    setattr(self._preferences, key, value)
            self._preferences.updated_at = time.monotonic()
            self._modified = True

    def get(self, key: str, default=None):
        with self._lock:
            return getattr(self._preferences, key, default)

    def set_preferred_voice(self, voice: str):
        self.update(preferred_voice=voice)

    def set_preferred_provider(self, provider: str):
        self.update(preferred_provider=provider)

    def set_speech_speed(self, speed: float):
        self.update(speech_speed=max(0.5, min(2.0, speed)))

    def set_pitch(self, pitch: float):
        self.update(pitch=max(-1.0, min(1.0, pitch)))

    def set_verbosity(self, verbosity: float):
        self.update(verbosity=max(0.0, min(1.0, verbosity)))

    def set_preferred_profile(self, profile_id: str):
        self.update(preferred_profile=profile_id)

    def set_address_user_as(self, name: str):
        self.update(address_user_as=name)

    def reset(self):
        with self._lock:
            self._preferences = IdentityPreferences()
            self._modified = True

    def export_dict(self) -> dict:
        return self._preferences.to_dict()

    def import_dict(self, data: dict):
        with self._lock:
            self._preferences = IdentityPreferences.from_dict(data)
            self._modified = True

    def snapshot(self) -> dict:
        return {
            "loaded": self._loaded,
            "modified": self._modified,
            "preferences": self._preferences.to_dict(),
        }
