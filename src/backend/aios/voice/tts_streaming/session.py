"""Streaming TTS Session — manages lifecycle of a streaming synthesis session."""

from __future__ import annotations

import asyncio
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .events import SpeechChunk, TTSRequest


class TTSSessionState(Enum):
    CREATED = "created"
    QUEUED = "queued"
    SYNTHESIZING = "synthesizing"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class TTSSessionEvent(Enum):
    STATE_CHANGED = "state_changed"
    CHUNK_READY = "chunk_ready"
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_RESUMED = "playback_resumed"
    PLAYBACK_COMPLETED = "playback_completed"
    SYNTHESIS_FAILED = "synthesis_failed"
    INTERRUPTED = "interrupted"


TTS_SESSION_TRANSITIONS = {
    TTSSessionState.CREATED: {TTSSessionState.QUEUED, TTSSessionState.CANCELLED},
    TTSSessionState.QUEUED: {TTSSessionState.SYNTHESIZING, TTSSessionState.CANCELLED, TTSSessionState.ERROR},
    TTSSessionState.SYNTHESIZING: {TTSSessionState.PLAYING, TTSSessionState.COMPLETED, TTSSessionState.CANCELLED, TTSSessionState.ERROR},
    TTSSessionState.PLAYING: {TTSSessionState.PAUSED, TTSSessionState.COMPLETED, TTSSessionState.CANCELLED, TTSSessionState.SYNTHESIZING},
    TTSSessionState.PAUSED: {TTSSessionState.PLAYING, TTSSessionState.CANCELLED},
    TTSSessionState.COMPLETED: {TTSSessionState.CREATED},
    TTSSessionState.CANCELLED: set(),
    TTSSessionState.ERROR: {TTSSessionState.CREATED, TTSSessionState.QUEUED},
}


@dataclass
class TTSSessionStats:
    session_id: str
    state: str
    provider: str
    text: str
    voice: str
    chunks_received: int = 0
    chunks_played: int = 0
    chunks_dropped: int = 0
    total_bytes: int = 0
    uptime_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class StreamingTTSSession:
    def __init__(self, *, session_id: str = "", provider_id: str = "default",
                 request: Optional[TTSRequest] = None):
        self._session_id = session_id or f"tts_{int(time.time() * 1000)}"
        self._provider_id = provider_id
        self._request = request or TTSRequest(text="")
        self._state = TTSSessionState.CREATED
        self._created_at = time.monotonic()
        self._state_entered_at = self._created_at
        self._error = None
        self._chunks_received = 0
        self._chunks_played = 0
        self._chunks_dropped = 0
        self._total_bytes = 0
        self._current_chunk: Optional[SpeechChunk] = None
        self._playback_position = 0
        self._event_handlers = {}
        self._lock = threading.Lock()

    @property
    def id(self): return self._session_id
    @property
    def state(self): return self._state
    @property
    def provider_id(self): return self._provider_id
    @property
    def request(self): return self._request
    @property
    def text(self): return self._request.text
    @property
    def voice(self): return self._request.voice
    @property
    def is_active(self): return self._state not in (TTSSessionState.CANCELLED, TTSSessionState.COMPLETED)
    @property
    def elapsed(self): return time.monotonic() - self._state_entered_at
    @property
    def uptime(self): return time.monotonic() - self._created_at
    @property
    def priority(self): return self._request.priority

    def on(self, event, handler):
        if event not in self._event_handlers: self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _transition(self, new_state, reason=""):
        valid = TTS_SESSION_TRANSITIONS.get(self._state, set())
        if new_state not in valid: return False
        prev = self._state
        self._state = new_state
        self._state_entered_at = time.monotonic()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(TTSSessionEvent.STATE_CHANGED, {
                "from": prev.value, "to": new_state.value, "reason": reason}))
        except RuntimeError: pass
        return True

    async def _emit(self, event, data):
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler): await handler(event, data)
                else: handler(event, data)
            except Exception: pass

    def queue(self): return self._transition(TTSSessionState.QUEUED, "queue")
    def start_synthesis(self): return self._transition(TTSSessionState.SYNTHESIZING, "start")
    def start_playing(self): return self._transition(TTSSessionState.PLAYING, "play")
    def pause(self): return self._transition(TTSSessionState.PAUSED, "pause")
    def resume(self): return self._transition(TTSSessionState.PLAYING, "resume")
    def complete(self): return self._transition(TTSSessionState.COMPLETED, "done")
    def cancel(self): return self._transition(TTSSessionState.CANCELLED, "cancel")

    def receive_chunk(self, chunk: SpeechChunk) -> bool:
        with self._lock:
            self._chunks_received += 1
            self._total_bytes += chunk.size_bytes
            self._current_chunk = chunk
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(TTSSessionEvent.CHUNK_READY, {
                "session_id": self._session_id, "chunk_index": chunk.chunk_index}))
        except RuntimeError: pass
        return True

    def play_chunk(self, chunk: SpeechChunk) -> bool:
        with self._lock:
            self._chunks_played += 1
            self._playback_position = chunk.chunk_index + 1
        return True

    def drop_chunk(self, chunk: SpeechChunk):
        with self._lock: self._chunks_dropped += 1

    def set_error(self, error: str):
        self._error = error
        self._transition(TTSSessionState.ERROR, error)

    def interrupt(self):
        self._transition(TTSSessionState.CANCELLED, "interrupt")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(TTSSessionEvent.INTERRUPTED, {
                "session_id": self._session_id}))
        except RuntimeError: pass

    def switch_provider(self, new_provider_id):
        with self._lock: self._provider_id = new_provider_id
        return True

    def stats(self):
        with self._lock:
            return TTSSessionStats(
                session_id=self._session_id, state=self._state.value, provider=self._provider_id,
                text=self._request.text, voice=self._request.voice,
                chunks_received=self._chunks_received, chunks_played=self._chunks_played,
                chunks_dropped=self._chunks_dropped, total_bytes=self._total_bytes,
                uptime_seconds=self.uptime, error=self._error)
