"""Wake Word Metrics — tracking for wake word detection performance."""

from __future__ import annotations

import time
import threading
from collections import deque
from dataclasses import dataclass


@dataclass
class WakeWordMetricsSnapshot:
    """Snapshot of wake word metrics at a point in time."""
    timestamp: float
    uptime_seconds: float
    total_detections: int = 0
    successful_detections: int = 0
    false_positives: int = 0
    rejected_detections: int = 0
    timeouts: int = 0
    sessions_started: int = 0
    sessions_ended: int = 0
    avg_detection_latency_ms: float = 0.0
    p95_detection_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    activations_today: int = 0
    current_threshold: float = 0.5
    current_sensitivity: str = "medium"

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class WakeWordMetrics:
    """Thread-safe metrics collection for wake word detection."""
    def __init__(self, *, history_size: int = 1000):
        self._history_size = history_size
        self._created_at = time.monotonic()
        self._lock = threading.Lock()
        self._total_detections = 0
        self._successful_detections = 0
        self._false_positives = 0
        self._rejected_detections = 0
        self._timeouts = 0
        self._sessions_started = 0
        self._sessions_ended = 0
        self._detection_latencies: deque[float] = deque(maxlen=history_size)
        self._confidences: deque[float] = deque(maxlen=history_size)
        self._activations_today = 0
        self._last_activation_date = ""

    @property
    def uptime(self) -> float:
        return time.monotonic() - self._created_at

    def record_detection(self, latency_ms: float, confidence: float, success: bool = True):
        with self._lock:
            self._total_detections += 1
            if success:
                self._successful_detections += 1
            self._detection_latencies.append(latency_ms)
            self._confidences.append(confidence)

    def record_false_positive(self):
        with self._lock:
            self._false_positives += 1

    def record_rejection(self):
        with self._lock:
            self._rejected_detections += 1

    def record_timeout(self):
        with self._lock:
            self._timeouts += 1

    def record_session_start(self):
        with self._lock:
            self._sessions_started += 1

    def record_session_end(self):
        with self._lock:
            self._sessions_ended += 1

    def record_activation(self):
        with self._lock:
            today = time.strftime("%Y-%m-%d")
            if self._last_activation_date != today:
                self._activations_today = 0
                self._last_activation_date = today
            self._activations_today += 1

    def snapshot(self, *, current_threshold: float = 0.5,
                 current_sensitivity: str = "medium") -> WakeWordMetricsSnapshot:
        with self._lock:
            sorted_lat = sorted(self._detection_latencies) if self._detection_latencies else [0.0]
            p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
            avg_conf = (sum(self._confidences) / len(self._confidences)
                       if self._confidences else 0.0)
            return WakeWordMetricsSnapshot(
                timestamp=time.monotonic(), uptime_seconds=self.uptime,
                total_detections=self._total_detections,
                successful_detections=self._successful_detections,
                false_positives=self._false_positives,
                rejected_detections=self._rejected_detections,
                timeouts=self._timeouts,
                sessions_started=self._sessions_started,
                sessions_ended=self._sessions_ended,
                avg_detection_latency_ms=sum(sorted_lat) / len(sorted_lat),
                p95_detection_latency_ms=sorted_lat[p95_idx],
                avg_confidence=avg_conf,
                activations_today=self._activations_today,
                current_threshold=current_threshold,
                current_sensitivity=current_sensitivity)

    def reset(self):
        with self._lock:
            self._total_detections = 0; self._successful_detections = 0
            self._false_positives = 0; self._rejected_detections = 0
            self._timeouts = 0; self._sessions_started = 0; self._sessions_ended = 0
            self._detection_latencies.clear(); self._confidences.clear()
            self._activations_today = 0; self._created_at = time.monotonic()
