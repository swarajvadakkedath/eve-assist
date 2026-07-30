"""Conversation module — core interaction layer for AIOS."""

from aios.conversation.models import Conversation, Message, Session, ToolCall, StreamEvent
from aios.conversation.manager import ConversationManager
from aios.conversation.service import ConversationService
from aios.conversation.interfaces import IConversationRepository, IConversationService
from aios.conversation.exceptions import (
    ConversationNotFoundError,
    MessageNotFoundError,
    SessionNotFoundError,
    ConversationError,
    AIProviderError,
    ToolExecutionError,
    MemoryError,
    PlannerError,
    StreamError,
)

__all__ = [
    "Conversation",
    "Message",
    "Session",
    "ToolCall",
    "StreamEvent",
    "ConversationManager",
    "ConversationService",
    "IConversationRepository",
    "IConversationService",
    "ConversationNotFoundError",
    "MessageNotFoundError",
    "SessionNotFoundError",
    "ConversationError",
    "AIProviderError",
    "ToolExecutionError",
    "MemoryError",
    "PlannerError",
    "StreamError",
]
