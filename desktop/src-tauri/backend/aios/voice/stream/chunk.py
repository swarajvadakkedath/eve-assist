"""Audio Chunk — fixed-size audio data with metadata for pipeline routing.

Chunks are the fundamental unit of data flowing through the speech pipeline.
Each chunk carries audio data plus metadata needed for ordering, validation,
and latency tracking.
"""

from __future__ import annotations

import struct
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChunkStatus(Enum):
    """Chunk lifecycle status."""
    CREATED = "created"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    DROPPED = "dropped"
    LOST = "lost"


@dataclass
class AudioChunk:
    """Fixed-size audio chunk with pipeline metadata.

    Attributes:
        data: Raw PCM audio bytes.
        sequence: Monotonic sequence number for ordering.
        timestamp: Wall-clock time when chunk was created.
        sample_rate: Audio sample rate in Hz.
        channels: Number of audio channels.
        duration_ms: Duration of audio in milliseconds.
        chunk_size_bytes: Expected chunk size in bytes.
        status: Current lifecycle status.
        source: Origin identifier (e.g., "microphone", "file").
        metadata: Arbitrary key-value metadata.
    """
    data: bytes
    sequence: int
    timestamp: float = field(default_factory=time.monotonic)
    sample_rate: int = 16000
    channels: int = 1
    duration_ms: float = 0.0
    chunk_size_bytes: int = 0
    status: ChunkStatus = ChunkStatus.CREATED
    source: str = "microphone"
    metadata: dict = field(default_factory=dict)

    @property
    def size_bytes(self) -> int:
        """Size of audio data in bytes."""
        return len(self.data)

    @property
    def is_valid(self) -> bool:
        """Chunk has data and expected size matches."""
        return len(self.data) > 0 and (
            self.chunk_size_bytes == 0 or len(self.data) == self.chunk_size_bytes
        )

    @property
    def age_ms(self) -> float:
        """Milliseconds since chunk was created."""
        return (time.monotonic() - self.timestamp) * 1000

    def mark_processing(self) -> None:
        """Mark chunk as being processed."""
        self.status = ChunkStatus.PROCESSING

    def mark_delivered(self) -> None:
        """Mark chunk as delivered to consumer."""
        self.status = ChunkStatus.DELIVERED

    def mark_dropped(self, reason: str = "") -> None:
        """Mark chunk as dropped."""
        self.status = ChunkStatus.DROPPED
        if reason:
            self.metadata["drop_reason"] = reason

    def to_dict(self) -> dict:
        """Serialize chunk metadata (not audio data) to dict."""
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration_ms": round(self.duration_ms, 3),
            "size_bytes": self.size_bytes,
            "chunk_size_bytes": self.chunk_size_bytes,
            "status": self.status.value,
            "source": self.source,
            "age_ms": round(self.age_ms, 3),
            "metadata": self.metadata,
        }


class ChunkGenerator:
    """Generates fixed-size AudioChunks from a raw audio stream.

    Accumulates incoming PCM bytes and emits chunks when the configured
    chunk size is reached. Supports sequence numbering, timestamping,
    and loss detection.

    Args:
        chunk_size_ms: Duration of each chunk in milliseconds.
        sample_rate: Audio sample rate in Hz.
        channels: Number of audio channels.
        sample_width: Bytes per sample (1=8-bit, 2=16-bit, 4=32-bit).
    """

    def __init__(
        self,
        *,
        chunk_size_ms: int = 30,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
    ):
        self._chunk_size_ms = chunk_size_ms
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width

        # Calculate chunk size in bytes
        samples_per_chunk = int(sample_rate * chunk_size_ms / 1000)
        self._chunk_size_bytes = samples_per_chunk * channels * sample_width
        self._chunk_duration_ms = (self._chunk_size_bytes / (sample_rate * channels * sample_width)) * 1000

        # State
        self._buffer = bytearray()
        self._sequence = 0
        self._total_chunks_created = 0
        self._total_bytes_fed = 0
        self._last_chunk_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def chunk_size_bytes(self) -> int:
        """Expected chunk size in bytes."""
        return self._chunk_size_bytes

    @property
    def chunk_size_ms(self) -> int:
        """Chunk duration in milliseconds."""
        return self._chunk_size_ms

    @property
    def buffered_bytes(self) -> int:
        """Bytes currently in the buffer."""
        with self._lock:
            return len(self._buffer)

    @property
    def sequence(self) -> int:
        """Next sequence number."""
        return self._sequence

    @property
    def stats(self) -> dict:
        """Generator statistics."""
        return {
            "chunk_size_bytes": self._chunk_size_bytes,
            "chunk_size_ms": self._chunk_size_ms,
            "sample_rate": self._sample_rate,
            "channels": self._channels,
            "sample_width": self._sample_width,
            "buffered_bytes": self.buffered_bytes,
            "sequence": self._sequence,
            "total_chunks_created": self._total_chunks_created,
            "total_bytes_fed": self._total_bytes_fed,
        }

    def feed(self, data: bytes) -> list[AudioChunk]:
        """Feed PCM data into the generator.

        Returns a list of complete chunks (0 or more).
        """
        chunks = []
        with self._lock:
            self._buffer.extend(data)
            self._total_bytes_fed += len(data)

            while len(self._buffer) >= self._chunk_size_bytes:
                chunk_data = bytes(self._buffer[:self._chunk_size_bytes])
                del self._buffer[:self._chunk_size_bytes]

                chunk = AudioChunk(
                    data=chunk_data,
                    sequence=self._sequence,
                    timestamp=time.monotonic(),
                    sample_rate=self._sample_rate,
                    channels=self._channels,
                    duration_ms=self._chunk_duration_ms,
                    chunk_size_bytes=self._chunk_size_bytes,
                    source="microphone",
                )
                self._sequence += 1
                self._total_chunks_created += 1
                self._last_chunk_time = chunk.timestamp
                chunks.append(chunk)

        return chunks

    def flush(self) -> Optional[AudioChunk]:
        """Flush remaining buffer as a partial chunk.

        Returns None if buffer is empty.
        """
        with self._lock:
            if not self._buffer:
                return None

            chunk_data = bytes(self._buffer)
            self._buffer.clear()

            # Calculate actual duration for partial chunk
            samples = len(chunk_data) / (self._channels * self._sample_width)
            duration_ms = (samples / self._sample_rate) * 1000

            chunk = AudioChunk(
                data=chunk_data,
                sequence=self._sequence,
                timestamp=time.monotonic(),
                sample_rate=self._sample_rate,
                channels=self._channels,
                duration_ms=duration_ms,
                chunk_size_bytes=0,  # Partial chunk
                source="microphone",
                metadata={"partial": True},
            )
            self._sequence += 1
            self._total_chunks_created += 1
            return chunk

    def reset(self) -> None:
        """Reset generator state."""
        with self._lock:
            self._buffer.clear()
            self._sequence = 0
            self._total_chunks_created = 0
            self._total_bytes_fed = 0
            self._last_chunk_time = 0.0


def validate_chunk(chunk: AudioChunk, expected_size: int) -> bool:
    """Validate a chunk has correct size and is not corrupted.

    Args:
        chunk: The chunk to validate.
        expected_size: Expected chunk size in bytes (0 to skip size check).

    Returns:
        True if chunk is valid.
    """
    if not chunk.data:
        return False
    if expected_size > 0 and len(chunk.data) != expected_size:
        return False
    if chunk.sample_rate <= 0:
        return False
    if chunk.channels <= 0:
        return False
    return True


def compute_chunk_order_score(chunks: list[AudioChunk]) -> tuple[int, int]:
    """Compute ordering statistics for a list of chunks.

    Returns:
        Tuple of (out_of_order_count, gap_count).
    """
    if len(chunks) < 2:
        return (0, 0)

    out_of_order = 0
    gaps = 0
    prev_seq = chunks[0].sequence

    for chunk in chunks[1:]:
        if chunk.sequence < prev_seq:
            out_of_order += 1
        elif chunk.sequence > prev_seq + 1:
            gaps += 1
        prev_seq = chunk.sequence

    return (out_of_order, gaps)
