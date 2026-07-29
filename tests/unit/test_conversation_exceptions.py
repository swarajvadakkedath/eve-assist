"""Tests for conversation exceptions."""

import pytest
from aios.conversation.exceptions import (
    ConversationError,
    ConversationNotFoundError,
    MessageNotFoundError,
    SessionNotFoundError,
    AIProviderError,
    ToolExecutionError,
    MemoryError,
    PlannerError,
    StreamError,
)


class TestConversationExceptions:
    def test_conversation_error_base(self):
        err = ConversationError("base error")
        assert str(err) == "base error"
        assert err.original is None

    def test_conversation_error_with_original(self):
        original = ValueError("inner")
        err = ConversationError("wrapped", original=original)
        assert err.original is original

    def test_conversation_not_found(self):
        err = ConversationNotFoundError("conv-123")
        assert "conv-123" in str(err)
        assert isinstance(err, ConversationError)

    def test_message_not_found(self):
        err = MessageNotFoundError("msg-456")
        assert "msg-456" in str(err)
        assert isinstance(err, ConversationError)

    def test_session_not_found(self):
        err = SessionNotFoundError("sess-789")
        assert "sess-789" in str(err)
        assert isinstance(err, ConversationError)

    def test_ai_provider_error_default(self):
        err = AIProviderError()
        assert "unavailable" in str(err)
        assert isinstance(err, ConversationError)

    def test_ai_provider_error_custom(self):
        err = AIProviderError("Custom error")
        assert "Custom error" in str(err)

    def test_tool_execution_error(self):
        err = ToolExecutionError("file.read", "permission denied")
        assert "file.read" in str(err)
        assert "permission denied" in str(err)
        assert isinstance(err, ConversationError)

    def test_memory_error_default(self):
        err = MemoryError()
        assert "failed" in str(err)
        assert isinstance(err, ConversationError)

    def test_memory_error_with_original(self):
        original = RuntimeError("db down")
        err = MemoryError("memory failure", original=original)
        assert err.original is original

    def test_planner_error_default(self):
        err = PlannerError()
        assert "failed" in str(err)
        assert isinstance(err, ConversationError)

    def test_stream_error_default(self):
        err = StreamError()
        assert "Stream error" in str(err)
        assert isinstance(err, ConversationError)

    def test_exception_inheritance_chain(self):
        assert issubclass(ConversationNotFoundError, ConversationError)
        assert issubclass(MessageNotFoundError, ConversationError)
        assert issubclass(SessionNotFoundError, ConversationError)
        assert issubclass(AIProviderError, ConversationError)
        assert issubclass(ToolExecutionError, ConversationError)
        assert issubclass(MemoryError, ConversationError)
        assert issubclass(PlannerError, ConversationError)
        assert issubclass(StreamError, ConversationError)
        assert issubclass(ConversationError, Exception)
