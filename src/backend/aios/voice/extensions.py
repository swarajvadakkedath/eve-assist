"""VoiceOS Extension Interfaces — hooks for future VoiceOS+ features.

Defines abstract interfaces that future features will implement:
  - WakeWordEngine — actual wake-word detection (Picovoice, OpenWakeWord)
  - OverlayExtension — system tray / floating overlay UI
  - AmbientExtension — background listening, proactive suggestions
  - VoiceCommandExtension — custom voice commands
  - HotkeyExtension — global keyboard shortcuts

Phase B foundation: these interfaces are defined but not wired.
Future phases will implement and register them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator
from uuid import uuid4

from aios.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Extension registry
# ---------------------------------------------------------------------------

class ExtensionType(str, Enum):
    """Types of VoiceOS extensions."""
    WAKE_WORD = "wake_word"
    OVERLAY = "overlay"
    AMBIENT = "ambient"
    VOICE_COMMAND = "voice_command"
    HOTKEY = "hotkey"
    NOTIFICATION = "notification"
    TTS_ENGINE = "tts_engine"
    STT_ENGINE = "stt_engine"


@dataclass
class ExtensionInfo:
    """Metadata about a registered extension."""
    extension_id: str
    extension_type: ExtensionType
    name: str
    version: str = "0.0.0"
    enabled: bool = True
    priority: int = 0  # higher = loaded first
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract extension interfaces
# ---------------------------------------------------------------------------

class VoiceOSExtension(ABC):
    """Base interface for all VoiceOS extensions."""

    @property
    @abstractmethod
    def extension_id(self) -> str:
        """Unique identifier for this extension."""

    @property
    @abstractmethod
    def extension_type(self) -> ExtensionType:
        """Type of extension."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @property
    def version(self) -> str:
        return "0.0.0"

    @abstractmethod
    async def start(self) -> None:
        """Start the extension."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the extension."""

    def get_info(self) -> ExtensionInfo:
        return ExtensionInfo(
            extension_id=self.extension_id,
            extension_type=self.extension_type,
            name=self.name,
            version=self.version,
        )


class WakeWordEngine(VoiceOSExtension):
    """Interface for wake-word detection engines.

    Implementations:
      - PicovoicePorcupine (future)
      - OpenWakeWord (future)
      - MockWakeWord (testing)
    """

    @property
    def extension_type(self) -> ExtensionType:
        return ExtensionType.WAKE_WORD

    @abstractmethod
    async def start_listening(self) -> None:
        """Start listening for the wake word."""

    @abstractmethod
    async def stop_listening(self) -> None:
        """Stop listening for the wake word."""

    @abstractmethod
    async def detections(self) -> AsyncIterator[dict]:
        """Yield wake-word detection events."""

    @abstractmethod
    def set_wake_word(self, wake_word: str) -> None:
        """Change the wake word phrase."""


class OverlayExtension(VoiceOSExtension):
    """Interface for system tray / floating overlay UI.

    The overlay shows:
      - Current VoiceOS state (idle, listening, processing, speaking)
      - Push-to-talk indicator
      - Quick settings (mute, volume, wake word toggle)
      - Recent transcript preview
    """

    @property
    def extension_type(self) -> ExtensionType:
        return ExtensionType.OVERLAY

    @abstractmethod
    async def show(self) -> None:
        """Show the overlay."""

    @abstractmethod
    async def hide(self) -> None:
        """Hide the overlay."""

    @abstractmethod
    async def update_state(self, state: dict) -> None:
        """Update the overlay with new VoiceOS state."""


class AmbientExtension(VoiceOSExtension):
    """Interface for background listening and proactive suggestions.

    Ambient mode:
      - Always listening (with user permission)
      - Detects relevant context (meetings, reminders, etc.)
      - Proactively offers help when appropriate
      - Respects privacy — only processes when triggered
    """

    @property
    def extension_type(self) -> ExtensionType:
        return ExtensionType.AMBIENT

    @abstractmethod
    async def start_ambient(self) -> None:
        """Start ambient listening mode."""

    @abstractmethod
    async def stop_ambient(self) -> None:
        """Stop ambient listening mode."""

    @abstractmethod
    async def suggestions(self) -> AsyncIterator[dict]:
        """Yield proactive suggestions based on ambient context."""


class VoiceCommandExtension(VoiceOSExtension):
    """Interface for custom voice commands.

    Users can define voice commands like:
      - "EVE, take a note" → creates a note
      - "EVE, start timer for 5 minutes" → starts a timer
      - "EVE, what's on my calendar?" → checks calendar
    """

    @property
    def extension_type(self) -> ExtensionType:
        return ExtensionType.VOICE_COMMAND

    @abstractmethod
    def register_command(self, phrase: str, handler: Any) -> None:
        """Register a voice command."""

    @abstractmethod
    def unregister_command(self, phrase: str) -> None:
        """Unregister a voice command."""

    @abstractmethod
    async def match_command(self, transcript: str) -> dict | None:
        """Match a transcript to a registered command. Returns command info or None."""


class HotkeyExtension(VoiceOSExtension):
    """Interface for global keyboard shortcuts.

    Default hotkeys (from SettingsStore):
      - ctrl+space: push-to-talk toggle
      - ctrl+shift+space: voice command mode
      - ctrl+alt+e: open EVE
    """

    @property
    def extension_type(self) -> ExtensionType:
        return ExtensionType.HOTKEY

    @abstractmethod
    def register_hotkey(self, keys: str, callback: Any) -> None:
        """Register a global hotkey."""

    @abstractmethod
    def unregister_hotkey(self, keys: str) -> None:
        """Unregister a global hotkey."""


# ---------------------------------------------------------------------------
# Extension registry (manages all registered extensions)
# ---------------------------------------------------------------------------

class VoiceOSExtensionRegistry:
    """Registry for VoiceOS extensions.

    Future phases will register their extensions here.
    """

    def __init__(self):
        self._extensions: dict[str, VoiceOSExtension] = {}
        self._by_type: dict[ExtensionType, list[VoiceOSExtension]] = {}

    def register(self, extension: VoiceOSExtension) -> None:
        """Register an extension."""
        info = extension.get_info()
        self._extensions[info.extension_id] = extension
        self._by_type.setdefault(info.extension_type, []).append(extension)
        logger.info("voiceos.extension_registered", id=info.extension_id, type=info.extension_type.value)

    def unregister(self, extension_id: str) -> None:
        """Unregister an extension."""
        ext = self._extensions.pop(extension_id, None)
        if ext:
            ext_type = ext.extension_type
            self._by_type[ext_type] = [
                e for e in self._by_type.get(ext_type, [])
                if e.extension_id != extension_id
            ]

    def get(self, extension_id: str) -> VoiceOSExtension | None:
        return self._extensions.get(extension_id)

    def get_by_type(self, extension_type: ExtensionType) -> list[VoiceOSExtension]:
        return self._by_type.get(extension_type, [])

    def list_all(self) -> list[ExtensionInfo]:
        return [ext.get_info() for ext in self._extensions.values()]

    async def start_all(self) -> None:
        """Start all registered extensions."""
        for ext in sorted(
            self._extensions.values(),
            key=lambda e: e.get_info().priority,
            reverse=True,
        ):
            try:
                await ext.start()
            except Exception as exc:
                logger.warning(
                    "voiceos.extension_start_failed",
                    id=ext.extension_id,
                    error=str(exc),
                )

    async def stop_all(self) -> None:
        """Stop all registered extensions."""
        for ext in self._extensions.values():
            try:
                await ext.stop()
            except Exception as exc:
                logger.warning(
                    "voiceos.extension_stop_failed",
                    id=ext.extension_id,
                    error=str(exc),
                )
