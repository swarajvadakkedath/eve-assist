"""Stream Metrics — latency tracking and pipeline performance monitoring.

Tracks capture latency, buffer latency, routing latency, queue latency,
processing latency, and end-to-end latency. Designed for AIOps integration.
"""

from __future__ import annotations

import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LatencySnapshot:
    """Point-in-time latency measurement."""
    capture_ms: float = 0.0
    buffer_ms: float = 0.0
    routing_ms: float = 0.0
    queue_ms: float = 0.0
    processing_ms: float = 0.0
    end_to_end_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "capture_ms": round(self.capture_ms, 3),
            "buffer_ms": round(self.buffer_ms, 3),
            "routing_ms": round(self.routing_ms, 3),
            "queue_ms": round(self.queue_ms, 3),
            "processing_ms": round(self.processing_ms, 3),
            "end_to_end_ms": round(self.end_to_end_ms, 3),
        }


@dataclass
class StreamMetricsSnapshot:
    """Complete snapshot of streaming pipeline metrics."""
    timestamp: float
    uptime_seconds: float

    # Throughput
    chunks_created: int = 0
    chunks_delivered: int = 0
    chunks_dropped: int = 0
    chunks_lost: int = 0
    total_bytes_processed: int = 0

    # Rates (per second)
    chunks_per_second: float = 0.0
    bytes_per_second: float = 0.0

    # Latency averages
    avg_capture_ms: float = 0.0
    avg_buffer_ms: float = 0.0
    avg_routing_ms: float = 0.0
    avg_queue_ms: float = 0.0
    avg_processing_ms: float = 0.0
    avg_end_to_end_ms: float = 0.0

    # Latency percentiles
    p95_end_to_end_ms: float = 0.0
    p99_end_to_end_ms: float = 0.0
    max_end_to_end_ms: float = 0.0

    # Queue depth
    queue_depth: int = 0
    max_queue_depth: int = 0

    # Backpressure
    backpressure_events: int = 0
    recovery_events: int = 0

    # Active sessions
    active_sessions: int = 0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "chunks_created": self.chunks_created,
            "chunks_delivered": self.chunks_delivered,
            "chunks_dropped": self.chunks_dropped,
            "chunks_lost": self.chunks_lost,
            "total_bytes_processed": self.total_bytes_processed,
            "chunks_per_second": round(self.chunks_per_second, 2),
            "bytes_per_second": round(self.bytes_per_second, 2),
            "avg_capture_ms": round(self.avg_capture_ms, 3),
            "avg_buffer_ms": round(self.avg_buffer_ms, 3),
            "avg_routing_ms": round(self.avg_routing_ms, 3),
            "avg_queue_ms": round(self.avg_queue_ms, 3),
            "avg_processing_ms": round(self.avg_processing_ms, 3),
            "avg_end_to_end_ms": round(self.avg_end_to_end_ms, 3),
            "p95_end_to_end_ms": round(self.p95_end_to_end_ms, 3),
            "p99_end_to_end_ms": round(self.p99_end_to_end_ms, 3),
            "max_end_to_end_ms": round(self.max_end_to_end_ms, 3),
            "queue_depth": self.queue_depth,
            "max_queue_depth": self.max_queue_depth,
            "backpressure_events": self.backpressure_events,
            "recovery_events": self.recovery_events,
            "active_sessions": self.active_sessions,
        }


class StreamMetrics:
    """Collects and reports streaming pipeline metrics.

    Thread-safe metrics collector that tracks throughput, latency,
    queue depth, and backpressure events. Designed for real-time
    monitoring and AIOps integration.

    Args:
        history_size: Number of latency readings to keep for percentile calculation.
        rate_window_seconds: Window for computing throughput rates.
    """

    def __init__(
        self,
        *,
        history_size: int = 1000,
        rate_window_seconds: float = 5.0,
    ):
        self._history_size = history_size
        self._rate_window = rate_window_seconds
        self._created_at = time.monotonic()
        self._lock = threading.Lock()

        # Counters
        self._chunks_created = 0
        self._chunks_delivered = 0
        self._chunks_dropped = 0
        self._chunks_lost = 0
        self._total_bytes = 0

        # Latency histories (circular buffer)
        self._capture_latencies: deque[float] = deque(maxlen=history_size)
        self._buffer_latencies: deque[float] = deque(maxlen=history_size)
        self._routing_latencies: deque[float] = deque(maxlen=history_size)
        self._queue_latencies: deque[float] = deque(maxlen=history_size)
        self._processing_latencies: deque[float] = deque(maxlen=history_size)
        self._end_to_end_latencies: deque[float] = deque(maxlen=history_size)

        # Throughput tracking
        self._recent_chunk_times: deque[float] = deque(maxlen=history_size)
        self._recent_byte_sizes: deque[tuple[float, int]] = deque(maxlen=history_size)

        # Queue depth
        self._queue_depth = 0
        self._max_queue_depth = 0

        # Events
        self._backpressure_events = 0
        self._recovery_events = 0

    @property
    def uptime(self) -> float:
        return time.monotonic() - self._created_at

    def record_chunk_created(self, size_bytes: int) -> None:
        """Record a chunk being created."""
        now = time.monotonic()
        with self._lock:
            self._chunks_created += 1
            self._total_bytes += size_bytes
            self._recent_chunk_times.append(now)
            self._recent_byte_sizes.append((now, size_bytes))

    def record_chunk_delivered(self) -> None:
        """Record a chunk being delivered to a consumer."""
        with self._lock:
            self._chunks_delivered += 1

    def record_chunk_dropped(self) -> None:
        """Record a chunk being dropped (overflow/backpressure)."""
        with self._lock:
            self._chunks_dropped += 1

    def record_chunk_lost(self) -> None:
        """Record a chunk being lost (gap in sequence)."""
        with self._lock:
            self._chunks_lost += 1

    def record_latency(self, stage: str, latency_ms: float) -> None:
        """Record a latency measurement for a pipeline stage.

        Args:
            stage: One of 'capture', 'buffer', 'routing', 'queue', 'processing', 'end_to_end'.
            latency_ms: Latency in milliseconds.
        """
        with self._lock:
            if stage == "capture":
                self._capture_latencies.append(latency_ms)
            elif stage == "buffer":
                self._buffer_latencies.append(latency_ms)
            elif stage == "routing":
                self._routing_latencies.append(latency_ms)
            elif stage == "queue":
                self._queue_latencies.append(latency_ms)
            elif stage == "processing":
                self._processing_latencies.append(latency_ms)
            elif stage == "end_to_end":
                self._end_to_end_latencies.append(latency_ms)

    def record_backpressure(self) -> None:
        """Record a backpressure event."""
        with self._lock:
            self._backpressure_events += 1

    def record_recovery(self) -> None:
        """Record a recovery event."""
        with self._lock:
            self._recovery_events += 1

    def update_queue_depth(self, depth: int) -> None:
        """Update current queue depth."""
        with self._lock:
            self._queue_depth = depth
            if depth > self._max_queue_depth:
                self._max_queue_depth = depth

    def _percentile(self, data: deque[float], pct: float) -> float:
        """Compute percentile from a deque of values."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * pct / 100)
        idx = min(idx, len(sorted_data) - 1)
        return sorted_data[idx]

    def _average(self, data: deque[float]) -> float:
        """Compute average from a deque of values."""
        if not data:
            return 0.0
        return sum(data) / len(data)

    def _throughput_rate(self) -> tuple[float, float]:
        """Compute chunks/sec and bytes/sec over the rate window."""
        now = time.monotonic()
        cutoff = now - self._rate_window

        chunks_in_window = sum(1 for t in self._recent_chunk_times if t >= cutoff)
        bytes_in_window = sum(s for t, s in self._recent_byte_sizes if t >= cutoff)

        rate = chunks_in_window / self._rate_window if self._rate_window > 0 else 0.0
        byte_rate = bytes_in_window / self._rate_window if self._rate_window > 0 else 0.0

        return (rate, byte_rate)

    def snapshot(self, active_sessions: int = 0) -> StreamMetricsSnapshot:
        """Take a snapshot of all metrics."""
        with self._lock:
            chunk_rate, byte_rate = self._throughput_rate()

            return StreamMetricsSnapshot(
                timestamp=time.monotonic(),
                uptime_seconds=self.uptime,
                chunks_created=self._chunks_created,
                chunks_delivered=self._chunks_delivered,
                chunks_dropped=self._chunks_dropped,
                chunks_lost=self._chunks_lost,
                total_bytes_processed=self._total_bytes,
                chunks_per_second=chunk_rate,
                bytes_per_second=byte_rate,
                avg_capture_ms=self._average(self._capture_latencies),
                avg_buffer_ms=self._average(self._buffer_latencies),
                avg_routing_ms=self._average(self._routing_latencies),
                avg_queue_ms=self._average(self._queue_latencies),
                avg_processing_ms=self._average(self._processing_latencies),
                avg_end_to_end_ms=self._average(self._end_to_end_latencies),
                p95_end_to_end_ms=self._percentile(self._end_to_end_latencies, 95),
                p99_end_to_end_ms=self._percentile(self._end_to_end_latencies, 99),
                max_end_to_end_ms=max(self._end_to_end_latencies) if self._end_to_end_latencies else 0.0,
                queue_depth=self._queue_depth,
                max_queue_depth=self._max_queue_depth,
                backpressure_events=self._backpressure_events,
                recovery_events=self._recovery_events,
                active_sessions=active_sessions,
            )

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._chunks_created = 0
            self._chunks_delivered = 0
            self._chunks_dropped = 0
            self._chunks_lost = 0
            self._total_bytes = 0
            self._capture_latencies.clear()
            self._buffer_latencies.clear()
            self._routing_latencies.clear()
            self._queue_latencies.clear()
            self._processing_latencies.clear()
            self._end_to_end_latencies.clear()
            self._recent_chunk_times.clear()
            self._recent_byte_sizes.clear()
            self._queue_depth = 0
            self._max_queue_depth = 0
            self._backpressure_events = 0
            self._recovery_events = 0
            self._created_at = time.monotonic()
