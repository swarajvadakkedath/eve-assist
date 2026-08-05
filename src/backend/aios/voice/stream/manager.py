"""Speech Stream Manager — orchestrates the real-time speech pipeline.

The manager is the single entry point for the streaming layer. It connects
the audio engine output to the VAD/listening intelligence and routes chunks
to consumers (future STT, wake word, recorder, diagnostics).
"""

from __future__ import annotations

import asyncio
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .chunk import AudioChunk, ChunkGenerator, ChunkStatus
from .metrics import StreamMetrics
from .session import SpeechSession, SessionState, SessionEvent
from .router import StreamRouter, DropPolicy, ConsumerState


class StreamEventType(Enum):
    """Events published by the manager."""
    STREAM_STARTED = "stream_started"
    STREAM_STOPPED = "stream_stopped"
    CHUNK_CREATED = "chunk_created"
    CHUNK_DROPPED = "chunk_dropped"
    LATENCY_WARNING = "latency_warning"
    BACKPRESSURE_DETECTED = "backpressure_detected"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_FINISHED = "recovery_finished"


@dataclass
class StreamConfig:
    """Configuration for the streaming pipeline."""
    chunk_size_ms: int = 30
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2
    max_queue_depth: int = 100
    max_latency_ms: float = 100.0
    recovery_timeout_s: float = 5.0
    drop_policy: DropPolicy = DropPolicy.DROP_OLDEST
    silence_timeout: float = 1.5
    max_speech_duration: float = 300.0

    def to_dict(self) -> dict:
        return {
            "chunk_size_ms": self.chunk_size_ms,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "sample_width": self.sample_width,
            "max_queue_depth": self.max_queue_depth,
            "max_latency_ms": self.max_latency_ms,
            "recovery_timeout_s": self.recovery_timeout_s,
            "drop_policy": self.drop_policy.value,
            "silence_timeout": self.silence_timeout,
            "max_speech_duration": self.max_speech_duration,
        }


class SpeechStreamManager:
    """Orchestrates the real-time speech pipeline.

    Connects audio capture to chunking, routing, and session management.
    This is the single entry point for the streaming layer.

    Args:
        config: Pipeline configuration.
    """

    def __init__(self, *, config: Optional[StreamConfig] = None):
        self._config = config or StreamConfig()
        self._state = "idle"
        self._created_at = time.monotonic()

        # Core components
        self._chunk_generator = ChunkGenerator(
            chunk_size_ms=self._config.chunk_size_ms,
            sample_rate=self._config.sample_rate,
            channels=self._config.channels,
            sample_width=self._config.sample_width,
        )
        self._metrics = StreamMetrics(history_size=2000)
        self._router = StreamRouter(
            default_max_queue=self._config.max_queue_depth,
            default_drop_policy=self._config.drop_policy,
        )

        # Session tracking
        self._sessions: dict[str, SpeechSession] = {}
        self._active_session: Optional[SpeechSession] = None

        # Event handlers
        self._event_handlers: dict[StreamEventType, list[Callable]] = {}

        # Backpressure
        self._total_chunks_fed = 0
        self._total_chunks_generated = 0
        self._latency_warnings = 0

        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        return self._state

    @property
    def config(self) -> StreamConfig:
        return self._config

    @property
    def metrics(self) -> StreamMetrics:
        return self._metrics

    @property
    def router(self) -> StreamRouter:
        return self._router

    @property
    def active_session(self) -> Optional[SpeechSession]:
        return self._active_session

    def on(self, event: StreamEventType, handler: Callable) -> None:
        """Subscribe to a manager event."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: StreamEventType, handler: Callable) -> None:
        """Unsubscribe from a manager event."""
        if event in self._event_handlers:
            self._event_handlers[event] = [
                h for h in self._event_handlers[event] if h != handler
            ]

    async def _emit(self, event: StreamEventType, data: dict) -> None:
        """Emit a manager event."""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, data)
                else:
                    handler(event, data)
            except Exception:
                pass

    def _emit_sync(self, event: StreamEventType, data: dict) -> None:
        """Emit event synchronously (safe without event loop)."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._emit(event, data))
        except RuntimeError:
            # No event loop — call handlers directly
            for handler in self._event_handlers.get(event, []):
                try:
                    handler(event, data)
                except Exception:
                    pass

    def start(self, session_id: str = "") -> SpeechSession:
        """Start a new streaming session.

        Args:
            session_id: Optional session identifier.

        Returns:
            The created session.
        """
        with self._lock:
            # Create session
            session = SpeechSession(
                session_id=session_id,
                silence_timeout=self._config.silence_timeout,
                max_speech_duration=self._config.max_speech_duration,
            )
            session.open()
            session.start_streaming()

            self._sessions[session.id] = session
            self._active_session = session
            self._state = "streaming"

        self._emit_sync(StreamEventType.STREAM_STARTED, {
            "session_id": session.id,
            "config": self._config.to_dict(),
        })

        return session

    def stop(self) -> None:
        """Stop the current streaming session."""
        with self._lock:
            if self._active_session:
                self._active_session.close()
                session_id = self._active_session.id
                self._active_session = None
            else:
                session_id = ""

            self._state = "idle"

        self._emit_sync(StreamEventType.STREAM_STOPPED, {
            "session_id": session_id,
        })

    def feed_audio(self, data: bytes) -> list[AudioChunk]:
        """Feed raw PCM audio data into the pipeline.

        Chunks are generated, routed to consumers, and tracked.
        Returns list of chunks that were created.
        """
        if self._state != "streaming":
            return []

        with self._lock:
            self._total_chunks_fed += len(data)

        # Generate chunks
        chunks = self._chunk_generator.feed(data)

        for chunk in chunks:
            self._total_chunks_generated += 1
            self._metrics.record_chunk_created(chunk.size_bytes)

            # Track in active session
            if self._active_session:
                self._active_session.receive_chunk(chunk)

            # Check backpressure
            self._check_backpressure()

            # Route to consumers
            results = self._router.route(chunk)

            # Deliver queued chunks
            self._router.deliver()

            # Record delivery results
            for cid, delivered in results.items():
                if delivered:
                    self._metrics.record_chunk_delivered()
                    if self._active_session:
                        self._active_session.process_chunk(chunk)
                else:
                    self._metrics.record_chunk_dropped()
                    chunk.mark_dropped(reason="queue_full")
                    self._emit_sync(StreamEventType.CHUNK_DROPPED, {
                        "consumer": cid,
                        "sequence": chunk.sequence,
                    })

            # Emit chunk created event
            self._emit_sync(StreamEventType.CHUNK_CREATED, {
                "sequence": chunk.sequence,
                "size": chunk.size_bytes,
            })

        return chunks

    def feed_audio_bytes(self, data: bytes) -> list[AudioChunk]:
        """Alias for feed_audio for API consistency."""
        return self.feed_audio(data)

    def _check_backpressure(self) -> None:
        """Check for backpressure conditions."""
        info = self._router.all_consumer_info()
        for consumer in info:
            if consumer.queue_size > consumer.max_queue_size * 0.8:
                self._latency_warnings += 1
                self._metrics.record_backpressure()
                self._emit_sync(StreamEventType.BACKPRESSURE_DETECTED, {
                    "consumer": consumer.consumer_id,
                    "queue_size": consumer.queue_size,
                    "max_queue": consumer.max_queue_size,
                })
                break

    def flush(self) -> Optional[AudioChunk]:
        """Flush remaining buffer as partial chunk."""
        chunk = self._chunk_generator.flush()
        if chunk and self._active_session:
            self._active_session.receive_chunk(chunk)
            self._router.route(chunk)
            self._metrics.record_chunk_created(chunk.size_bytes)
        return chunk

    def subscribe_consumer(
        self,
        consumer_id: str,
        handler: Callable[[AudioChunk], None],
        *,
        max_queue_size: Optional[int] = None,
        drop_policy: Optional[DropPolicy] = None,
    ) -> bool:
        """Subscribe a consumer to receive chunks."""
        return self._router.subscribe(
            consumer_id,
            handler,
            max_queue_size=max_queue_size,
            drop_policy=drop_policy,
        )

    def unsubscribe_consumer(self, consumer_id: str) -> bool:
        """Unsubscribe a consumer."""
        return self._router.unsubscribe(consumer_id)

    def pause(self) -> bool:
        """Pause the active session."""
        with self._lock:
            if self._active_session:
                result = self._active_session.pause()
                if result:
                    self._state = "paused"
                return result
        return False

    def resume(self) -> bool:
        """Resume the active session."""
        with self._lock:
            if self._active_session:
                result = self._active_session.resume()
                if result:
                    self._state = "streaming"
                return result
        return False

    def recover(self) -> bool:
        """Begin recovery from error."""
        with self._lock:
            if self._active_session:
                self._emit_sync(StreamEventType.RECOVERY_STARTED, {
                    "session_id": self._active_session.id,
                })
                return self._active_session.recover()
        return False

    def finish_recovery(self) -> bool:
        """Complete recovery."""
        with self._lock:
            if self._active_session:
                result = self._active_session.finish_recovery()
                if result:
                    self._state = "streaming"
                self._emit_sync(StreamEventType.RECOVERY_FINISHED, {
                    "session_id": self._active_session.id,
                })
                return result
        return False

    def snapshot(self) -> dict:
        """Get a complete snapshot of the streaming pipeline state."""
        metrics_snap = self._metrics.snapshot(
            active_sessions=len([s for s in self._sessions.values() if s.is_active])
        )

        session_stats = None
        if self._active_session:
            session_stats = self._active_session.stats().to_dict()

        return {
            "state": self._state,
            "config": self._config.to_dict(),
            "session": session_stats,
            "metrics": metrics_snap.to_dict(),
            "router": self._router.stats(),
            "chunk_generator": self._chunk_generator.stats,
            "total_chunks_fed": self._total_chunks_fed,
            "total_chunks_generated": self._total_chunks_generated,
            "latency_warnings": self._latency_warnings,
        }

    def reset(self) -> None:
        """Reset the manager to initial state."""
        self.stop()
        with self._lock:
            self._sessions.clear()
            self._chunk_generator.reset()
            self._metrics.reset()
            self._router.reset()
            self._total_chunks_fed = 0
            self._total_chunks_generated = 0
            self._latency_warnings = 0
            self._created_at = time.monotonic()
