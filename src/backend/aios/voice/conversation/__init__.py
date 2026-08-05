"""Voice Conversation — continuous conversation management."""

from .events import Turn, ConversationEvent, ConversationEventType
from .state import ConversationState, can_transition
from .session import ConversationSession, ConversationSessionConfig, ConversationSessionStats, ConvEvent
from .metrics import ConversationMetrics, ConversationMetricsSnapshot
from .manager import (
    ConversationSessionManager,
    TurnManager,
    ConversationManagerConfig,
    TurnState,
    TurnAction,
    ManagerEvent,
)

__all__ = [
    "Turn",
    "ConversationEvent",
    "ConversationEventType",
    "ConversationState",
    "can_transition",
    "ConversationSession",
    "ConversationSessionConfig",
    "ConversationSessionStats",
    "ConvEvent",
    "ConversationMetrics",
    "ConversationMetricsSnapshot",
    "ConversationSessionManager",
    "TurnManager",
    "ConversationManagerConfig",
    "TurnState",
    "TurnAction",
    "ManagerEvent",
]
