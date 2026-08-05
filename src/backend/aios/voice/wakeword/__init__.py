"""Voice Wake Word — hands-free activation for EVE."""

from .models import (
    WakePhrase, WakeWordConfig, WakeWordState, DetectionResult,
    SensitivityLevel, SensitivityProfile, PowerMode, SENSITIVITY_PROFILES,
)
from .events import WakeWordEvent, WakeWordEventType
from .metrics import WakeWordMetrics, WakeWordMetricsSnapshot
from .detector import WakeWordDetector, AudioFrame, DetectorState
from .session import WakeWordSession, WakeSessionState, WakeSessionStats, WakeSessionEvent
from .engine import WakeWordEngine, WakeEngineState

__all__ = [
    "WakePhrase", "WakeWordConfig", "WakeWordState", "DetectionResult",
    "SensitivityLevel", "SensitivityProfile", "PowerMode", "SENSITIVITY_PROFILES",
    "WakeWordEvent", "WakeWordEventType",
    "WakeWordMetrics", "WakeWordMetricsSnapshot",
    "WakeWordDetector", "AudioFrame", "DetectorState",
    "WakeWordSession", "WakeSessionState", "WakeSessionStats", "WakeSessionEvent",
    "WakeWordEngine", "WakeEngineState",
]
