"""Voice Stream — real-time speech pipeline infrastructure.

Provides the streaming layer that connects the audio engine output
to speech-to-text and other consumers.

Modules:
    chunk: AudioChunk dataclass and ChunkGenerator for fixed-size chunking.
    metrics: StreamMetrics for latency and throughput tracking.
    session: SpeechSession lifecycle management.
    router: StreamRouter for multi-consumer chunk distribution.
    manager: SpeechStreamManager as the single pipeline entry point.
"""

from .chunk import (
    AudioChunk,
    ChunkGenerator,
    ChunkStatus,
    validate_chunk,
    compute_chunk_order_score,
)
from .metrics import (
    StreamMetrics,
    StreamMetricsSnapshot,
    LatencySnapshot,
)
from .session import (
    SpeechSession,
    SessionState,
    SessionEvent,
    SessionStats,
    SESSION_TRANSITIONS,
)
from .router import (
    StreamRouter,
    ConsumerInfo,
    ConsumerState,
    DropPolicy,
)
from .manager import (
    SpeechStreamManager,
    StreamConfig,
    StreamEventType,
)

__all__ = [
    # Chunk
    "AudioChunk",
    "ChunkGenerator",
    "ChunkStatus",
    "validate_chunk",
    "compute_chunk_order_score",
    # Metrics
    "StreamMetrics",
    "StreamMetricsSnapshot",
    "LatencySnapshot",
    # Session
    "SpeechSession",
    "SessionState",
    "SessionEvent",
    "SessionStats",
    "SESSION_TRANSITIONS",
    # Router
    "StreamRouter",
    "ConsumerInfo",
    "ConsumerState",
    "DropPolicy",
    # Manager
    "SpeechStreamManager",
    "StreamConfig",
    "StreamEventType",
]
