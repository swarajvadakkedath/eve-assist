"""Streaming STT Session — manages lifecycle of a streaming recognition session."""

from __future__ import annotations

import asyncio
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .events import WordTiming


class SessionState(Enum):
    CREATED = "created"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    RECEIVING = "receiving"
    FINALISING = "finalising"
    COMPLETED = "completed"
    CLOSED = "closed"
    ERROR = "error"


class SessionEvent(Enum):
    STATE_CHANGED = "state_changed"
    PARTIAL_TRANSCRIPT = "partial_transcript"
    FINAL_TRANSCRIPT = "final_transcript"
    PROVIDER_CONNECTED = "provider_connected"
    PROVIDER_DISCONNECTED = "provider_disconnected"
    PROVIDER_SWITCHED = "provider_switched"
    RECOGNITION_STARTED = "recognition_started"
    RECOGNITION_STOPPED = "recognition_stopped"
    RECOGNITION_RECOVERED = "recognition_recovered"
    RECOGNITION_FAILED = "recognition_failed"
    ERROR = "error"


SESSION_TRANSITIONS = {
    SessionState.CREATED: {SessionState.CONNECTING, SessionState.CLOSED},
    SessionState.CONNECTING: {SessionState.STREAMING, SessionState.ERROR, SessionState.CLOSED},
    SessionState.STREAMING: {SessionState.RECEIVING, SessionState.FINALISING, SessionState.ERROR, SessionState.CLOSED},
    SessionState.RECEIVING: {SessionState.STREAMING, SessionState.FINALISING, SessionState.ERROR, SessionState.CLOSED},
    SessionState.FINALISING: {SessionState.COMPLETED, SessionState.ERROR, SessionState.CLOSED},
    SessionState.COMPLETED: {SessionState.CLOSED, SessionState.CREATED},
    SessionState.CLOSED: set(),
    SessionState.ERROR: {SessionState.CREATED, SessionState.CLOSED, SessionState.CONNECTING},
}


@dataclass
class TranscriptChunk:
    text: str = ""
    confidence: float = 0.0
    is_final: bool = False
    words: list = field(default_factory=list)
    provider: str = ""
    timestamp: float = field(default_factory=time.monotonic)
    language: str = ""

    def to_dict(self) -> dict:
        return {"text": self.text, "confidence": round(self.confidence, 4), "is_final": self.is_final,
                "words": [w.to_dict() for w in self.words], "provider": self.provider,
                "timestamp": self.timestamp, "language": self.language}


@dataclass
class SessionStats:
    session_id: str
    state: str
    provider: str
    partial_count: int = 0
    final_count: int = 0
    total_words: int = 0
    avg_confidence: float = 0.0
    uptime_seconds: float = 0.0
    bytes_sent: int = 0
    chunks_sent: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class StreamingSTTSession:
    def __init__(self, *, session_id: str = "", provider_id: str = "default"):
        self._session_id = session_id or f"stt_{int(time.time() * 1000)}"
        self._provider_id = provider_id
        self._state = SessionState.CREATED
        self._created_at = time.monotonic()
        self._state_entered_at = self._created_at
        self._error = None
        self._partial_text = ""
        self._final_text = ""
        self._partial_count = 0
        self._final_count = 0
        self._total_words = 0
        self._confidence_sum = 0.0
        self._confidence_count = 0
        self._bytes_sent = 0
        self._chunks_sent = 0
        self._event_handlers = {}
        self._lock = threading.Lock()

    @property
    def id(self): return self._session_id
    @property
    def state(self): return self._state
    @property
    def provider_id(self): return self._provider_id
    @property
    def partial_text(self):
        with self._lock: return self._partial_text
    @property
    def final_text(self):
        with self._lock: return self._final_text
    @property
    def is_active(self): return self._state not in (SessionState.CLOSED, SessionState.COMPLETED)
    @property
    def elapsed(self): return time.monotonic() - self._state_entered_at
    @property
    def uptime(self): return time.monotonic() - self._created_at

    def on(self, event, handler):
        if event not in self._event_handlers: self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event, handler):
        if event in self._event_handlers:
            self._event_handlers[event] = [h for h in self._event_handlers[event] if h != handler]

    async def _emit(self, event, data):
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler): await handler(event, data)
                else: handler(event, data)
            except Exception: pass

    def _transition(self, new_state, reason=""):
        valid = SESSION_TRANSITIONS.get(self._state, set())
        if new_state not in valid: return False
        now = time.monotonic()
        prev = self._state
        self._state = new_state
        self._state_entered_at = now
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(SessionEvent.STATE_CHANGED, {
                "from": prev.value, "to": new_state.value, "reason": reason, "session_id": self._session_id}))
        except RuntimeError: pass
        return True

    def connect(self): return self._transition(SessionState.CONNECTING, "connect")
    def start_streaming(self): return self._transition(SessionState.STREAMING, "start_streaming")

    def receive_partial(self, text, confidence=0.0, words=None, provider=""):
        with self._lock:
            self._partial_text = text
            self._partial_count += 1
            word_list = words or []
            self._total_words += len(word_list)
            if confidence > 0:
                self._confidence_sum += confidence
                self._confidence_count += 1
            if self._state == SessionState.STREAMING:
                self._transition(SessionState.RECEIVING, "partial_received")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(SessionEvent.PARTIAL_TRANSCRIPT, {
                "session_id": self._session_id, "text": text, "confidence": confidence, "provider": provider}))
        except RuntimeError: pass

    def receive_final(self, text, confidence=0.0, words=None, provider=""):
        with self._lock:
            self._final_text += text
            self._final_count += 1
            self._partial_text = ""
            word_list = words or []
            self._total_words += len(word_list)
            if confidence > 0:
                self._confidence_sum += confidence
                self._confidence_count += 1
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(SessionEvent.FINAL_TRANSCRIPT, {
                "session_id": self._session_id, "text": text, "confidence": confidence, "provider": provider}))
        except RuntimeError: pass

    def finish(self):
        if not self._transition(SessionState.FINALISING, "finish"): return False
        return self._transition(SessionState.COMPLETED, "finalised")

    def close(self): self._transition(SessionState.CLOSED, "close")
    def set_error(self, error):
        self._error = error
        self._transition(SessionState.ERROR, error)

    def switch_provider(self, new_provider_id):
        with self._lock: self._provider_id = new_provider_id
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(SessionEvent.PROVIDER_SWITCHED, {
                "session_id": self._session_id, "new_provider": new_provider_id}))
        except RuntimeError: pass
        return True

    def add_bytes_sent(self, count):
        with self._lock:
            self._bytes_sent += count
            self._chunks_sent += 1

    def stats(self):
        with self._lock:
            avg_conf = self._confidence_sum / self._confidence_count if self._confidence_count > 0 else 0.0
            return SessionStats(session_id=self._session_id, state=self._state.value, provider=self._provider_id,
                                partial_count=self._partial_count, final_count=self._final_count,
                                total_words=self._total_words, avg_confidence=avg_conf, uptime_seconds=self.uptime,
                                bytes_sent=self._bytes_sent, chunks_sent=self._chunks_sent, error=self._error)
