"""Transcript Metrics — latency and throughput tracking for streaming STT."""

from __future__ import annotations

import time
import threading
from collections import deque
from dataclasses import dataclass


@dataclass
class TranscriptMetricsSnapshot:
    timestamp: float
    uptime_seconds: float
    total_partials: int = 0
    total_finals: int = 0
    total_words: int = 0
    avg_confidence: float = 0.0
    words_per_second: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    provider_switches: int = 0
    recovery_events: int = 0
    failed_attempts: int = 0
    active_sessions: int = 0

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class TranscriptMetrics:
    def __init__(self, *, history_size: int = 1000):
        self._history_size = history_size
        self._created_at = time.monotonic()
        self._lock = threading.Lock()
        self._total_partials = 0
        self._total_finals = 0
        self._total_words = 0
        self._confidence_sum = 0.0
        self._confidence_count = 0
        self._latencies: deque[float] = deque(maxlen=history_size)
        self._word_times: deque[tuple[float, int]] = deque(maxlen=history_size)
        self._provider_switches = 0
        self._recovery_events = 0
        self._failed_attempts = 0

    @property
    def uptime(self): return time.monotonic() - self._created_at

    def record_partial(self, text, confidence=0.0):
        with self._lock:
            self._total_partials += 1
            words = len(text.split()) if text else 0
            self._total_words += words
            self._word_times.append((time.monotonic(), words))
            if confidence > 0:
                self._confidence_sum += confidence
                self._confidence_count += 1

    def record_final(self, text, confidence=0.0):
        with self._lock:
            self._total_finals += 1
            words = len(text.split()) if text else 0
            self._total_words += words
            self._word_times.append((time.monotonic(), words))
            if confidence > 0:
                self._confidence_sum += confidence
                self._confidence_count += 1

    def record_latency(self, latency_ms):
        with self._lock: self._latencies.append(latency_ms)

    def record_provider_switch(self):
        with self._lock: self._provider_switches += 1

    def record_recovery(self):
        with self._lock: self._recovery_events += 1

    def record_failure(self):
        with self._lock: self._failed_attempts += 1

    def _wps(self):
        now = time.monotonic()
        cutoff = now - 5.0
        total_w = sum(w for t, w in self._word_times if t >= cutoff)
        return total_w / 5.0 if self._word_times else 0.0

    def snapshot(self, active_sessions=0):
        with self._lock:
            avg_conf = self._confidence_sum / self._confidence_count if self._confidence_count > 0 else 0.0
            sorted_lat = sorted(self._latencies) if self._latencies else [0.0]
            p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
            return TranscriptMetricsSnapshot(
                timestamp=time.monotonic(), uptime_seconds=self.uptime,
                total_partials=self._total_partials, total_finals=self._total_finals,
                total_words=self._total_words, avg_confidence=avg_conf, words_per_second=self._wps(),
                avg_latency_ms=sum(sorted_lat) / len(sorted_lat), p95_latency_ms=sorted_lat[p95_idx],
                max_latency_ms=max(sorted_lat), provider_switches=self._provider_switches,
                recovery_events=self._recovery_events, failed_attempts=self._failed_attempts,
                active_sessions=active_sessions)

    def reset(self):
        with self._lock:
            self._total_partials = 0; self._total_finals = 0; self._total_words = 0
            self._confidence_sum = 0.0; self._confidence_count = 0
            self._latencies.clear(); self._word_times.clear()
            self._provider_switches = 0; self._recovery_events = 0; self._failed_attempts = 0
            self._created_at = time.monotonic()
