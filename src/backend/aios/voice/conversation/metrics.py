"""Conversation Metrics — tracking for conversation quality and performance."""

from __future__ import annotations

import time
import threading
from collections import deque
from dataclasses import dataclass


@dataclass
class ConversationMetricsSnapshot:
    timestamp: float
    uptime_seconds: float
    total_conversations: int = 0
    total_turns: int = 0
    total_follow_ups: int = 0
    total_interruptions: int = 0
    total_timeouts: int = 0
    avg_turns_per_conversation: float = 0.0
    avg_response_latency_ms: float = 0.0
    p95_response_latency_ms: float = 0.0
    avg_conversation_duration_s: float = 0.0
    active_conversations: int = 0

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


class ConversationMetrics:
    def __init__(self, *, history_size: int = 1000):
        self._history_size = history_size
        self._created_at = time.monotonic()
        self._lock = threading.Lock()
        self._total_conversations = 0
        self._total_turns = 0
        self._total_follow_ups = 0
        self._total_interruptions = 0
        self._total_timeouts = 0
        self._response_latencies: deque[float] = deque(maxlen=history_size)
        self._conversation_durations: deque[float] = deque(maxlen=history_size)
        self._turns_per_conversation: deque[int] = deque(maxlen=history_size)

    @property
    def uptime(self): return time.monotonic() - self._created_at

    def record_conversation_start(self):
        with self._lock: self._total_conversations += 1

    def record_conversation_end(self, duration_s: float, turn_count: int):
        with self._lock:
            self._conversation_durations.append(duration_s)
            self._turns_per_conversation.append(turn_count)

    def record_turn(self, response_latency_ms: float = 0.0):
        with self._lock:
            self._total_turns += 1
            if response_latency_ms > 0:
                self._response_latencies.append(response_latency_ms)

    def record_follow_up(self):
        with self._lock: self._total_follow_ups += 1

    def record_interruption(self):
        with self._lock: self._total_interruptions += 1

    def record_timeout(self):
        with self._lock: self._total_timeouts += 1

    def snapshot(self, active_conversations=0):
        with self._lock:
            sorted_lat = sorted(self._response_latencies) if self._response_latencies else [0.0]
            p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)
            avg_tpc = (sum(self._turns_per_conversation) / len(self._turns_per_conversation)
                      if self._turns_per_conversation else 0.0)
            avg_dur = (sum(self._conversation_durations) / len(self._conversation_durations)
                      if self._conversation_durations else 0.0)
            return ConversationMetricsSnapshot(
                timestamp=time.monotonic(), uptime_seconds=self.uptime,
                total_conversations=self._total_conversations, total_turns=self._total_turns,
                total_follow_ups=self._total_follow_ups, total_interruptions=self._total_interruptions,
                total_timeouts=self._total_timeouts, avg_turns_per_conversation=avg_tpc,
                avg_response_latency_ms=sum(sorted_lat) / len(sorted_lat),
                p95_response_latency_ms=sorted_lat[p95_idx],
                avg_conversation_duration_s=avg_dur, active_conversations=active_conversations)

    def reset(self):
        with self._lock:
            self._total_conversations = 0; self._total_turns = 0
            self._total_follow_ups = 0; self._total_interruptions = 0; self._total_timeouts = 0
            self._response_latencies.clear(); self._conversation_durations.clear()
            self._turns_per_conversation.clear()
            self._created_at = time.monotonic()
