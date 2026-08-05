"""Voice Activity Detector — detects speech and silence in audio streams.

Uses energy-based detection with configurable sensitivity profiles.
Operates on PCM audio frames and publishes state changes via callbacks.
"""

from __future__ import annotations

import asyncio
import math
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .profiles import VoiceProfile, ProfileType, get_profile


class VADState(Enum):
    """VAD detection state."""
    IDLE = "idle"
    SPEECH = "speech"
    SILENCE = "silence"
    PAUSE = "pause"


class VADEvent(Enum):
    """VAD events published during detection."""
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    SHORT_PAUSE = "short_pause"
    LONG_PAUSE = "long_pause"
    SILENCE = "silence"
    CONFIDENCE_CHANGED = "confidence_changed"


@dataclass
class VADFrame:
    """Result of VAD analysis on a single audio frame."""
    timestamp: float
    rms: float
    peak: float
    confidence: float
    is_speech: bool
    state: VADState
    speech_duration: float
    silence_duration: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "rms": round(self.rms, 6),
            "peak": round(self.peak, 6),
            "confidence": round(self.confidence, 4),
            "is_speech": self.is_speech,
            "state": self.state.value,
            "speech_duration": round(self.speech_duration, 3),
            "silence_duration": round(self.silence_duration, 3),
        }


@dataclass
class VADStats:
    """VAD cumulative statistics."""
    total_frames: int = 0
    speech_frames: int = 0
    silence_frames: int = 0
    speech_count: int = 0
    avg_speech_duration: float = 0.0
    avg_silence_duration: float = 0.0
    max_speech_duration: float = 0.0
    current_confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_frames": self.total_frames,
            "speech_frames": self.speech_frames,
            "silence_frames": self.silence_frames,
            "speech_count": self.speech_count,
            "avg_speech_duration": round(self.avg_speech_duration, 3),
            "avg_silence_duration": round(self.avg_silence_duration, 3),
            "max_speech_duration": round(self.max_speech_duration, 3),
            "current_confidence": round(self.current_confidence, 4),
        }


class VoiceActivityDetector:
    """Energy-based voice activity detection.

    Analyzes audio frames to detect speech/silence transitions.
    Uses configurable profiles for threshold tuning.
    Publishes events via registered callbacks.
    """

    def __init__(self, profile: Optional[VoiceProfile] = None, *,
                 sample_rate: int = 16000, channels: int = 1,
                 sample_width: int = 2):
        self._profile = profile or get_profile(ProfileType.QUIET_ROOM)
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width

        # State
        self._state = VADState.IDLE
        self._speech_start_time: float = 0.0
        self._silence_start_time: float = 0.0
        self._last_speech_time: float = 0.0
        self._last_silence_time: float = 0.0
        self._hangover_until: float = 0.0
        self._current_confidence: float = 0.0

        # Stats
        self._total_frames = 0
        self._speech_frames = 0
        self._silence_frames = 0
        self._speech_count = 0
        self._speech_durations: list[float] = []
        self._silence_durations: list[float] = []

        # Callbacks
        self._event_handlers: dict[VADEvent, list[Callable]] = {}

        self._created_at = time.monotonic()

    @property
    def state(self) -> VADState:
        return self._state

    @property
    def is_speech(self) -> bool:
        return self._state == VADState.SPEECH

    @property
    def confidence(self) -> float:
        return self._current_confidence

    @property
    def profile(self) -> VoiceProfile:
        return self._profile

    def set_profile(self, profile: VoiceProfile) -> None:
        """Change the active sensitivity profile."""
        self._profile = profile

    def on(self, event: VADEvent, handler: Callable) -> None:
        """Subscribe to a VAD event."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: VADEvent, handler: Callable) -> None:
        """Unsubscribe from a VAD event."""
        if event in self._event_handlers:
            self._event_handlers[event] = [
                h for h in self._event_handlers[event] if h != handler
            ]

    async def _emit(self, event: VADEvent, data: dict) -> None:
        """Emit a VAD event to all registered handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, data)
                else:
                    handler(event, data)
            except Exception:
                pass

    def analyze_frame(self, data: bytes) -> VADFrame:
        """Analyze a single audio frame and return VAD results.

        This is the core detection method. Call it for each audio frame
        (typically every 20-40ms).
        """
        now = time.monotonic()
        self._total_frames += 1

        # Calculate audio metrics
        samples = self._unpack_samples(data)
        rms = self._calculate_rms(samples)
        peak = max(abs(s) for s in samples) / 32768.0 if samples else 0.0

        # Calculate confidence (how likely this is speech)
        confidence = self._calculate_confidence(rms, peak)

        # Determine speech/silence
        is_speech = rms >= self._profile.speech_threshold and confidence >= self._profile.confidence_threshold

        # Apply hangover (prevent choppiness at speech boundaries)
        if is_speech:
            self._hangover_until = now + self._profile.hangover_ms / 1000.0
        elif now < self._hangover_until:
            is_speech = True

        # State transitions
        prev_state = self._state
        self._update_state(is_speech, now, rms)

        # Update confidence
        self._current_confidence = confidence

        # Track durations
        speech_duration = 0.0
        silence_duration = 0.0
        if self._state == VADState.SPEECH and self._speech_start_time > 0:
            speech_duration = now - self._speech_start_time
        elif self._silence_start_time > 0:
            silence_duration = now - self._silence_start_time

        return VADFrame(
            timestamp=now,
            rms=rms,
            peak=peak,
            confidence=confidence,
            is_speech=is_speech,
            state=self._state,
            speech_duration=speech_duration,
            silence_duration=silence_duration,
        )

    def _calculate_confidence(self, rms: float, peak: float) -> float:
        """Calculate speech confidence based on energy and profile.

        Returns 0.0-1.0 where higher = more likely speech.
        """
        if rms <= 0:
            return 0.0

        # Energy-based confidence
        noise = self._profile.noise_threshold
        speech = self._profile.speech_threshold

        if rms <= noise:
            energy_conf = 0.0
        elif rms >= speech * 3:
            energy_conf = 1.0
        else:
            # Linear interpolation between noise and speech*3
            energy_conf = (rms - noise) / (speech * 3 - noise) if (speech * 3 - noise) > 0 else 0

        # Peak-to-RMS ratio (speech typically has higher ratio)
        crest_factor = peak / rms if rms > 0 else 0
        crest_conf = min(1.0, crest_factor / 3.0)  # Normalize

        # Combined confidence (weighted average)
        return 0.7 * energy_conf + 0.3 * crest_conf

    def _update_state(self, is_speech: bool, now: float, rms: float) -> None:
        """Update VAD state machine."""
        prev = self._state

        if is_speech:
            if self._state != VADState.SPEECH:
                # Speech started
                self._state = VADState.SPEECH
                self._speech_start_time = now
                self._silence_start_time = 0.0
                self._speech_count += 1
                self._last_speech_time = now

                # Emit event (fire-and-forget)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._emit(VADEvent.SPEECH_START, {
                        "timestamp": now,
                        "speech_count": self._speech_count,
                    }))
                except RuntimeError:
                    pass
        else:
            if self._state == VADState.SPEECH:
                # Speech ended → silence
                self._state = VADState.SILENCE
                self._silence_start_time = now
                speech_duration = now - self._speech_start_time
                self._speech_durations.append(speech_duration)
                self._speech_frames += self._total_frames

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._emit(VADEvent.SPEECH_END, {
                        "timestamp": now,
                        "duration": speech_duration,
                    }))
                except RuntimeError:
                    pass

            elif self._state == VADState.SILENCE:
                silence_duration = now - self._silence_start_time

                # Check for long pause
                if silence_duration >= self._profile.long_pause_timeout:
                    if prev != VADState.PAUSE:
                        self._state = VADState.PAUSE
                        self._last_silence_time = now
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(self._emit(VADEvent.LONG_PAUSE, {
                                "timestamp": now,
                                "duration": silence_duration,
                            }))
                        except RuntimeError:
                            pass

                # Check for short pause
                elif silence_duration >= self._profile.short_pause_timeout:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._emit(VADEvent.SHORT_PAUSE, {
                            "timestamp": now,
                            "duration": silence_duration,
                        }))
                    except RuntimeError:
                        pass

    def _unpack_samples(self, data: bytes) -> list[int]:
        """Unpack raw PCM bytes into integer samples."""
        if self._sample_width == 2:
            count = len(data) // 2
            if count == 0:
                return []
            return list(struct.unpack(f"<{count}h", data[:count * 2]))
        elif self._sample_width == 1:
            return [b - 128 for b in data]
        elif self._sample_width == 4:
            count = len(data) // 4
            if count == 0:
                return []
            return list(struct.unpack(f"<{count}i", data[:count * 4]))
        return []

    def _calculate_rms(self, samples: list[int]) -> float:
        """Calculate RMS amplitude (normalized to 0.0-1.0)."""
        if not samples:
            return 0.0
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / len(samples))
        return rms / 32768.0 if self._sample_width == 2 else rms / 128.0

    def reset(self) -> None:
        """Reset VAD state and statistics."""
        self._state = VADState.IDLE
        self._speech_start_time = 0.0
        self._silence_start_time = 0.0
        self._last_speech_time = 0.0
        self._last_silence_time = 0.0
        self._hangover_until = 0.0
        self._current_confidence = 0.0
        self._total_frames = 0
        self._speech_frames = 0
        self._silence_frames = 0
        self._speech_count = 0
        self._speech_durations.clear()
        self._silence_durations.clear()

    def stats(self) -> VADStats:
        """Get cumulative VAD statistics."""
        avg_speech = 0.0
        avg_silence = 0.0
        max_speech = 0.0

        if self._speech_durations:
            avg_speech = sum(self._speech_durations) / len(self._speech_durations)
            max_speech = max(self._speech_durations)
        if self._silence_durations:
            avg_silence = sum(self._silence_durations) / len(self._silence_durations)

        return VADStats(
            total_frames=self._total_frames,
            speech_frames=self._speech_frames,
            silence_frames=self._silence_frames,
            speech_count=self._speech_count,
            avg_speech_duration=avg_speech,
            avg_silence_duration=avg_silence,
            max_speech_duration=max_speech,
            current_confidence=self._current_confidence,
        )

    def to_dict(self) -> dict:
        """Serialize VAD state."""
        return {
            "state": self._state.value,
            "confidence": round(self._current_confidence, 4),
            "profile": self._profile.name,
            "stats": self.stats().to_dict(),
        }
