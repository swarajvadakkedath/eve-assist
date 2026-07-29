"""Tests for response formatter."""

from datetime import datetime
from aios.conversation.formatter import (
    format_conversation_response,
    format_message_response,
    format_message_list,
    format_tool_call_card,
    create_token_event,
    create_done_event,
    create_error_event,
    create_tool_call_event,
    create_tool_result_event,
    create_status_event,
    create_planner_started_event,
    create_planner_completed_event,
    create_memory_retrieval_event,
    create_tool_requested_event,
    create_tool_running_event,
    create_tool_completed_event,
    create_context_loaded_event,
    create_final_response_event,
    create_title_generated_event,
    create_analytics_event,
    create_vision_observation_event,
)
from aios.conversation.models import Conversation, Message, MessageRole, ToolCall, EditEntry


class TestFormatConversationResponse:
    def test_format_conversation_response(self):
        conv = Conversation(title="Test", active_project="/project", message_count=5, metadata={"key": "val"})
        result = format_conversation_response(conv)
        assert result["id"] == conv.id
        assert result["title"] == "Test"
        assert result["active_project"] == "/project"
        assert result["message_count"] == 5
        assert result["is_active"] is True
        assert result["metadata"]["key"] == "val"

    def test_format_conversation_is_branch(self):
        conv = Conversation(title="Branch", parent_id="parent-1")
        result = format_conversation_response(conv)
        assert result["is_branch"] is True
        assert result["parent_id"] == "parent-1"

    def test_format_conversation_title_custom(self):
        conv = Conversation(title="Custom", metadata={"title_is_custom": True})
        result = format_conversation_response(conv)
        assert result["title_is_custom"] is True

    def test_format_conversation_no_dates(self):
        conv = Conversation(title="No Dates")
        conv.created_at = None
        conv.updated_at = None
        result = format_conversation_response(conv)
        assert result["created_at"] == ""
        assert result["updated_at"] == ""


class TestFormatMessageResponse:
    def test_format_message_response(self):
        msg = Message(role=MessageRole.USER, content="Hello", tokens_used=0)
        result = format_message_response(msg)
        assert result["role"] == "user"
        assert result["content"] == "Hello"
        assert result["tokens_used"] == 0

    def test_format_message_with_tool_details(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp/test"})
        msg = Message(role=MessageRole.ASSISTANT, content="Done", tool_calls=[tc])
        result = format_message_response(msg, include_tool_details=True)
        assert "tool_calls" in result
        assert result["tool_calls"][0]["tool_name"] == "file.read"

    def test_format_message_without_tool_details(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp/test"})
        msg = Message(role=MessageRole.ASSISTANT, content="Done", tool_calls=[tc])
        result = format_message_response(msg, include_tool_details=False)
        assert "tool_calls" not in result

    def test_format_message_with_edit_history(self):
        msg = Message(role=MessageRole.USER, content="Final")
        entry = EditEntry(original_content="Original", edited_content="Final", timestamp=datetime.utcnow())
        msg.edit_history.append(entry)
        result = format_message_response(msg)
        assert "edit_history" in result
        assert result["edit_history"][0]["original_content"] == "Original"

    def test_format_message_with_attachments(self):
        msg = Message(role=MessageRole.USER, content="See", attachments=[{"type": "image"}])
        result = format_message_response(msg)
        assert result["attachments"] == [{"type": "image"}]

    def test_format_message_regenerated_flag(self):
        msg = Message(role=MessageRole.USER, content="test", is_regenerated=True)
        result = format_message_response(msg)
        assert result["is_regenerated"] is True

    def test_format_message_latency(self):
        msg = Message(role=MessageRole.USER, content="test", latency_ms=150.5)
        result = format_message_response(msg)
        assert result["latency_ms"] == 150.5

    def test_format_message_no_tool_calls_field(self):
        msg = Message(role=MessageRole.USER, content="test")
        result = format_message_response(msg)
        assert "tool_calls" not in result


class TestFormatMessageList:
    def test_format_message_list(self):
        msgs = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi"),
        ]
        result = format_message_list(msgs)
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    def test_format_message_list_empty(self):
        result = format_message_list([])
        assert result == []

    def test_format_message_list_with_tool_details(self):
        tc = ToolCall(tool_name="search", capability="web.search", parameters={"q": "test"})
        msgs = [Message(role=MessageRole.ASSISTANT, content="Done", tool_calls=[tc])]
        result = format_message_list(msgs, include_tool_details=True)
        assert "tool_calls" in result[0]

    def test_format_message_list_multiple_calls(self):
        tcs = [
            ToolCall(tool_name="a", capability="a", parameters={}),
            ToolCall(tool_name="b", capability="b", parameters={}),
        ]
        msgs = [Message(role=MessageRole.ASSISTANT, content="Multiple", tool_calls=tcs)]
        result = format_message_list(msgs, include_tool_details=True)
        assert len(result[0]["tool_calls"]) == 2


class TestFormatToolCallCard:
    def test_format_tool_call_card(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp"}, status="success", execution_time=0.5, result={"content": "test"})
        result = format_tool_call_card(tc)
        assert result["tool_name"] == "file.read"
        assert result["status"] == "success"
        assert result["execution_time"] == 0.5
        assert result["result"] == {"content": "test"}

    def test_format_tool_call_card_defaults(self):
        tc = ToolCall()
        result = format_tool_call_card(tc)
        assert result["tool_name"] == ""
        assert result["status"] == "pending"


class TestEventCreators:
    def test_create_token_event(self):
        event = create_token_event("Hello")
        assert event["type"] == "token"
        assert event["data"]["token"] == "Hello"

    def test_create_done_event(self):
        event = create_done_event("msg-1", tokens_used=42)
        assert event["type"] == "done"
        assert event["data"]["message_id"] == "msg-1"
        assert event["data"]["tokens_used"] == 42

    def test_create_done_event_default(self):
        event = create_done_event("msg-1")
        assert event["data"]["tokens_used"] == 0

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
        assert event["data"]["parameters"] == {"path": "/tmp/test"}

    def test_create_tool_result_event(self):
        event = create_tool_result_event("file.read", {"content": "test"}, True)
        assert event["type"] == "tool_result"
        assert event["data"]["tool_name"] == "file.read"
        assert event["data"]["success"] is True

    def test_create_tool_result_event_failure(self):
        event = create_tool_result_event("file.read", "permission denied", False)
        assert event["data"]["success"] is False

    def test_create_status_event(self):
        event = create_status_event("processing", "Thinking...")
        assert event["type"] == "status"
        assert event["data"]["status"] == "processing"
        assert event["data"]["message"] == "Thinking..."

    def test_create_status_event_no_message(self):
        event = create_status_event("done")
        assert event["data"]["message"] == ""

    def test_create_planner_started_event(self):
        event = create_planner_started_event("Find files")
        assert event["type"] == "planner_started"
        assert event["data"]["request"] == "Find files"

    def test_create_planner_completed_event(self):
        event = create_planner_completed_event(5)
        assert event["type"] == "planner_completed"
        assert event["data"]["steps"] == 5

    def test_create_memory_retrieval_event(self):
        event = create_memory_retrieval_event("Python", 3)
        assert event["type"] == "memory_retrieval"
        assert event["data"]["query"] == "Python"
        assert event["data"]["count"] == 3

    def test_create_tool_requested_event(self):
        event = create_tool_requested_event("file.read", "file.read")
        assert event["type"] == "tool_requested"
        assert event["data"]["tool_name"] == "file.read"

    def test_create_tool_running_event(self):
        event = create_tool_running_event("file.read")
        assert event["type"] == "tool_running"
        assert event["data"]["tool_name"] == "file.read"

    def test_create_tool_completed_event(self):
        event = create_tool_completed_event("file.read", True, 1.5)
        assert event["type"] == "tool_completed"
        assert event["data"]["tool_name"] == "file.read"
        assert event["data"]["success"] is True
        assert event["data"]["duration"] == 1.5

    def test_create_tool_completed_event_failure(self):
        event = create_tool_completed_event("file.read", False, 0.5)
        assert event["data"]["success"] is False

    def test_create_context_loaded_event(self):
        event = create_context_loaded_event(4096)
        assert event["type"] == "context_loaded"
        assert event["data"]["context_size"] == 4096

    def test_create_final_response_event(self):
        event = create_final_response_event()
        assert event["type"] == "final_response"
        assert event["data"] == {}

    def test_create_title_generated_event(self):
        event = create_title_generated_event("New Title")
        assert event["type"] == "title_generated"
        assert event["data"]["title"] == "New Title"

    def test_create_analytics_event(self):
        event = create_analytics_event({"tokens": 100, "cost": 0.002})
        assert event["type"] == "analytics"
        assert event["data"]["tokens"] == 100
        assert event["data"]["cost"] == 0.002

    def test_create_vision_observation_event(self):
        event = create_vision_observation_event({"objects": ["cat", "dog"]})
        assert event["type"] == "vision_observation"
        assert event["data"]["objects"] == ["cat", "dog"]
