"""Unit tests for response formatter."""

from datetime import datetime
from aios.conversation.formatter import (
    format_conversation_response,
    format_message_response,
    format_message_list,
    create_token_event,
    create_done_event,
    create_error_event,
    create_tool_call_event,
    create_tool_result_event,
    create_status_event,
)
from aios.conversation.models import Conversation, Message, MessageRole, ToolCall


class TestFormatter:
    def test_format_conversation_response(self):
        conv = Conversation(title="Test", active_project="/project")
        result = format_conversation_response(conv)
        assert result["id"] == conv.id
        assert result["title"] == "Test"
        assert result["active_project"] == "/project"

    def test_format_message_response(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        result = format_message_response(msg)
        assert result["role"] == "user"
        assert result["content"] == "Hello"

    def test_format_message_response_with_tool_details(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp/test"})
        msg = Message(role=MessageRole.ASSISTANT, content="Done", tool_calls=[tc])
        result = format_message_response(msg, include_tool_details=True)
        assert "tool_calls" in result
        assert result["tool_calls"][0]["tool_name"] == "file.read"

    def test_format_message_list(self):
        msgs = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi"),
        ]
        result = format_message_list(msgs)
        assert len(result) == 2

    def test_create_token_event(self):
        event = create_token_event("Hello")
        assert event["type"] == "token"
        assert event["data"]["token"] == "Hello"

    def test_create_done_event(self):
        event = create_done_event("msg-1", tokens_used=42)
        assert event["type"] == "done"
        assert event["data"]["message_id"] == "msg-1"
        assert event["data"]["tokens_used"] == 42

    def test_create_error_event(self):
        event = create_error_event("Something went wrong")
        assert event["type"] == "error"
        assert event["data"]["error"] == "Something went wrong"
        assert event["data"]["recoverable"] is True

    def test_create_error_event_non_recoverable(self):
        event = create_error_event("Fatal", recoverable=False)
        assert event["data"]["recoverable"] is False

    def test_create_tool_call_event(self):
        event = create_tool_call_event("file.read", "file.read", {"path": "/tmp/test"})
        assert event["type"] == "tool_call"
        assert event["data"]["tool_name"] == "file.read"

    def test_create_tool_result_event(self):
        event = create_tool_result_event("file.read", {"content": "test"}, True)
        assert event["type"] == "tool_result"
        assert event["data"]["success"] is True

    def test_create_status_event(self):
        event = create_status_event("processing", "Thinking...")
        assert event["type"] == "status"
        assert event["data"]["status"] == "processing"
