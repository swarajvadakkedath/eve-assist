"""Stream Router — routes audio chunks to multiple consumers.

The router implements a pub/sub pattern where consumers subscribe
to receive chunks independently. Each consumer gets its own copy
of every chunk with independent queue management.
"""

from __future__ import annotations

import asyncio
import collections
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .chunk import AudioChunk, ChunkStatus


class ConsumerState(Enum):
    """Consumer subscription state."""
    ACTIVE = "active"
    PAUSED = "paused"
    DRAINING = "draining"
    UNSUBSCRIBED = "unsubscribed"


class DropPolicy(Enum):
    """How to handle queue overflow."""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    BLOCK = "block"
    ERROR = "error"


@dataclass
class ConsumerInfo:
    """Information about a registered consumer."""
    consumer_id: str
    state: ConsumerState
    queue_size: int
    max_queue_size: int
    chunks_received: int = 0
    chunks_dropped: int = 0
    last_chunk_time: float = 0.0

    def to_dict(self) -> dict:
        return {
            "consumer_id": self.consumer_id,
            "state": self.state.value,
            "queue_size": self.queue_size,
            "max_queue_size": self.max_queue_size,
            "chunks_received": self.chunks_received,
            "chunks_dropped": self.chunks_dropped,
            "last_chunk_time": self.last_chunk_time,
        }


@dataclass
class _Consumer:
    """Internal consumer state."""
    consumer_id: str
    handler: Callable[[AudioChunk], None]
    max_queue_size: int
    drop_policy: DropPolicy
    state: ConsumerState = ConsumerState.ACTIVE
    queue: collections.deque = field(default_factory=lambda: collections.deque())
    chunks_received: int = 0
    chunks_dropped: int = 0
    last_chunk_time: float = 0.0


class StreamRouter:
    """Routes audio chunks to multiple consumers.

    Each consumer subscribes with a handler callback and receives
    independent copies of chunks. Supports configurable queue sizes,
    drop policies, and backpressure.

    Args:
        default_max_queue: Default maximum queue size per consumer.
        default_drop_policy: Default drop policy on overflow.
    """

    def __init__(
        self,
        *,
        default_max_queue: int = 100,
        default_drop_policy: DropPolicy = DropPolicy.DROP_OLDEST,
    ):
        self._default_max_queue = default_max_queue
        self._default_drop_policy = default_drop_policy
        self._consumers: dict[str, _Consumer] = {}
        self._lock = threading.Lock()
        self._total_chunks_routed = 0
        self._total_chunks_dropped = 0

    @property
    def consumer_count(self) -> int:
        """Number of registered consumers."""
        with self._lock:
            return len(self._consumers)

    @property
    def total_chunks_routed(self) -> int:
        return self._total_chunks_routed

    @property
    def total_chunks_dropped(self) -> int:
        return self._total_chunks_dropped

    def subscribe(
        self,
        consumer_id: str,
        handler: Callable[[AudioChunk], None],
        *,
        max_queue_size: Optional[int] = None,
        drop_policy: Optional[DropPolicy] = None,
    ) -> bool:
        """Subscribe a consumer to receive chunks.

        Args:
            consumer_id: Unique consumer identifier.
            handler: Callback invoked with each AudioChunk.
            max_queue_size: Maximum queued chunks before applying drop policy.
            drop_policy: How to handle queue overflow.

        Returns:
            True if subscription was successful.
        """
        with self._lock:
            if consumer_id in self._consumers:
                return False

            self._consumers[consumer_id] = _Consumer(
                consumer_id=consumer_id,
                handler=handler,
                max_queue_size=max_queue_size or self._default_max_queue,
                drop_policy=drop_policy or self._default_drop_policy,
            )
            return True

    def unsubscribe(self, consumer_id: str) -> bool:
        """Unsubscribe a consumer.

        Returns:
            True if consumer was found and removed.
        """
        with self._lock:
            if consumer_id not in self._consumers:
                return False
            self._consumers[consumer_id].state = ConsumerState.UNSUBSCRIBED
            self._consumers[consumer_id].queue.clear()
            del self._consumers[consumer_id]
            return True

    def pause_consumer(self, consumer_id: str) -> bool:
        """Pause a consumer (stops receiving chunks)."""
        with self._lock:
            consumer = self._consumers.get(consumer_id)
            if not consumer:
                return False
            consumer.state = ConsumerState.PAUSED
            return True

    def resume_consumer(self, consumer_id: str) -> bool:
        """Resume a paused consumer."""
        with self._lock:
            consumer = self._consumers.get(consumer_id)
            if not consumer:
                return False
            consumer.state = ConsumerState.ACTIVE
            return True

    def route(self, chunk: AudioChunk) -> dict[str, bool]:
        """Route a chunk to all active consumers.

        Chunks are queued for delivery. Call deliver() to process the queue.
        Returns dict mapping consumer_id to queue success.
        """
        results = {}
        with self._lock:
            for cid, consumer in self._consumers.items():
                if consumer.state == ConsumerState.UNSUBSCRIBED:
                    results[cid] = False
                    continue

                if consumer.state == ConsumerState.PAUSED:
                    results[cid] = False
                    continue

                # Check queue capacity
                if len(consumer.queue) >= consumer.max_queue_size:
                    dropped = self._apply_drop_policy(consumer, chunk)
                    if dropped:
                        results[cid] = False
                        self._total_chunks_dropped += 1
                        continue

                # Queue chunk for delivery
                consumer.queue.append(chunk)
                consumer.chunks_received += 1
                consumer.last_chunk_time = time.monotonic()
                self._total_chunks_routed += 1
                results[cid] = True

        return results

    def deliver(self) -> int:
        """Deliver all queued chunks to consumers.

        Returns number of chunks delivered.
        """
        delivered = 0
        with self._lock:
            consumers_snapshot = [
                (cid, consumer) for cid, consumer in self._consumers.items()
                if consumer.queue
            ]

        for cid, consumer in consumers_snapshot:
            while consumer.queue:
                try:
                    chunk_to_deliver = consumer.queue.popleft()
                    consumer.handler(chunk_to_deliver)
                    delivered += 1
                except Exception:
                    pass

        return delivered

    def _apply_drop_policy(self, consumer: _Consumer, new_chunk: AudioChunk) -> bool:
        """Apply drop policy when queue is full.

        Returns True if the new chunk should be dropped.
        """
        if consumer.drop_policy == DropPolicy.DROP_OLDEST:
            if consumer.queue:
                consumer.queue.popleft()
                consumer.chunks_dropped += 1
                return False  # New chunk can be added
            return True

        elif consumer.drop_policy == DropPolicy.DROP_NEWEST:
            consumer.chunks_dropped += 1
            return True  # Drop the new chunk

        elif consumer.drop_policy == DropPolicy.BLOCK:
            # In blocking mode, we don't drop — but we've already exceeded limit
            # Return True to indicate queue is full (caller should handle)
            return True

        elif consumer.drop_policy == DropPolicy.ERROR:
            consumer.chunks_dropped += 1
            return True

        return True

    def consumer_info(self, consumer_id: str) -> Optional[ConsumerInfo]:
        """Get info about a specific consumer."""
        with self._lock:
            consumer = self._consumers.get(consumer_id)
            if not consumer:
                return None
            return ConsumerInfo(
                consumer_id=consumer.consumer_id,
                state=consumer.state,
                queue_size=len(consumer.queue),
                max_queue_size=consumer.max_queue_size,
                chunks_received=consumer.chunks_received,
                chunks_dropped=consumer.chunks_dropped,
                last_chunk_time=consumer.last_chunk_time,
            )

    def all_consumer_info(self) -> list[ConsumerInfo]:
        """Get info about all consumers."""
        with self._lock:
            return [
                ConsumerInfo(
                    consumer_id=c.consumer_id,
                    state=c.state,
                    queue_size=len(c.queue),
                    max_queue_size=c.max_queue_size,
                    chunks_received=c.chunks_received,
                    chunks_dropped=c.chunks_dropped,
                    last_chunk_time=c.last_chunk_time,
                )
                for c in self._consumers.values()
            ]

    def stats(self) -> dict:
        """Get router statistics."""
        with self._lock:
            return {
                "consumer_count": len(self._consumers),
                "total_chunks_routed": self._total_chunks_routed,
                "total_chunks_dropped": self._total_chunks_dropped,
                "default_max_queue": self._default_max_queue,
                "default_drop_policy": self._default_drop_policy.value,
            }

    def reset(self) -> None:
        """Reset router state and clear all consumers."""
        with self._lock:
            self._consumers.clear()
            self._total_chunks_routed = 0
            self._total_chunks_dropped = 0
