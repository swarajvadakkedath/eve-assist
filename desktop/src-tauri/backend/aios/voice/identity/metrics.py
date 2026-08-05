"""Identity Metrics — tracking for voice identity system."""

from __future__ import annotations

import time
import threading
from collections import deque
from dataclasses import dataclass


@dataclass
class IdentityMetricsSnapshot:
    """Snapshot of identity metrics."""
    timestamp: float
    uptime_seconds: float
    total_adaptations: int = 0
    context_switches: int = 0
    profile_changes: int = 0
    pronunciation_lookups: int = 0
    preference_updates: int = 0
    avg_adaptation_latency_ms: float = 0.0
    p95_adaptation_latency_ms: float = 0.0
    adaptations_today: int = 0
    current_profile: str = "friendly"
    current_context: str = "general"

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class IdentityMetrics:
    """Thread-safe metrics for the identity system."""
    def __init__(self, *, history_size: int = 1000):
        self._history_size = history_size
        self._created_at = time.monotonic()
        self._lock = threading.Lock()
        self._total_adaptations = 0
        self._context_switches = 0
        self._profile_changes = 0
        self._pronunciation_lookups = 0
        self._preference_updates = 0
        self._adaptation_latencies: deque[float] = deque(maxlen=history_size)
        self._adaptations_today = 0
        self._last_adaptation_date = ""

    @property
    def uptime(self) -> float:
        return time.monotonic() - self._created_at

    def record_adaptation(self, latency_ms: float):
        with self._lock:
            self._total_adaptations += 1
            self._adaptation_latencies.append(latency_ms)
            today = time.strftime("%Y-%m-%d")
            if self._last_adaptation_date != today:
                self._adaptations_today = 0
                self._last_adaptation_date = today
            self._adaptations_today += 1

    def record_context_switch(self):
        with self._lock:
            self._context_switches += 1

    def record_profile_change(self):
        with self._lock:
            self._profile_changes += 1

    def record_pronunciation_lookup(self):
        with self._lock:
            self._pronunciation_lookups += 1

    def record_preference_update(self):
        with self._lock:
            self._preference_updates += 1

    def snapshot(self, *, current_profile: str = "friendly",
                 current_context: str = "general") -> IdentityMetricsSnapshot:
        with self._lock:
            sorted_lat = sorted(self._adaptation_latencies) if self._adaptation_latencies else [0.0]
            p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
            return IdentityMetricsSnapshot(
                timestamp=time.monotonic(), uptime_seconds=self.uptime,
                total_adaptations=self._total_adaptations,
                context_switches=self._context_switches,
                profile_changes=self._profile_changes,
                pronunciation_lookups=self._pronunciation_lookups,
                preference_updates=self._preference_updates,
                avg_adaptation_latency_ms=sum(sorted_lat) / len(sorted_lat),
                p95_adaptation_latency_ms=sorted_lat[p95_idx],
                adaptations_today=self._adaptations_today,
                current_profile=current_profile,
                current_context=current_context)

    def reset(self):
        with self._lock:
            self._total_adaptations = 0; self._context_switches = 0
            self._profile_changes = 0; self._pronunciation_lookups = 0
            self._preference_updates = 0
            self._adaptation_latencies.clear()
            self._adaptations_today = 0; self._created_at = time.monotonic()
