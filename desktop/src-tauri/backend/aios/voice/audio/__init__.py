"""Audio subsystem — production-grade audio infrastructure for VoiceOS+.

This package provides the complete audio operating system that every
future voice feature will use. No module may access microphones or
speakers directly — everything goes through AudioEngine.

Architecture:
    AudioEngine (single entry point)
        → DeviceManager (discover/manage hardware)
        → AudioRouter (route audio streams)
        → Recorder (capture from input)
        → Playback (output to speakers)
        → Mixer (combine multiple streams)
        → AudioSession (lifecycle management)
        → AudioResampler (rate conversion)
        → AudioDiagnostics (metrics for AIOps)
        → AudioBuffer (thread-safe ring buffer)
        → NoiseProcessor (audio cleaning)
        → VoiceActivityDetector (speech detection)
        → ListeningStateMachine (interaction lifecycle)
        → CalibrationManager (auto mic calibration)
        → VoiceProfile (sensitivity profiles)
"""

from .buffer import AudioBuffer, BufferStats
from .calibration import CalibrationManager, CalibrationConfig, CalibrationResult, CalibrationState
from .device_manager import DeviceManager, AudioDeviceInfo, DeviceType, DeviceStatus
from .diagnostics import AudioDiagnostics, AudioDiagnosticsSnapshot
from .engine import AudioEngine, AudioEngineConfig, AudioEngineState
from .exceptions import (
    AudioError,
    AudioBufferError,
    AudioBufferOverflowError,
    AudioBufferUnderflowError,
    AudioDeviceBusyError,
    AudioDeviceError,
    AudioDeviceNotFoundError,
    AudioDiagnosticsError,
    AudioMixerError,
    AudioPermissionError,
    AudioPlaybackError,
    AudioRecordingError,
    AudioResamplerError,
    AudioRoutingError,
    AudioSessionError,
    AudioSessionStateError,
)
from .listening_state import ListeningStateMachine, ListeningState, ListeningEvent, ListeningSnapshot
from .mixer import Mixer, MixerStream, StreamPriority
from .noise import NoiseProcessor, NoiseStats
from .playback import Playback, PlaybackSession, PlaybackState
from .profiles import VoiceProfile, ProfileType, get_profile, list_profiles, create_custom_profile, PROFILES
from .recorder import Recorder, RecordingSession, RecordingState
from .resampler import AudioResampler, SampleRate, ResampleResult
from .router import AudioRouter, AudioRoute, RouteType, RouteStatus
from .session import AudioSession, AudioSessionState, AudioSessionSnapshot
from .vad import VoiceActivityDetector, VADState, VADEvent, VADFrame, VADStats

__all__ = [
    # Engine
    "AudioEngine",
    "AudioEngineConfig",
    "AudioEngineState",
    # Device Manager
    "DeviceManager",
    "AudioDeviceInfo",
    "DeviceType",
    "DeviceStatus",
    # Router
    "AudioRouter",
    "AudioRoute",
    "RouteType",
    "RouteStatus",
    # Recorder
    "Recorder",
    "RecordingSession",
    "RecordingState",
    # Playback
    "Playback",
    "PlaybackSession",
    "PlaybackState",
    # Mixer
    "Mixer",
    "MixerStream",
    "StreamPriority",
    # Session
    "AudioSession",
    "AudioSessionState",
    "AudioSessionSnapshot",
    # Buffer
    "AudioBuffer",
    "BufferStats",
    # Resampler
    "AudioResampler",
    "SampleRate",
    "ResampleResult",
    # Diagnostics
    "AudioDiagnostics",
    "AudioDiagnosticsSnapshot",
    # Noise Processing
    "NoiseProcessor",
    "NoiseStats",
    # Voice Activity Detection
    "VoiceActivityDetector",
    "VADState",
    "VADEvent",
    "VADFrame",
    "VADStats",
    # Listening State Machine
    "ListeningStateMachine",
    "ListeningState",
    "ListeningEvent",
    "ListeningSnapshot",
    # Calibration
    "CalibrationManager",
    "CalibrationConfig",
    "CalibrationResult",
    "CalibrationState",
    # Profiles
    "VoiceProfile",
    "ProfileType",
    "get_profile",
    "list_profiles",
    "create_custom_profile",
    "PROFILES",
    # Exceptions
    "AudioError",
    "AudioDeviceError",
    "AudioDeviceNotFoundError",
    "AudioDeviceBusyError",
    "AudioPermissionError",
    "AudioBufferError",
    "AudioBufferOverflowError",
    "AudioBufferUnderflowError",
    "AudioResamplerError",
    "AudioRoutingError",
    "AudioSessionError",
    "AudioSessionStateError",
    "AudioPlaybackError",
    "AudioRecordingError",
    "AudioMixerError",
    "AudioDiagnosticsError",
]
