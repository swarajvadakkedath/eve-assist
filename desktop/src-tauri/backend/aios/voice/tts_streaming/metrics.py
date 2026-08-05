"""TTS Metrics — latency and throughput tracking for streaming TTS."""

from __future__ import annotations

import time
import threading
from collections import deque
from dataclasses import dataclass


@dataclass
class TTSMetricsSnapshot:
    timestamp: float
    uptime_seconds: float
    total_syntheses: int = 0
    total_chunks: int = 0
    total_played: int = 0
    total_dropped: int = 0
    total_bytes: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    first_word_latency_ms: float = 0.0
    provider_switches: int = 0
    recovery_events: int = 0
    failed_attempts: int = 0
    active_sessions: int = 0

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class TTSMetrics:
    def __init__(self, *, history_size: int = 1000):
        self._history_size = history_size
        self._created_at = time.monotonic()
        self._lock = threading.Lock()
        self._total_syntheses = 0
        self._total_chunks = 0
        self._total_played = 0
        self._total_dropped = 0
        self._total_bytes = 0
        self._latencies: deque[float] = deque(maxlen=history_size)
        self._first_word_latencies: deque[float] = deque(maxlen=history_size)
        self._provider_switches = 0
        self._recovery_events = 0
        self._failed_attempts = 0

    @property
    def uptime(self): return time.monotonic() - self._created_at

    def record_synthesis(self):
        with self._lock: self._total_syntheses += 1

    def record_chunk(self, size_bytes: int = 0):
        with self._lock:
            self._total_chunks += 1
            self._total_bytes += size_bytes

    def record_played(self):
        with self._lock: self._total_played += 1

    def record_dropped(self):
        with self._lock: self._total_dropped += 1

    def record_latency(self, latency_ms: float):
        with self._lock: self._latencies.append(latency_ms)

    def record_first_word_latency(self, latency_ms: float):
        with self._lock: self._first_word_latencies.append(latency_ms)

    def record_provider_switch(self):
        with self._lock: self._provider_switches += 1

    def record_recovery(self):
        with self._lock: self._recovery_events += 1

    def record_failure(self):
        with self._lock: self._failed_attempts += 1

    def snapshot(self, active_sessions=0):
        with self._lock:
            sorted_lat = sorted(self._latencies) if self._latencies else [0.0]
            p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
            avg_fwl = (sum(self._first_word_latencies) / len(self._first_word_latencies)
                      if self._first_word_latencies else 0.0)
            return TTSMetricsSnapshot(
                timestamp=time.monotonic(), uptime_seconds=self.uptime,
                total_syntheses=self._total_syntheses, total_chunks=self._total_chunks,
                total_played=self._total_played, total_dropped=self._total_dropped,
                total_bytes=self._total_bytes, avg_latency_ms=sum(sorted_lat) / len(sorted_lat),
                p95_latency_ms=sorted_lat[p95_idx], max_latency_ms=max(sorted_lat),
                first_word_latency_ms=avg_fwl, provider_switches=self._provider_switches,
                recovery_events=self._recovery_events, failed_attempts=self._failed_attempts,
                active_sessions=active_sessions)

    def reset(self):
        with self._lock:
            self._total_syntheses = 0; self._total_chunks = 0; self._total_played = 0
            self._total_dropped = 0; self._total_bytes = 0
            self._latencies.clear(); self._first_word_latencies.clear()
            self._provider_switches = 0; self._recovery_events = 0; self._failed_attempts = 0
            self._created_at = time.monotonic()
