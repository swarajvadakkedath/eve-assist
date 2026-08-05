"""STT Provider — abstraction for speech-to-text provider integration."""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProviderState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"
    RECOVERING = "recovering"


class ProviderCapability(Enum):
    STREAMING = "streaming"
    PARTIAL_RESULTS = "partial_results"
    WORD_TIMING = "word_timing"
    SPEAKER_DIARIZATION = "speaker_diarization"
    MULTI_LANGUAGE = "multi_language"


@dataclass
class ProviderConfig:
    provider_id: str
    model: str = ""
    language: str = "en"
    auto_detect_language: bool = True
    sample_rate: int = 16000
    channels: int = 1
    encoding: str = "pcm_16"
    enable_partial_results: bool = True
    enable_word_timing: bool = True
    confidence_threshold: float = 0.0
    max_retries: int = 3
    retry_delay_s: float = 1.0
    timeout_s: float = 30.0
    priority: int = 100

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ProviderHealth:
    provider_id: str
    state: ProviderState = ProviderState.DISCONNECTED
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    last_error: str = ""
    last_success_time: float = 0.0
    consecutive_failures: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0: return 0.0
        return self.successful_requests / self.total_requests

    def to_dict(self) -> dict:
        return {"provider_id": self.provider_id, "state": self.state.value,
                "total_requests": self.total_requests, "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests, "success_rate": round(self.success_rate, 4),
                "avg_latency_ms": round(self.avg_latency_ms, 3), "last_error": self.last_error,
                "consecutive_failures": self.consecutive_failures}


class STTProvider:
    def __init__(self, *, config=None):
        self._config = config or ProviderConfig(provider_id="default")
        self._state = ProviderState.DISCONNECTED
        self._health = ProviderHealth(provider_id=self._config.provider_id)
        self._lock = threading.Lock()
        self._stream_id = None
        self._bytes_sent = 0
        self._chunks_sent = 0

    @property
    def config(self): return self._config
    @property
    def state(self): return self._state
    @property
    def health(self):
        with self._lock: return self._health
    @property
    def provider_id(self): return self._config.provider_id
    @property
    def is_connected(self): return self._state in (ProviderState.CONNECTED, ProviderState.STREAMING)

    def connect(self) -> bool:
        with self._lock:
            self._state = ProviderState.CONNECTING
            self._health.state = ProviderState.CONNECTING
            self._state = ProviderState.CONNECTED
            self._health.state = ProviderState.CONNECTED
            self._health.consecutive_failures = 0
            return True

    def start_stream(self):
        if not self.is_connected: return None
        with self._lock:
            self._state = ProviderState.STREAMING
            self._health.state = ProviderState.STREAMING
            self._stream_id = f"stream_{int(time.time() * 1000)}"
            self._bytes_sent = 0
            self._chunks_sent = 0
            return self._stream_id

    def send_audio(self, data: bytes) -> bool:
        if self._state != ProviderState.STREAMING: return False
        with self._lock:
            self._bytes_sent += len(data)
            self._chunks_sent += 1
            self._health.total_requests += 1
            self._health.successful_requests += 1
            self._health.last_success_time = time.monotonic()
        return True

    def finish_stream(self):
        if self._state != ProviderState.STREAMING: return None
        with self._lock:
            self._state = ProviderState.CONNECTED
            self._health.state = ProviderState.CONNECTED
            stream_id = self._stream_id
            self._stream_id = None
            return {"stream_id": stream_id, "status": "completed", "text": "", "confidence": 0.0}

    def disconnect(self):
        with self._lock:
            self._state = ProviderState.DISCONNECTED
            self._health.state = ProviderState.DISCONNECTED
            self._stream_id = None

    def set_error(self, error: str):
        with self._lock:
            self._state = ProviderState.ERROR
            self._health.state = ProviderState.ERROR
            self._health.last_error = error
            self._health.failed_requests += 1
            self._health.consecutive_failures += 1

    def recover(self) -> bool:
        with self._lock:
            self._state = ProviderState.RECOVERING
            self._health.state = ProviderState.RECOVERING
            self._state = ProviderState.CONNECTED
            self._health.state = ProviderState.CONNECTED
            self._health.consecutive_failures = 0
            return True

    def snapshot(self):
        with self._lock:
            return {"provider_id": self._config.provider_id, "state": self._state.value,
                    "health": self._health.to_dict(), "config": self._config.to_dict(),
                    "stream_id": self._stream_id, "bytes_sent": self._bytes_sent,
                    "chunks_sent": self._chunks_sent}
