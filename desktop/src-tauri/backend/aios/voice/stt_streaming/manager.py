"""Streaming STT Manager — orchestrates streaming speech recognition."""

from __future__ import annotations

import asyncio
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .provider import STTProvider, ProviderConfig
from .session import StreamingSTTSession, SessionState
from .metrics import TranscriptMetrics


class ManagerEventType(Enum):
    SESSION_STARTED = "session_started"
    SESSION_STOPPED = "session_stopped"
    PROVIDER_FAILOVER = "provider_failover"
    PIPELINE_ERROR = "pipeline_error"


@dataclass
class STTConfig:
    language: str = "en"
    auto_detect_language: bool = True
    model: str = ""
    provider_id: str = "openai"
    confidence_threshold: float = 0.0
    partial_update_frequency_ms: float = 100.0
    provider_priority: list = field(default_factory=list)
    max_retries: int = 3
    retry_delay_s: float = 1.0
    timeout_s: float = 30.0
    sample_rate: int = 16000

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class StreamingSTTManager:
    def __init__(self, *, config=None):
        self._config = config or STTConfig()
        self._metrics = TranscriptMetrics()
        self._sessions = {}
        self._active_session = None
        self._providers = {}
        self._event_handlers = {}
        self._lock = threading.Lock()
        self._created_at = time.monotonic()

    @property
    def config(self): return self._config
    @property
    def metrics(self): return self._metrics
    @property
    def active_session(self): return self._active_session

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
            cfg = config or ProviderConfig(provider_id=provider_id)
            self._providers[provider_id] = STTProvider(config=cfg)

    def unregister_provider(self, provider_id):
        with self._lock: self._providers.pop(provider_id, None)

    def get_provider(self, provider_id):
        with self._lock: return self._providers.get(provider_id)

    def start_session(self, session_id="", provider_id=None):
        pid = provider_id or self._config.provider_id
        provider = self.get_provider(pid)
        if not provider: return None
        session = StreamingSTTSession(session_id=session_id, provider_id=pid)
        session.connect()
        if not provider.connect():
            session.set_error("connection_failed")
            self._metrics.record_failure()
            return None
        session.start_streaming()
        stream_id = provider.start_stream()
        if not stream_id:
            session.set_error("stream_start_failed")
            self._metrics.record_failure()
            return None
        with self._lock:
            self._sessions[session.id] = session
            self._active_session = session
        self._emit_sync(ManagerEventType.SESSION_STARTED, {"session_id": session.id, "provider": pid})
        return session

    def stop_session(self, session_id=None):
        with self._lock:
            sid = session_id or (self._active_session.id if self._active_session else None)
            if not sid: return
            session = self._sessions.get(sid)
        if session:
            session.finish()
            provider = self.get_provider(session.provider_id)
            if provider: provider.finish_stream()
            session.close()
            self._emit_sync(ManagerEventType.SESSION_STOPPED, {"session_id": sid})
        with self._lock:
            if self._active_session and self._active_session.id == sid:
                self._active_session = None

    def send_audio(self, data, session_id=None):
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session or session.state != SessionState.STREAMING: return False
        provider = self.get_provider(session.provider_id)
        if not provider or not provider.send_audio(data): return False
        session.add_bytes_sent(len(data))
        return True

    def process_partial(self, text, confidence=0.0, words=None, session_id=None):
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session: return
        session.receive_partial(text, confidence=confidence, words=words, provider=session.provider_id)
        self._metrics.record_partial(text, confidence)

    def process_final(self, text, confidence=0.0, words=None, session_id=None):
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session: return
        session.receive_final(text, confidence=confidence, words=words, provider=session.provider_id)
        self._metrics.record_final(text, confidence)

    def failover(self, session_id=None):
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session: return False
        old_provider = session.provider_id
        provider_list = list(self._providers.keys())
        if old_provider in provider_list:
            idx = provider_list.index(old_provider)
            new_pid = provider_list[(idx + 1) % len(provider_list)] if provider_list else None
        else:
            new_pid = provider_list[0] if provider_list else None
        if not new_pid: return False
        new_provider = self.get_provider(new_pid)
        if not new_provider or not new_provider.connect(): return False
        session.switch_provider(new_pid)
        stream_id = new_provider.start_stream()
        if not stream_id:
            session.set_error("failover_stream_failed")
            return False
        self._metrics.record_provider_switch()
        self._emit_sync(ManagerEventType.PROVIDER_FAILOVER, {
            "session_id": session.id, "old_provider": old_provider, "new_provider": new_pid})
        return True

    def recover(self, session_id=None):
        with self._lock:
            session = self._active_session
            if session_id: session = self._sessions.get(session_id)
        if not session or session.state != SessionState.ERROR: return False
        provider = self.get_provider(session.provider_id)
        if provider and provider.recover():
            session._transition(SessionState.CONNECTING, "recovery")
            session.start_streaming()
            provider.start_stream()
            self._metrics.record_recovery()
            return True
        return False

    def snapshot(self):
        metrics_snap = self._metrics.snapshot(
            active_sessions=len([s for s in self._sessions.values() if s.is_active]))
        session_snap = self._active_session.stats().to_dict() if self._active_session else None
        providers = {pid: p.snapshot() for pid, p in self._providers.items()}
        return {"config": self._config.to_dict(), "session": session_snap,
                "metrics": metrics_snap.to_dict(), "providers": providers}

    def reset(self):
        with self._lock:
            self._sessions.clear(); self._active_session = None
            self._metrics.reset(); self._providers.clear()
            self._created_at = time.monotonic()
