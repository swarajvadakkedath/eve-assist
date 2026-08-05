"""Streaming STT — streaming speech-to-text recognition layer."""

from .events import TranscriptEvent, TranscriptEventType, WordTiming
from .provider import STTProvider, ProviderConfig, ProviderState, ProviderHealth, ProviderCapability
from .session import StreamingSTTSession, SessionState, SessionEvent, TranscriptChunk, SessionStats, SESSION_TRANSITIONS
from .metrics import TranscriptMetrics, TranscriptMetricsSnapshot
from .manager import StreamingSTTManager, STTConfig, ManagerEventType

__all__ = [
    "TranscriptEvent", "TranscriptEventType", "WordTiming",
    "STTProvider", "ProviderConfig", "ProviderState", "ProviderHealth", "ProviderCapability",
    "StreamingSTTSession", "SessionState", "SessionEvent", "TranscriptChunk", "SessionStats", "SESSION_TRANSITIONS",
    "TranscriptMetrics", "TranscriptMetricsSnapshot",
    "StreamingSTTManager", "STTConfig", "ManagerEventType",
]
