"""Streaming TTS — streaming text-to-speech synthesis layer."""

from .events import SpeechChunk, TTSRequest, TTSEventType
from .provider import TTSProvider, TTSProviderConfig, TTSProviderState, TTSProviderHealth
from .session import StreamingTTSSession, TTSSessionState, TTSSessionEvent, TTSSessionStats, TTS_SESSION_TRANSITIONS
from .metrics import TTSMetrics, TTSMetricsSnapshot
from .manager import StreamingTTSManager, TTSConfig, TTSManagerEventType, SpeechQueue

__all__ = [
    "SpeechChunk", "TTSRequest", "TTSEventType",
    "TTSProvider", "TTSProviderConfig", "TTSProviderState", "TTSProviderHealth",
    "StreamingTTSSession", "TTSSessionState", "TTSSessionEvent", "TTSSessionStats", "TTS_SESSION_TRANSITIONS",
    "TTSMetrics", "TTSMetricsSnapshot",
    "StreamingTTSManager", "TTSConfig", "TTSManagerEventType", "SpeechQueue",
]
