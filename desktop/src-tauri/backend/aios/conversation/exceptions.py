"""Conversation-specific exceptions."""


class ConversationError(Exception):
    """Base exception for conversation module."""

    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.original = original


class ConversationNotFoundError(ConversationError):
    def __init__(self, conversation_id: str):
        super().__init__(f"Conversation not found: {conversation_id}")


class MessageNotFoundError(ConversationError):
    def __init__(self, message_id: str):
        super().__init__(f"Message not found: {message_id}")


class SessionNotFoundError(ConversationError):
    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}")


class AIProviderError(ConversationError):
    def __init__(self, message: str = "AI provider unavailable", original: Exception | None = None):
        super().__init__(message, original)

    def __str__(self):
        base = super().__str__()
        if self.original:
            return f"{base} (original: {self.original})"
        return base


class ToolExecutionError(ConversationError):
    def __init__(self, tool_name: str, reason: str = ""):
        super().__init__(f"Tool execution failed: {tool_name} - {reason}")


class MemoryError(ConversationError):
    def __init__(self, message: str = "Memory operation failed", original: Exception | None = None):
        super().__init__(message, original)


class PlannerError(ConversationError):
    def __init__(self, message: str = "Planner operation failed", original: Exception | None = None):
        super().__init__(message, original)


class StreamError(ConversationError):
    def __init__(self, message: str = "Stream error", original: Exception | None = None):
        super().__init__(message, original)
