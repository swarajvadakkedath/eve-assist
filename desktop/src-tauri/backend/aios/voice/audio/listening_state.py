"""Listening State Machine — manages the voice interaction lifecycle.

Official lifecycle:
    Idle → Listening → SpeechDetected → Recording → SilenceDetected → ProcessingReady → Idle

Supports pause, resume, timeout, cancel, and manual stop.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class ListeningState(Enum):
    """Listening lifecycle states."""
    IDLE = "idle"
    LISTENING = "listening"
    SPEECH_DETECTED = "speech_detected"
    RECORDING = "recording"
    SILENCE_DETECTED = "silence_detected"
    PROCESSING_READY = "processing_ready"
    PAUSED = "paused"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    ERROR = "error"


class ListeningEvent(Enum):
    """Events published by the state machine."""
    STATE_CHANGED = "state_changed"
    LISTENING_STARTED = "listening_started"
    LISTENING_STOPPED = "listening_stopped"
    SPEECH_DETECTED = "speech_detected"
    RECORDING_STARTED = "recording_started"
    SILENCE_DETECTED = "silence_detected"
    PROCESSING_READY = "processing_ready"
    TIMEOUT_OCCURRED = "timeout_occurred"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RESUMED = "resumed"


@dataclass
class ListeningSnapshot:
    """Snapshot of listening state for diagnostics."""
    state: ListeningState
    elapsed_seconds: float
    speech_duration: float
    silence_duration: float
    is_recording: bool
    timeout_seconds: float
    turn_count: int
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "speech_duration": round(self.speech_duration, 3),
            "silence_duration": round(self.silence_duration, 3),
            "is_recording": self.is_recording,
            "timeout_seconds": round(self.timeout_seconds, 2),
            "turn_count": self.turn_count,
            "error": self.error,
        }


# Valid state transitions
TRANSITIONS: dict[ListeningState, set[ListeningState]] = {
    ListeningState.IDLE: {ListeningState.LISTENING, ListeningState.CANCELLED},
    ListeningState.LISTENING: {
        ListeningState.SPEECH_DETECTED,
        ListeningState.TIMEOUT,
        ListeningState.CANCELLED,
        ListeningState.PAUSED,
    },
    ListeningState.SPEECH_DETECTED: {
        ListeningState.RECORDING,
        ListeningState.SILENCE_DETECTED,
        ListeningState.CANCELLED,
    },
    ListeningState.RECORDING: {
        ListeningState.SILENCE_DETECTED,
        ListeningState.CANCELLED,
        ListeningState.PAUSED,
    },
    ListeningState.SILENCE_DETECTED: {
        ListeningState.PROCESSING_READY,
        ListeningState.RECORDING,  # Speech resumes
        ListeningState.IDLE,  # Timeout
        ListeningState.CANCELLED,
    },
    ListeningState.PROCESSING_READY: {
        ListeningState.IDLE,
        ListeningState.LISTENING,  # Next turn
        ListeningState.CANCELLED,
    },
    ListeningState.PAUSED: {
        ListeningState.LISTENING,
        ListeningState.IDLE,
        ListeningState.CANCELLED,
    },
    ListeningState.TIMEOUT: {ListeningState.IDLE, ListeningState.CANCELLED},
    ListeningState.CANCELLED: {ListeningState.IDLE},
    ListeningState.ERROR: {ListeningState.IDLE, ListeningState.CANCELLED},
}


class ListeningStateMachine:
    """Manages the voice interaction lifecycle.

    Coordinates VAD events into a high-level state machine
    that the conversation pipeline can consume.
    """

    def __init__(self, *, silence_timeout: float = 1.5,
                 listening_timeout: float = 30.0,
                 speech_min_duration: float = 0.1):
        self._state = ListeningState.IDLE
        self._silence_timeout = silence_timeout
        self._listening_timeout = listening_timeout
        self._speech_min_duration = speech_min_duration

        # Timing
        self._state_entered_at: float = 0.0
        self._listening_started_at: float = 0.0
        self._speech_start_time: float = 0.0
        self._silence_start_time: float = 0.0
        self._total_speech_duration: float = 0.0
        self._total_silence_duration: float = 0.0

        # Turn tracking
        self._turn_count: int = 0
        self._error: Optional[str] = None

        # Event handlers
        self._event_handlers: dict[ListeningEvent, list[Callable]] = {}

        self._created_at = time.monotonic()
        self._state_entered_at = self._created_at

    @property
    def state(self) -> ListeningState:
        return self._state

    @property
    def is_recording(self) -> bool:
        return self._state in (ListeningState.RECORDING, ListeningState.SPEECH_DETECTED)

    @property
    def turn_count(self) -> int:
        return self._turn_count

    @property
    def elapsed(self) -> float:
        """Seconds since current state was entered."""
        return time.monotonic() - self._state_entered_at

    def on(self, event: ListeningEvent, handler: Callable) -> None:
        """Subscribe to a listening event."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: ListeningEvent, handler: Callable) -> None:
        """Unsubscribe from a listening event."""
        if event in self._event_handlers:
            self._event_handlers[event] = [
                h for h in self._event_handlers[event] if h != handler
            ]

    async def _emit(self, event: ListeningEvent, data: dict) -> None:
        """Emit a listening event."""
        for handler in self._event_handlers.get(event, []):
            try:
                if inspect.iscoroutinefunction(handler):
                    await handler(event, data)
                else:
                    handler(event, data)
            except Exception:
                pass

    def _transition(self, new_state: ListeningState, reason: str = "") -> bool:
        """Attempt a state transition.

        Returns True if transition was valid.
        """
        valid = TRANSITIONS.get(self._state, set())
        if new_state not in valid:
            return False

        now = time.monotonic()
        prev = self._state

        # Track timing
        if prev == ListeningState.RECORDING:
            self._total_speech_duration += now - self._speech_start_time
        elif prev == ListeningState.LISTENING and self._silence_start_time > 0:
            self._total_silence_duration += now - self._silence_start_time

        self._state = new_state
        self._state_entered_at = now

        # Reset timing for new state
        if new_state == ListeningState.LISTENING:
            self._listening_started_at = now
            self._silence_start_time = now
        elif new_state == ListeningState.SPEECH_DETECTED:
            self._speech_start_time = now
            self._silence_start_time = 0.0
        elif new_state == ListeningState.RECORDING:
            self._speech_start_time = now
        elif new_state == ListeningState.SILENCE_DETECTED:
            self._silence_start_time = now

        # Track turns
        if new_state == ListeningState.IDLE and prev == ListeningState.PROCESSING_READY:
            self._turn_count += 1

        # Emit state change event
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(ListeningEvent.STATE_CHANGED, {
                "from": prev.value,
                "to": new_state.value,
                "reason": reason,
            }))
        except RuntimeError:
            pass

        return True

    def start(self) -> bool:
        """Start listening. Transitions from IDLE to LISTENING."""
        return self._transition(ListeningState.LISTENING, "start")

    def on_speech_detected(self) -> bool:
        """VAD detected speech. Transitions to SPEECH_DETECTED or RECORDING."""
        if self._state == ListeningState.LISTENING:
            return self._transition(ListeningState.SPEECH_DETECTED, "speech")
        elif self._state == ListeningState.SILENCE_DETECTED:
            # Speech resumed during silence window
            return self._transition(ListeningState.RECORDING, "speech_resume")
        return False

    def on_speech_started(self) -> bool:
        """Speech confirmed (min duration met). Transitions to RECORDING."""
        if self._state == ListeningState.SPEECH_DETECTED:
            return self._transition(ListeningState.RECORDING, "confirmed")
        return False

    def on_silence_detected(self) -> bool:
        """VAD detected silence. Transitions to SILENCE_DETECTED."""
        if self._state in (ListeningState.RECORDING, ListeningState.SPEECH_DETECTED):
            return self._transition(ListeningState.SILENCE_DETECTED, "silence")
        return False

    def on_silence_timeout(self) -> bool:
        """Silence timeout reached. Transitions to PROCESSING_READY."""
        if self._state == ListeningState.SILENCE_DETECTED:
            return self._transition(ListeningState.PROCESSING_READY, "timeout")
        return False

    def on_processing_complete(self) -> bool:
        """Processing done. Transitions back to IDLE or LISTENING."""
        if self._state == ListeningState.PROCESSING_READY:
            return self._transition(ListeningState.IDLE, "complete")
        return False

    def pause(self) -> bool:
        """Pause listening."""
        if self._state in (ListeningState.LISTENING, ListeningState.RECORDING):
            return self._transition(ListeningState.PAUSED, "pause")
        return False

    def resume(self) -> bool:
        """Resume from pause."""
        if self._state == ListeningState.PAUSED:
            return self._transition(ListeningState.LISTENING, "resume")
        return False

    def cancel(self) -> bool:
        """Cancel current operation."""
        if self._state != ListeningState.IDLE:
            return self._transition(ListeningState.CANCELLED, "cancel")
        return False

    def stop(self) -> bool:
        """Force stop to IDLE."""
        if self._state != ListeningState.IDLE:
            self._state = ListeningState.IDLE
            self._state_entered_at = time.monotonic()
            return True
        return False

    def check_timeout(self) -> bool:
        """Check if listening timeout has been reached."""
        if self._state == ListeningState.LISTENING:
            if self.elapsed >= self._listening_timeout:
                return self._transition(ListeningState.TIMEOUT, "listening_timeout")
        elif self._state == ListeningState.SILENCE_DETECTED:
            if self.elapsed >= self._silence_timeout:
                return self._transition(ListeningState.PROCESSING_READY, "silence_timeout")
        return False

    def snapshot(self) -> ListeningSnapshot:
        """Take a snapshot of the current state."""
        return ListeningSnapshot(
            state=self._state,
            elapsed_seconds=self.elapsed,
            speech_duration=self._total_speech_duration,
            silence_duration=self._total_silence_duration,
            is_recording=self.is_recording,
            timeout_seconds=self._listening_timeout,
            turn_count=self._turn_count,
            error=self._error,
        )

    def to_dict(self) -> dict:
        """Serialize state machine state."""
        return self.snapshot().to_dict()
