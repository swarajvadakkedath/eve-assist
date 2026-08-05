"""VoiceSessionManager — VoiceOS foundation layer.

Owns:
  - Microphone lifecycle (acquire, release, hot-plug detection)
  - Push-to-talk activation / deactivation
  - Wake-word hooks (design-only — integration deferred)
  - Conversation state machine (idle → listening → processing → speaking → idle)
  - Interruption handling (barge-in, voice commands)
  - Audio input/output routing
  - STT orchestration (delegates to STTEngine)
  - TTS orchestration (delegates to TTSEngine)

Does NOT own:
  - LLM inference, routing, conversation memory, tools (EVE Core owns all of these)
  - Provider selection, model selection, health monitoring (SmartRouter / ProviderManager)
  - The user's identity — always "EVE", never "Hermes" in any user-facing path

Phase B foundation — voice personalisation, ambient computing, and overlay are
future work.  This module is the minimal substrate they will build on.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable
from uuid import uuid4

from aios.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Public enums / dataclasses
# ---------------------------------------------------------------------------

class MicrophoneState(str, Enum):
    """Physical microphone lifecycle."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    ACTIVE = "active"
    ERROR = "error"


class VoiceOSState(str, Enum):
    """High-level VoiceOS state exposed to the UI / tray / overlay."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    WAKE_DETECTED = "wake_detected"
    INTERRUPTED = "interrupted"
    ERROR = "error"


class InterruptionType(str, Enum):
    """What caused the interruption."""
    BARGE_IN = "barge_in"          # user spoke while EVE was speaking
    VOICE_COMMAND = "voice_command"  # detected a voice command mid-speech
    PUSH_TO_TALK = "push_to_talk"   # PTT key pressed during speech
    SYSTEM = "system"               # system event (e.g. incoming notification)


@dataclass
class MicrophoneInfo:
    """Metadata about the current audio input device."""
    device_id: str = ""
    name: str = ""
    state: MicrophoneState = MicrophoneState.DISCONNECTED
    sample_rate: int = 16000
    channels: int = 1
    is_default: bool = True
    last_error: str | None = None
    connected_at: datetime | None = None
    disconnected_at: datetime | None = None


@dataclass
class InterruptionEvent:
    """Captures an interruption that occurred during speech or processing."""
    interruption_type: InterruptionType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detail: str = ""
    utterance_id: str | None = None
    cancelled_text: str = ""


@dataclass
class VoiceOSSnapshot:
    """Immutable snapshot of VoiceOS state for UI / debugging."""
    state: VoiceOSState
    microphone: MicrophoneInfo
    conversation_id: str
    is_push_to_talk_active: bool
    wake_word_enabled: bool
    wake_word: str
    session_id: str
    uptime_seconds: float
    interruption_count: int
    last_transcript: str
    last_error: str | None


# ---------------------------------------------------------------------------
# Callbacks — VoiceOS emits lifecycle events, it does not own business logic
# ---------------------------------------------------------------------------

@dataclass
class VoiceOSCallbacks:
    """Injected callbacks — VoiceOS calls these, never imports business logic."""
    on_state_change: Callable[[VoiceOSState, VoiceOSState], Any] | None = None
    on_microphone_change: Callable[[MicrophoneInfo], Any] | None = None
    on_transcript_partial: Callable[[str, float], Any] | None = None
    on_transcript_final: Callable[[str, float], Any] | None = None
    on_interruption: Callable[[InterruptionEvent], Any] | None = None
    on_audio_level: Callable[[float], Any] | None = None
    on_error: Callable[[str], Any] | None = None


# ---------------------------------------------------------------------------
# VoiceSessionManager
# ---------------------------------------------------------------------------

class VoiceSessionManager:
    """Minimal VoiceOS foundation — microphone lifecycle, PTT, wake-word hooks,
    state machine, interruption handling, STT/TTS orchestration.

    Construction takes ONLY the low-level engines it wraps.  All higher-level
    decisions (what to do with a transcript, how to respond, which model to use)
    are delegated via ``VoiceOSCallbacks`` to the caller.
    """

    def __init__(
        self,
        stt_engine: Any | None = None,
        tts_engine: Any | None = None,
        event_bus: Any | None = None,
        callbacks: VoiceOSCallbacks | None = None,
        *,
        wake_word: str = "hey eve",
        wake_word_enabled: bool = False,
        push_to_talk_key: str = "v",
    ):
        self._stt = stt_engine
        self._tts = tts_engine
        self._event_bus = event_bus
        self._callbacks = callbacks or VoiceOSCallbacks()

        # State
        self._state = VoiceOSState.IDLE
        self._session_id = uuid4().hex
        self._started_at: datetime | None = None

        # Microphone
        self._microphone = MicrophoneInfo()

        # Conversation (set externally after construction)
        self._conversation_id: str = ""

        # Push-to-talk
        self._ptt_key = push_to_talk_key
        self._ptt_active = False
        self._ptt_held = False

        # Wake-word (design-only — no actual wake-word engine wired yet)
        self._wake_enabled = wake_word_enabled
        self._wake_word = wake_word

        # Interruption tracking
        self._interruption_count = 0
        self._last_transcript = ""
        self._last_error: str | None = None

        # Internal tasks
        self._listen_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    # ── Properties ──────────────────────────────────────────────────

    @property
    def state(self) -> VoiceOSState:
        return self._state

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def conversation_id(self) -> str:
        return self._conversation_id

    @property
    def microphone(self) -> MicrophoneInfo:
        return self._microphone

    @property
    def is_push_to_talk_active(self) -> bool:
        return self._ptt_active

    @property
    def is_wake_word_enabled(self) -> bool:
        return self._wake_enabled

    @property
    def wake_word(self) -> str:
        return self._wake_word

    # ── Lifecycle ───────────────────────────────────────────────────

    async def start(self) -> None:
        """Acquire microphone and initialise STT/TTS engines."""
        if self._started_at is not None:
            return
        self._started_at = datetime.now(timezone.utc)
        await self._acquire_microphone()
        if self._stt is not None:
            try:
                await self._stt.initialize()
            except Exception as exc:
                logger.warning("voiceos.stt_init_failed", error=str(exc))
        if self._tts is not None:
            try:
                await self._tts.initialize()
            except Exception as exc:
                logger.warning("voiceos.tts_init_failed", error=str(exc))
        logger.info("voiceos.started", session_id=self._session_id)

    async def shutdown(self) -> None:
        """Release microphone and cancel all tasks."""
        if self._listen_task is not None:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None
        await self._release_microphone()
        if self._stt is not None:
            try:
                await self._stt.cleanup()
            except Exception:
                pass
        if self._tts is not None:
            try:
                await self._tts.cleanup()
            except Exception:
                pass
        self._started_at = None
        await self._transition(VoiceOSState.IDLE)
        logger.info("voiceos.shutdown", session_id=self._session_id)

    # ── Conversation binding ────────────────────────────────────────

    def set_conversation(self, conversation_id: str) -> None:
        self._conversation_id = conversation_id

    # ── Microphone management ──────────────────────────────────────

    async def _acquire_microphone(self) -> None:
        """Attempt to acquire the default audio input device."""
        self._microphone.state = MicrophoneState.CONNECTING
        self._microphone.connected_at = datetime.now(timezone.utc)
        # Actual device acquisition is deferred to the platform layer.
        # For now we mark READY and let STTEngine handle the real device.
        self._microphone.state = MicrophoneState.READY
        await self._emit_microphone_change()

    async def _release_microphone(self) -> None:
        self._microphone.state = MicrophoneState.DISCONNECTED
        self._microphone.disconnected_at = datetime.now(timezone.utc)
        await self._emit_microphone_change()

    async def select_microphone(self, device_id: str) -> None:
        """Switch to a specific audio input device by id."""
        self._microphone.device_id = device_id
        self._microphone.state = MicrophoneState.CONNECTING
        await self._emit_microphone_change()
        # Platform device-switch deferred — mark READY
        self._microphone.state = MicrophoneState.READY
        await self._emit_microphone_change()

    async def list_microphones(self) -> list[dict[str, Any]]:
        """Return available audio input devices."""
        if self._stt is not None and hasattr(self._stt, "get_available_devices"):
            try:
                return await self._stt.get_available_devices()
            except Exception:
                pass
        return []

    # ── Push-to-talk ───────────────────────────────────────────────

    async def ptt_press(self) -> None:
        """Called when the PTT key is pressed."""
        if self._ptt_held:
            return
        self._ptt_held = True
        self._ptt_active = True
        await self.start_listening()

    async def ptt_release(self) -> None:
        """Called when the PTT key is released."""
        if not self._ptt_held:
            return
        self._ptt_held = False
        self._ptt_active = False
        transcript = await self.stop_listening()
        if transcript and self._callbacks.on_transcript_final:
            self._callbacks.on_transcript_final(transcript, 1.0)

    # ── Wake-word (design-only) ────────────────────────────────────

    def enable_wake_word(self, enabled: bool = True, wake_word: str | None = None) -> None:
        """Enable or disable wake-word detection.

        Phase B foundation: the hook is registered but no actual wake-word
        engine is integrated yet.  The wake-word pipeline will be wired in
        a future phase when an engine (e.g. Picovoice Porcupine, OpenWakeWord)
        is selected.
        """
        self._wake_enabled = enabled
        if wake_word is not None:
            self._wake_word = wake_word
        logger.info("voiceos.wake_word_config", enabled=self._wake_enabled, word=self._wake_word)

    async def on_wake_word_detected(self) -> None:
        """Hook called by a future wake-word engine when the wake phrase is detected.

        Transitions state to WAKE_DETECTED, then immediately begins listening.
        """
        if self._state == VoiceOSState.SPEAKING:
            await self._handle_interruption(InterruptionType.VOICE_COMMAND, "wake word detected")
        await self._transition(VoiceOSState.WAKE_DETECTED)
        await self.start_listening()

    # ── Listening ──────────────────────────────────────────────────

    async def start_listening(self, language: str | None = None) -> None:
        """Begin capturing audio and feeding it to STT."""
        async with self._lock:
            if self._state == VoiceOSState.LISTENING:
                return
            if self._state == VoiceOSState.SPEAKING:
                await self._handle_interruption(InterruptionType.BARGE_IN, "user started speaking")
            await self._transition(VoiceOSState.LISTENING)
            if self._stt is not None:
                try:
                    await self._stt.start_listening(language)
                except Exception as exc:
                    logger.warning("voiceos.stt_start_failed", error=str(exc))
            if self._event_bus is not None:
                await self._event_bus.publish(
                    "voice:listening:start",
                    {"session_id": self._session_id, "device": self._microphone.device_id},
                    source="voiceos",
                )
            self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop_listening(self) -> str | None:
        """Stop capturing audio and return the final transcript."""
        async with self._lock:
            if self._state != VoiceOSState.LISTENING:
                return None
            self._ptt_held = False
            if self._stt is not None:
                try:
                    await self._stt.stop_listening()
                except Exception:
                    pass
            if self._listen_task is not None:
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass
                self._listen_task = None
            if self._event_bus is not None:
                await self._event_bus.publish(
                    "voice:listening:stop",
                    {"session_id": self._session_id, "reason": "manual"},
                    source="voiceos",
                )
            transcript = self._last_transcript.strip() or None
            await self._transition(VoiceOSState.IDLE)
            return transcript

    async def _listen_loop(self) -> None:
        """Continuously read partial/final transcripts from STT engine."""
        try:
            if self._stt is None or not hasattr(self._stt, "recognize_stream"):
                return
            async for result in self._stt.recognize_stream():
                if self._state != VoiceOSState.LISTENING:
                    break
                text = getattr(result, "text", "") or ""
                confidence = getattr(result, "confidence", 0.0)
                is_final = getattr(result, "is_final", False)
                if text:
                    self._last_transcript = text
                if is_final and text.strip():
                    if self._callbacks.on_transcript_final:
                        self._callbacks.on_transcript_final(text, confidence)
                    if self._event_bus is not None:
                        await self._event_bus.publish(
                            "voice:transcript:final",
                            {"session_id": self._session_id, "text": text, "confidence": confidence},
                            source="voiceos",
                        )
                elif text:
                    if self._callbacks.on_transcript_partial:
                        self._callbacks.on_transcript_partial(text, confidence)
                    if self._event_bus is not None:
                        await self._event_bus.publish(
                            "voice:transcript:partial",
                            {"session_id": self._session_id, "text": text, "confidence": confidence},
                            source="voiceos",
                        )
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self._last_error = str(exc)
            logger.error("voiceos.listen_loop_error", error=str(exc))
            if self._callbacks.on_error:
                self._callbacks.on_error(str(exc))
            await self._transition(VoiceOSState.ERROR)

    # ── Speaking ───────────────────────────────────────────────────

    async def speak(self, text: str) -> str | None:
        """Speak text via TTS. Returns utterance_id."""
        if not text or not text.strip():
            return None
        if self._state == VoiceOSState.SPEAKING:
            await self._handle_interruption(InterruptionType.BARGE_IN, "new speech requested")
        await self._transition(VoiceOSState.SPEAKING)
        if self._tts is not None:
            try:
                utterance_id = await self._tts.speak(text)
                if self._event_bus is not None:
                    await self._event_bus.publish(
                        "voice:speaking:start",
                        {"session_id": self._session_id, "utterance_id": utterance_id},
                        source="voiceos",
                    )
                return utterance_id
            except Exception as exc:
                self._last_error = str(exc)
                logger.error("voiceos.tts_speak_failed", error=str(exc))
                await self._transition(VoiceOSState.ERROR)
                return None
        # No TTS engine — just transition back
        await self._transition(VoiceOSState.IDLE)
        return None

    async def stop_speaking(self, reason: str = "manual") -> None:
        """Stop current TTS playback."""
        if self._state != VoiceOSState.SPEAKING:
            return
        if self._tts is not None and hasattr(self._tts, "stop"):
            try:
                await self._tts.stop()
            except Exception:
                pass
        if self._event_bus is not None:
            await self._event_bus.publish(
                "voice:speaking:stop",
                {"session_id": self._session_id, "reason": reason},
                source="voiceos",
            )
        await self._transition(VoiceOSState.IDLE)

    # ── Interruption handling ──────────────────────────────────────

    async def _handle_interruption(self, interruption_type: InterruptionType, detail: str = "") -> None:
        """Handle an interruption — stop current TTS, record event, notify callbacks."""
        self._interruption_count += 1
        event = InterruptionEvent(
            interruption_type=interruption_type,
            detail=detail,
        )
        # Stop any active TTS
        if self._state == VoiceOSState.SPEAKING and self._tts is not None:
            try:
                await self._tts.stop()
            except Exception:
                pass
            if self._event_bus is not None:
                await self._event_bus.publish(
                    "voice:speaking:stop",
                    {"session_id": self._session_id, "reason": interruption_type.value},
                    source="voiceos",
                )
        await self._transition(VoiceOSState.INTERRUPTED)
        if self._callbacks.on_interruption:
            self._callbacks.on_interruption(event)
        logger.info(
            "voiceos.interruption",
            type=interruption_type.value,
            detail=detail,
            count=self._interruption_count,
        )

    async def interrupt(self, interruption_type: InterruptionType = InterruptionType.BARGE_IN, detail: str = "") -> None:
        """Public interruption API — can be called from hotkey handler or overlay."""
        await self._handle_interruption(interruption_type, detail)

    # ── Snapshot ───────────────────────────────────────────────────

    def snapshot(self) -> VoiceOSSnapshot:
        """Return an immutable snapshot of current VoiceOS state."""
        uptime = 0.0
        if self._started_at:
            uptime = (datetime.now(timezone.utc) - self._started_at).total_seconds()
        return VoiceOSSnapshot(
            state=self._state,
            microphone=self._microphone,
            conversation_id=self._conversation_id,
            is_push_to_talk_active=self._ptt_active,
            wake_word_enabled=self._wake_enabled,
            wake_word=self._wake_word,
            session_id=self._session_id,
            uptime_seconds=uptime,
            interruption_count=self._interruption_count,
            last_transcript=self._last_transcript,
            last_error=self._last_error,
        )

    # ── Internal ───────────────────────────────────────────────────

    async def _transition(self, new_state: VoiceOSState) -> None:
        old = self._state
        self._state = new_state
        if old != new_state:
            if self._callbacks.on_state_change:
                self._callbacks.on_state_change(new_state, old)
            if self._event_bus is not None:
                await self._event_bus.publish(
                    "voice:state:change",
                    {"session_id": self._session_id, "state": new_state.value, "previous_state": old.value},
                    source="voiceos",
                )

    async def _emit_microphone_change(self) -> None:
        if self._callbacks.on_microphone_change:
            self._callbacks.on_microphone_change(self._microphone)
