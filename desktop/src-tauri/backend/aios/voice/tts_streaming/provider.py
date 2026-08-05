"""TTS Provider — abstraction for text-to-text provider integration."""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .events import SpeechChunk


class TTSProviderState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNTHESIZING = "synthesizing"
    ERROR = "error"
    RECOVERING = "recovering"


@dataclass
class TTSProviderConfig:
    provider_id: str
    voice: str = "default"
    model: str = ""
    speed: float = 1.0
    sample_rate: int = 22050
    channels: int = 1
    sample_width: int = 2
    max_retries: int = 3
    retry_delay_s: float = 1.0
    timeout_s: float = 30.0
    priority: int = 100

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class TTSProviderHealth:
    provider_id: str
    state: TTSProviderState = TTSProviderState.DISCONNECTED
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    last_error: str = ""
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


class TTSProvider:
    """Abstract TTS provider wrapping SmartRouter integration."""

    def __init__(self, *, config=None):
        self._config = config or TTSProviderConfig(provider_id="default")
        self._state = TTSProviderState.DISCONNECTED
        self._health = TTSProviderHealth(provider_id=self._config.provider_id)
        self._lock = threading.Lock()

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
    def is_connected(self): return self._state in (TTSProviderState.CONNECTED, TTSProviderState.SYNTHESIZING)

    def connect(self) -> bool:
        with self._lock:
            self._state = TTSProviderState.CONNECTING
            self._health.state = TTSProviderState.CONNECTING
            self._state = TTSProviderState.CONNECTED
            self._health.state = TTSProviderState.CONNECTED
            self._health.consecutive_failures = 0
            return True

    def synthesize(self, text: str, voice: str = "", speed: float = 1.0) -> list[SpeechChunk]:
        """Synthesize text into audio chunks. Returns list of SpeechChunk."""
        if not self.is_connected:
            return []

        with self._lock:
            self._state = TTSProviderState.SYNTHESIZING
            self._health.state = TTSProviderState.SYNTHESIZING
            self._health.total_requests += 1

        # Simulate chunked synthesis
        chunks = []
        words = text.split()
        chunk_size = max(1, len(words) // 3) if len(words) > 3 else len(words)

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            # Simulate audio data (in real impl, this would be actual audio)
            audio_size = len(chunk_text) * 32  # Simulated bytes
            chunk = SpeechChunk(
                audio_data=b'\x00\x00' * (audio_size // 2),
                chunk_index=len(chunks),
                text=chunk_text,
                is_final=(i + chunk_size >= len(words)),
                sample_rate=self._config.sample_rate,
                channels=self._config.channels,
                sample_width=self._config.sample_width,
                duration_ms=(audio_size / (self._config.sample_rate * self._config.channels * self._config.sample_width)) * 1000,
                timestamp=time.monotonic(),
            )
            chunks.append(chunk)

        with self._lock:
            self._state = TTSProviderState.CONNECTED
            self._health.state = TTSProviderState.CONNECTED
            self._health.successful_requests += 1

        return chunks

    def synthesize_streaming(self, text: str, voice: str = "", speed: float = 1.0):
        """Generator that yields audio chunks as they're ready."""
        if not self.is_connected:
            return

        with self._lock:
            self._state = TTSProviderState.SYNTHESIZING
            self._health.state = TTSProviderState.SYNTHESIZING
            self._health.total_requests += 1

        words = text.split()
        chunk_size = max(1, len(words) // 4) if len(words) > 4 else len(words)

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            audio_size = len(chunk_text) * 32
            chunk = SpeechChunk(
                audio_data=b'\x00\x00' * (audio_size // 2),
                chunk_index=i // chunk_size,
                text=chunk_text,
                is_final=(i + chunk_size >= len(words)),
                sample_rate=self._config.sample_rate,
                channels=self._config.channels,
                sample_width=self._config.sample_width,
                duration_ms=(audio_size / (self._config.sample_rate * self._config.channels * self._config.sample_width)) * 1000,
                timestamp=time.monotonic(),
            )
            yield chunk

        with self._lock:
            self._state = TTSProviderState.CONNECTED
            self._health.state = TTSProviderState.CONNECTED
            self._health.successful_requests += 1

    def set_error(self, error: str):
        with self._lock:
            self._state = TTSProviderState.ERROR
            self._health.state = TTSProviderState.ERROR
            self._health.last_error = error
            self._health.failed_requests += 1
            self._health.consecutive_failures += 1

    def recover(self) -> bool:
        with self._lock:
            self._state = TTSProviderState.RECOVERING
            self._health.state = TTSProviderState.RECOVERING
            self._state = TTSProviderState.CONNECTED
            self._health.state = TTSProviderState.CONNECTED
            self._health.consecutive_failures = 0
            return True

    def disconnect(self):
        with self._lock:
            self._state = TTSProviderState.DISCONNECTED
            self._health.state = TTSProviderState.DISCONNECTED

    def snapshot(self):
        with self._lock:
            return {"provider_id": self._config.provider_id, "state": self._state.value,
                    "health": self._health.to_dict(), "config": self._config.to_dict()}
