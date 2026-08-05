"""Streaming TTS Manager — orchestrates streaming text-to-speech."""

from __future__ import annotations

import asyncio
import time
import threading
import heapq
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .events import SpeechChunk, TTSRequest, TTSEventType
from .provider import TTSProvider, TTSProviderConfig, TTSProviderState
from .session import StreamingTTSSession, TTSSessionState
from .metrics import TTSMetrics


class TTSManagerEventType(Enum):
    SESSION_QUEUED = "session_queued"
    SESSION_STARTED = "session_started"
    SESSION_COMPLETED = "session_completed"
    SESSION_CANCELLED = "session_cancelled"
    PROVIDER_FAILOVER = "provider_failover"
    QUEUE_CHANGED = "queue_changed"


@dataclass
class TTSConfig:
    provider_id: str = "openai"
    voice: str = "default"
    speed: float = 1.0
    sample_rate: int = 22050
    max_queue_size: int = 20
    enable_interrupt: bool = True
    buffer_size_ms: float = 100.0
    max_retries: int = 3
    retry_delay_s: float = 1.0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class SpeechQueue:
    """Priority queue for TTS sessions with cancellation support."""

    def __init__(self, max_size: int = 20):
        self._max_size = max_size
        self._queue: list = []
        self._sessions: dict[str, StreamingTTSSession] = {}
        self._counter = 0
        self._lock = threading.Lock()

    @property
    def size(self):
        with self._lock: return len(self._queue)

    @property
    def is_full(self):
        with self._lock: return len(self._queue) >= self._max_size

    def enqueue(self, session: StreamingTTSSession) -> bool:
        with self._lock:
            if len(self._queue) >= self._max_size: return False
            self._counter += 1
            heapq.heappush(self._queue, (-session.priority, self._counter, session.id))
            self._sessions[session.id] = session
            return True

    def dequeue(self) -> Optional[StreamingTTSSession]:
        with self._lock:
            if not self._queue: return None
            _, _, sid = heapq.heappop(self._queue)
            return self._sessions.pop(sid, None)

    def peek(self) -> Optional[StreamingTTSSession]:
        with self._lock:
            if not self._queue: return None
            _, _, sid = self._queue[0]
            return self._sessions.get(sid)

    def cancel(self, session_id: str) -> bool:
        with self._lock:
            self._queue = [(p, c, s) for p, c, s in self._queue if s != session_id]
            heapq.heapify(self._queue)
            session = self._sessions.pop(session_id, None)
            if session: session.cancel()
            return session is not None

    def clear(self):
        with self._lock:
            for sid, session in self._sessions.items():
                session.cancel()
            self._queue.clear()
            self._sessions.clear()

    def contains(self, session_id: str) -> bool:
        with self._lock: return session_id in self._sessions

    def get_all(self) -> list[StreamingTTSSession]:
        with self._lock:
            return [self._sessions[s] for _, _, s in sorted(self._queue)]


class StreamingTTSManager:
    def __init__(self, *, config=None):
        self._config = config or TTSConfig()
        self._metrics = TTSMetrics()
        self._queue = SpeechQueue(max_size=self._config.max_queue_size)
        self._sessions: dict[str, StreamingTTSSession] = {}
        self._active_session: Optional[StreamingTTSSession] = None
        self._providers: dict[str, TTSProvider] = {}
        self._event_handlers = {}
        self._lock = threading.Lock()
        self._created_at = time.monotonic()

    @property
    def config(self): return self._config
    @property
    def metrics(self): return self._metrics
    @property
    def active_session(self): return self._active_session
    @property
    def queue(self): return self._queue

    def on(self, event, handler):
        if event not in self._event_handlers: self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def _emit_sync(self, event, data):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_emit(event, data))
        except RuntimeError:
            for handler in self._event_handlers.get(event, []):
                try: handler(event, data)
                except Exception: pass

    async def _async_emit(self, event, data):
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler): await handler(event, data)
                else: handler(event, data)
            except Exception: pass

    def register_provider(self, provider_id, config=None):
        with self._lock:
            cfg = config or TTSProviderConfig(provider_id=provider_id)
            self._providers[provider_id] = TTSProvider(config=cfg)

    def unregister_provider(self, provider_id):
        with self._lock: self._providers.pop(provider_id, None)

    def get_provider(self, provider_id):
        with self._lock: return self._providers.get(provider_id)

    def synthesize(self, text: str, voice: str = "", speed: float = 1.0,
                   priority: int = 0, session_id: str = "") -> Optional[StreamingTTSSession]:
        """Submit text for synthesis. Returns session or None if queue full."""
        pid = self._config.provider_id
        provider = self.get_provider(pid)
        if not provider: return None

        request = TTSRequest(text=text, voice=voice or self._config.voice,
                             speed=speed, priority=priority, request_id=session_id)
        session = StreamingTTSSession(session_id=session_id, provider_id=pid, request=request)

        if not session.queue(): return None
        if not self._queue.enqueue(session):
            session.cancel()
            return None

        with self._lock: self._sessions[session.id] = session
        self._emit_sync(TTSManagerEventType.SESSION_QUEUED, {"session_id": session.id, "text": text[:50]})
        return session

    def start_next(self) -> Optional[StreamingTTSSession]:
        """Start the next queued session."""
        session = self._queue.dequeue()
        if not session: return None

        provider = self.get_provider(session.provider_id)
        if not provider or not provider.connect():
            session.set_error("connection_failed")
            self._metrics.record_failure()
            return None

        session.start_synthesis()
        self._metrics.record_synthesis()

        with self._lock: self._active_session = session
        self._emit_sync(TTSManagerEventType.SESSION_STARTED, {"session_id": session.id})
        return session

    def process_chunks(self, session_id: str = None) -> list[SpeechChunk]:
        """Synthesize and return chunks for the given or active session."""
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session: return []

        provider = self.get_provider(session.provider_id)
        if not provider: return []

        chunks = provider.synthesize(session.text, voice=session.voice,
                                     speed=session.request.speed)

        for chunk in chunks:
            session.receive_chunk(chunk)
            self._metrics.record_chunk(chunk.size_bytes)
            if session.state == TTSSessionState.SYNTHESIZING:
                session.start_playing()

        return chunks

    def synthesize_streaming(self, text: str, voice: str = "", speed: float = 1.0):
        """Generator that yields audio chunks with streaming synthesis."""
        pid = self._config.provider_id
        provider = self.get_provider(pid)
        if not provider or not provider.connect():
            return

        for chunk in provider.synthesize_streaming(text, voice=voice, speed=speed):
            self._metrics.record_chunk(chunk.size_bytes)
            yield chunk

    def play_chunk(self, chunk: SpeechChunk, session_id: str = None) -> bool:
        """Record that a chunk was played."""
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session: return False
        session.play_chunk(chunk)
        self._metrics.record_played()
        return True

    def cancel_session(self, session_id: str) -> bool:
        """Cancel a session (from queue or active)."""
        if self._queue.cancel(session_id):
            self._emit_sync(TTSManagerEventType.SESSION_CANCELLED, {"session_id": session_id})
            return True
        with self._lock:
            session = self._sessions.get(session_id)
        if session:
            session.cancel()
            if self._active_session and self._active_session.id == session_id:
                self._active_session = None
            self._emit_sync(TTSManagerEventType.SESSION_CANCELLED, {"session_id": session_id})
            return True
        return False

    def interrupt(self):
        """Interrupt the current playback."""
        with self._lock:
            if self._active_session:
                self._active_session.interrupt()
                self._active_session = None
            self._queue.clear()

    def complete_current(self):
        """Complete the current active session."""
        with self._lock:
            if self._active_session:
                self._active_session.complete()
                self._emit_sync(TTSManagerEventType.SESSION_COMPLETED, {
                    "session_id": self._active_session.id})
                self._active_session = None

    def failover(self, session_id: str = None) -> bool:
        """Failover to next provider."""
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session: return False

        old_pid = session.provider_id
        provider_list = list(self._providers.keys())
        if old_pid in provider_list:
            idx = provider_list.index(old_pid)
            new_pid = provider_list[(idx + 1) % len(provider_list)]
        else:
            new_pid = provider_list[0] if provider_list else None
        if not new_pid: return False

        new_provider = self.get_provider(new_pid)
        if not new_provider or not new_provider.connect(): return False

        session.switch_provider(new_pid)
        self._metrics.record_provider_switch()
        self._emit_sync(TTSManagerEventType.PROVIDER_FAILOVER, {
            "session_id": session.id, "old_provider": old_pid, "new_provider": new_pid})
        return True

    def recover(self, session_id: str = None) -> bool:
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session or session.state != TTSSessionState.ERROR: return False
        provider = self.get_provider(session.provider_id)
        if provider and provider.recover():
            session._transition(TTSSessionState.QUEUED, "recovery")
            self._metrics.record_recovery()
            return True
        return False

    def snapshot(self):
        metrics_snap = self._metrics.snapshot(
            active_sessions=len([s for s in self._sessions.values() if s.is_active]))
        session_snap = self._active_session.stats().to_dict() if self._active_session else None
        providers = {pid: p.snapshot() for pid, p in self._providers.items()}
        queue_sessions = [s.stats().to_dict() for s in self._queue.get_all()]
        return {"config": self._config.to_dict(), "session": session_snap,
                "metrics": metrics_snap.to_dict(), "providers": providers,
                "queue": queue_sessions, "queue_size": self._queue.size}

    def reset(self):
        self.interrupt()
        with self._lock:
            self._sessions.clear(); self._active_session = None
            self._metrics.reset(); self._providers.clear()
            self._created_at = time.monotonic()
