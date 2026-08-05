"""Thread-safe ring buffer for low-latency audio streaming."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from .exceptions import AudioBufferOverflowError, AudioBufferUnderflowError


@dataclass
class BufferStats:
    """Ring buffer statistics."""
    total_written: int = 0
    total_read: int = 0
    overflow_count: int = 0
    underflow_count: int = 0
    peak_usage: int = 0
    current_usage: int = 0
    capacity: int = 0

    def to_dict(self) -> dict:
        return {
            "total_written": self.total_written,
            "total_read": self.total_read,
            "overflow_count": self.overflow_count,
            "underflow_count": self.underflow_count,
            "peak_usage": self.peak_usage,
            "current_usage": self.current_usage,
            "capacity": self.capacity,
        }


class AudioBuffer:
    """Thread-safe ring buffer for audio samples.

    Supports configurable size, overflow/underflow protection,
    and statistics collection for diagnostics.
    """

    def __init__(self, capacity: int = 8192, *, overflow_protection: bool = True,
                 underflow_protection: bool = True):
        self._capacity = capacity
        self._buffer = bytearray(capacity)
        self._write_pos = 0
        self._read_pos = 0
        self._count = 0
        self._overflow_protection = overflow_protection
        self._underflow_protection = underflow_protection
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._closed = False
        self._stats = BufferStats(capacity=capacity)
        self._created_at = time.monotonic()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    @property
    def available(self) -> int:
        with self._lock:
            return self._capacity - self._count

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return self._count == 0

    @property
    def is_full(self) -> bool:
        with self._lock:
            return self._count == self._capacity

    @property
    def stats(self) -> BufferStats:
        with self._lock:
            self._stats.current_usage = self._count
            self._stats.peak_usage = max(self._stats.peak_usage, self._count)
            return self._stats

    def write(self, data: bytes, *, block: bool = False,
              timeout: Optional[float] = None) -> int:
        """Write audio data into the ring buffer.

        Returns number of bytes actually written.
        Raises AudioBufferOverflowError if buffer full and overflow_protection enabled.
        """
        if self._closed:
            return 0

        data_len = len(data)
        if data_len == 0:
            return 0

        with self._lock:
            if block and timeout is not None:
                deadline = time.monotonic() + timeout
                while self._count == self._capacity:
                    if self._closed:
                        return 0
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        if self._overflow_protection:
                            raise AudioBufferOverflowError(
                                f"Buffer full ({self._capacity} bytes) after {timeout}s timeout"
                            )
                        return 0
                    self._not_full.wait(timeout=min(remaining, 0.01))
            elif block:
                while self._count == self._capacity:
                    if self._closed:
                        return 0
                    self._not_full.wait(timeout=0.01)
            elif self._count == self._capacity:
                if self._overflow_protection:
                    raise AudioBufferOverflowError(
                        f"Buffer full ({self._capacity} bytes)"
                    )
                return 0

            # Write in two parts if wrapping around
            first_chunk = min(data_len, self._capacity - self._write_pos)
            self._buffer[self._write_pos:self._write_pos + first_chunk] = data[:first_chunk]
            self._write_pos = (self._write_pos + first_chunk) % self._capacity

            second_chunk = data_len - first_chunk
            if second_chunk > 0:
                self._buffer[self._write_pos:self._write_pos + second_chunk] = data[first_chunk:first_chunk + second_chunk]
                self._write_pos = (self._write_pos + second_chunk) % self._capacity

            self._count += data_len
            self._stats.total_written += data_len
            self._not_empty.notify_all()
            return data_len

    def read(self, length: int, *, block: bool = False,
             timeout: Optional[float] = None) -> bytes:
        """Read audio data from the ring buffer.

        Returns up to `length` bytes.
        Raises AudioBufferUnderflowError if buffer empty and underflow_protection enabled.
        """
        if self._closed and self._count == 0:
            return b""

        with self._lock:
            if block and timeout is not None:
                deadline = time.monotonic() + timeout
                while self._count == 0:
                    if self._closed:
                        # Return whatever is left
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        if self._underflow_protection:
                            raise AudioBufferUnderflowError(
                                f"Buffer empty after {timeout}s timeout"
                            )
                        return b""
                    self._not_empty.wait(timeout=min(remaining, 0.01))
            elif block:
                while self._count == 0:
                    if self._closed:
                        break
                    self._not_empty.wait(timeout=0.01)
            elif self._count == 0:
                if self._underflow_protection:
                    raise AudioBufferUnderflowError(
                        f"Buffer empty (capacity={self._capacity})"
                    )
                return b""

            to_read = min(length, self._count)
            if to_read == 0:
                return b""

            # Read in two parts if wrapping around
            first_chunk = min(to_read, self._capacity - self._read_pos)
            result = bytes(self._buffer[self._read_pos:self._read_pos + first_chunk])
            self._read_pos = (self._read_pos + first_chunk) % self._capacity

            second_chunk = to_read - first_chunk
            if second_chunk > 0:
                result += bytes(self._buffer[self._read_pos:self._read_pos + second_chunk])
                self._read_pos = (self._read_pos + second_chunk) % self._capacity

            self._count -= to_read
            self._stats.total_read += to_read
            self._not_full.notify_all()
            return result

    def peek(self, length: int) -> bytes:
        """Peek at data without consuming it."""
        with self._lock:
            to_peek = min(length, self._count)
            if to_peek == 0:
                return b""

            pos = self._read_pos
            first_chunk = min(to_peek, self._capacity - pos)
            result = bytes(self._buffer[pos:pos + first_chunk])
            pos = (pos + first_chunk) % self._capacity

            second_chunk = to_peek - first_chunk
            if second_chunk > 0:
                result += bytes(self._buffer[pos:pos + second_chunk])

            return result

    def flush(self) -> int:
        """Discard all buffered data. Returns bytes discarded."""
        with self._lock:
            discarded = self._count
            self._count = 0
            self._read_pos = 0
            self._write_pos = 0
            self._not_full.notify_all()
            return discarded

    def close(self) -> None:
        """Close the buffer, unblocking any waiting readers/writers."""
        with self._lock:
            self._closed = True
            self._not_empty.notify_all()
            self._not_full.notify_all()

    @property
    def is_closed(self) -> bool:
        with self._lock:
            return self._closed

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self._stats = BufferStats(capacity=self._capacity)

    def __len__(self) -> int:
        return self.count

    def __bool__(self) -> bool:
        return not self.is_empty
