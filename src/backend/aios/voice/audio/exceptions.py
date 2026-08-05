"""Audio subsystem exceptions."""

from __future__ import annotations


class AudioError(Exception):
    """Base exception for audio subsystem."""


class AudioDeviceError(AudioError):
    """Audio device not available or failed."""


class AudioDeviceNotFoundError(AudioDeviceError):
    """Requested audio device not found."""


class AudioDeviceBusyError(AudioDeviceError):
    """Audio device is busy (in use by another session)."""


class AudioPermissionError(AudioError):
    """Microphone permission denied."""


class AudioBufferError(AudioError):
    """Buffer overflow, underflow, or allocation failure."""


class AudioBufferOverflowError(AudioBufferError):
    """Buffer overflow — data written faster than consumed."""


class AudioBufferUnderflowError(AudioBufferError):
    """Buffer underflow — data consumed faster than written."""


class AudioResamplerError(AudioError):
    """Resampling failed."""


class AudioRoutingError(AudioError):
    """Audio routing failed."""


class AudioSessionError(AudioError):
    """Audio session lifecycle error."""


class AudioSessionStateError(AudioSessionError):
    """Invalid state transition for audio session."""


class AudioPlaybackError(AudioError):
    """Playback failed."""


class AudioRecordingError(AudioError):
    """Recording failed."""


class AudioMixerError(AudioError):
    """Mixer operation failed."""


class AudioDiagnosticsError(AudioError):
    """Diagnostics collection failed."""
