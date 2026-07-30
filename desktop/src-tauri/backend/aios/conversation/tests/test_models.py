"""Unit tests for conversation data models."""

import pytest
from datetime import datetime
from uuid import UUID

from aios.conversation.models import (
    Conversation,
    Message,
    Session,
    ToolCall,
    MessageRole,
    ToolCallStatus,
)


class TestConversationModel:
    def test_create_conversation(self):
        conv = Conversation(title="Test Chat")
        assert conv.id
        assert conv.title == "Test Chat"
        assert conv.created_at is not None
        assert conv.updated_at is not None
        assert conv.is_active is True
        assert conv.message_count == 0

    def test_conversation_default_id(self):
        conv = Conversation()
        assert len(conv.id) == 32

    def test_conversation_custom_id(self):
        conv = Conversation(id="custom-id")
        assert conv.id == "custom-id"

    def test_conversation_with_project(self):
        conv = Conversation(title="Project Chat", active_project="/path/to/project")
        assert conv.active_project == "/path/to/project"


class TestMessageModel:
    def test_create_user_message(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.id
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.timestamp is not None

    def test_create_assistant_message(self):
        msg = Message(role=MessageRole.ASSISTANT, content="Hi there", tokens_used=42)
        assert msg.role == MessageRole.ASSISTANT
        assert msg.tokens_used == 42

    def test_message_with_tool_calls(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp/test"})
        msg = Message(role=MessageRole.ASSISTANT, content="Reading file...", tool_calls=[tc])
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].tool_name == "file.read"

    def test_message_role_string_conversion(self):
        msg = Message(role="user", content="test")
        assert msg.role == MessageRole.USER
        assert msg.role.value == "user"


class TestSessionModel:
    def test_create_session(self):
        session = Session(conversation_id="conv-1")
        assert session.session_id
        assert session.conversation_id == "conv-1"
        assert session.created_at is not None

    def test_session_with_context(self):
        session = Session(conversation_id="conv-1", current_context={"app": "vscode"})
        assert session.current_context["app"] == "vscode"


class TestToolCallModel:
    def test_create_tool_call(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp/test"})
        assert tc.status == ToolCallStatus.PENDING
        assert tc.execution_time == 0.0

    def test_tool_call_status_string(self):
        tc = ToolCall(status="success")
        assert tc.status == ToolCallStatus.SUCCESS

    def test_tool_call_with_result(self):
        tc = ToolCall(tool_name="file.read", status="success", result={"content": "test"}, execution_time=0.5)
        assert tc.result["content"] == "test"
        assert tc.execution_time == 0.5
