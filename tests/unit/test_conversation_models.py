"""Tests for conversation data models."""

import pytest
from datetime import datetime
from uuid import UUID

from aios.conversation.models import (
    Conversation,
    Message,
    Session,
    ToolCall,
    EditEntry,
    PlanningContext,
    ExecutionContext,
    MessageRole,
    ToolCallStatus,
    StreamEventType,
    StreamEvent,
)


class TestMessageRole:
    def test_values(self):
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.TOOL.value == "tool"

    def test_from_string(self):
        assert MessageRole("user") == MessageRole.USER


class TestToolCallStatus:
    def test_values(self):
        assert ToolCallStatus.PENDING.value == "pending"
        assert ToolCallStatus.RUNNING.value == "running"
        assert ToolCallStatus.SUCCESS.value == "success"
        assert ToolCallStatus.FAILED.value == "failed"
        assert ToolCallStatus.CANCELLED.value == "cancelled"


class TestStreamEventType:
    def test_values(self):
        assert StreamEventType.TOKEN.value == "token"
        assert StreamEventType.DONE.value == "done"
        assert StreamEventType.ERROR.value == "error"
        assert StreamEventType.TOOL_CALL.value == "tool_call"
        assert StreamEventType.TOOL_RESULT.value == "tool_result"
        assert StreamEventType.STATUS.value == "status"
        assert StreamEventType.PLANNER_STARTED.value == "planner_started"
        assert StreamEventType.PLANNER_COMPLETED.value == "planner_completed"
        assert StreamEventType.MEMORY_RETRIEVAL.value == "memory_retrieval"
        assert StreamEventType.TOOL_REQUESTED.value == "tool_requested"
        assert StreamEventType.TOOL_RUNNING.value == "tool_running"
        assert StreamEventType.TOOL_COMPLETED.value == "tool_completed"
        assert StreamEventType.CONTEXT_LOADED.value == "context_loaded"
        assert StreamEventType.FINAL_RESPONSE.value == "final_response"
        assert StreamEventType.TITLE_GENERATED.value == "title_generated"
        assert StreamEventType.ANALYTICS.value == "analytics"
        assert StreamEventType.VISION_OBSERVATION.value == "vision_observation"


class TestToolCallModel:
    def test_create_tool_call(self):
        tc = ToolCall(tool_name="file.read", capability="file.read", parameters={"path": "/tmp/test"})
        assert tc.status == ToolCallStatus.PENDING
        assert tc.execution_time == 0.0
        assert tc.result is None

    def test_tool_call_status_string_conversion(self):
        tc = ToolCall(status="success")
        assert tc.status == ToolCallStatus.SUCCESS

    def test_tool_call_with_result(self):
        tc = ToolCall(tool_name="file.read", status="success", result={"content": "test"}, execution_time=0.5)
        assert tc.result["content"] == "test"
        assert tc.execution_time == 0.5

    def test_tool_call_defaults(self):
        tc = ToolCall()
        assert tc.tool_name == ""
        assert tc.capability == ""
        assert tc.parameters == {}
        assert tc.status == ToolCallStatus.PENDING


class TestEditEntry:
    def test_create_edit_entry(self):
        now = datetime.utcnow()
        entry = EditEntry(original_content="old", edited_content="new", timestamp=now)
        assert entry.original_content == "old"
        assert entry.edited_content == "new"
        assert entry.timestamp == now
        assert entry.regenerated is False

    def test_edit_entry_regenerated(self):
        entry = EditEntry(original_content="old", edited_content="new", timestamp=datetime.utcnow(), regenerated=True)
        assert entry.regenerated is True


class TestPlanningContext:
    def test_defaults(self):
        ctx = PlanningContext()
        assert ctx.intent is None
        assert ctx.plan is None
        assert ctx.selected_capabilities == []
        assert ctx.planning_time_ms is None
        assert ctx.planner_version is None

    def test_with_values(self):
        ctx = PlanningContext(intent="file", selected_capabilities=["file.read", "file.write"], planning_time_ms=150.0)
        assert ctx.intent == "file"
        assert len(ctx.selected_capabilities) == 2
        assert ctx.planning_time_ms == 150.0


class TestExecutionContext:
    def test_defaults(self):
        ctx = ExecutionContext()
        assert ctx.execution_id is None
        assert ctx.status is None
        assert ctx.current_step == 0
        assert ctx.completed_steps == 0
        assert ctx.total_steps == 0
        assert ctx.progress == 0.0
        assert ctx.cancelled is False
        assert ctx.tools_executed == []
        assert ctx.capabilities_used == []

    def test_with_values(self):
        ctx = ExecutionContext(
            execution_id="exec-1",
            status="completed",
            current_step=2,
            completed_steps=3,
            total_steps=5,
            progress=60.0,
            error="timeout on step 4",
        )
        assert ctx.execution_id == "exec-1"
        assert ctx.status == "completed"
        assert ctx.current_step == 2
        assert ctx.completed_steps == 3
        assert ctx.progress == 60.0
        assert ctx.error == "timeout on step 4"


class TestMessageModel:
    def test_create_user_message(self):
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.id
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.timestamp is not None
        assert msg.tool_calls == []
        assert msg.tokens_used == 0

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

    def test_message_default_id_generation(self):
        msg = Message(role=MessageRole.USER, content="test")
        assert len(msg.id) == 32

    def test_message_custom_id(self):
        msg = Message(id="msg-custom", role=MessageRole.USER, content="test")
        assert msg.id == "msg-custom"

    def test_message_with_edit_history(self):
        msg = Message(role=MessageRole.USER, content="edited")
        entry = EditEntry(original_content="original", edited_content="edited", timestamp=datetime.utcnow())
        msg.edit_history.append(entry)
        assert len(msg.edit_history) == 1
        assert msg.edit_history[0].original_content == "original"

    def test_message_with_planning_context(self):
        ctx = PlanningContext(intent="question")
        msg = Message(role=MessageRole.USER, content="What?", planning_context=ctx)
        assert msg.detected_intent == "question"
        assert msg.generated_plan is None
        assert msg.selected_capabilities == []

    def test_message_with_execution_context(self):
        ctx = ExecutionContext(execution_id="exec-1")
        msg = Message(role=MessageRole.ASSISTANT, content="Done", execution_context=ctx)
        assert msg.execution_context.execution_id == "exec-1"

    def test_message_with_attachments(self):
        msg = Message(role=MessageRole.USER, content="See this", attachments=[{"type": "image", "path": "/img.png"}])
        assert len(msg.attachments) == 1
        assert msg.attachments[0]["type"] == "image"

    def test_message_default_latency(self):
        msg = Message(role=MessageRole.USER, content="test")
        assert msg.latency_ms == 0.0

    def test_message_default_is_regenerated(self):
        msg = Message(role=MessageRole.USER, content="test")
        assert msg.is_regenerated is False

    def test_message_tool_results_default(self):
        msg = Message(role=MessageRole.USER, content="test")
        assert msg.tool_results == []

    def test_message_metadata_default(self):
        msg = Message(role=MessageRole.USER, content="test")
        assert msg.metadata == {}


class TestConversationModel:
    def test_create_conversation(self):
        conv = Conversation(title="Test Chat")
        assert conv.id
        assert conv.title == "Test Chat"
        assert conv.created_at is not None
        assert conv.updated_at is not None
        assert conv.is_active is True
        assert conv.message_count == 0
        assert conv.mode == "chat"

    def test_conversation_default_id(self):
        conv = Conversation()
        assert len(conv.id) == 32

    def test_conversation_custom_id(self):
        conv = Conversation(id="custom-id")
        assert conv.id == "custom-id"

    def test_conversation_with_project(self):
        conv = Conversation(title="Project Chat", active_project="/path/to/project")
        assert conv.active_project == "/path/to/project"

    def test_conversation_is_branch_by_parent(self):
        conv = Conversation(title="Branch", parent_id="parent-123")
        assert conv.is_branch is True

    def test_conversation_is_branch_by_metadata(self):
        conv = Conversation(title="Branch", metadata={"is_branch": True})
        assert conv.is_branch is True

    def test_conversation_is_not_branch(self):
        conv = Conversation(title="Main")
        assert conv.is_branch is False

    def test_conversation_title_is_custom(self):
        conv = Conversation(title="Custom", metadata={"title_is_custom": True})
        assert conv.title_is_custom is True

    def test_conversation_title_not_custom(self):
        conv = Conversation(title="Default")
        assert conv.title_is_custom is False

    def test_conversation_update_timestamps(self):
        conv = Conversation(title="Test")
        old_updated = conv.updated_at
        conv.updated_at = datetime.utcnow()
        assert conv.updated_at >= old_updated

    def test_conversation_metadata_mutable(self):
        conv = Conversation(title="Test")
        conv.metadata["custom_key"] = "custom_value"
        assert conv.metadata["custom_key"] == "custom_value"


class TestSessionModel:
    def test_create_session(self):
        session = Session(conversation_id="conv-1")
        assert session.session_id
        assert session.conversation_id == "conv-1"
        assert session.created_at is not None
        assert session.active_capabilities == []

    def test_session_with_context(self):
        session = Session(conversation_id="conv-1", current_context={"app": "vscode"})
        assert session.current_context["app"] == "vscode"

    def test_session_with_capabilities(self):
        session = Session(conversation_id="conv-1", active_capabilities=["file.read", "file.write"])
        assert len(session.active_capabilities) == 2

    def test_session_default_expiry(self):
        session = Session(conversation_id="conv-1")
        assert session.expires_at is None

    def test_session_memory_reference_default(self):
        session = Session(conversation_id="conv-1")
        assert session.memory_reference == {}

    def test_session_planner_state_default(self):
        session = Session(conversation_id="conv-1")
        assert session.planner_state == {}


class TestStreamEvent:
    def test_create_stream_event(self):
        event = StreamEvent(type=StreamEventType.TOKEN, data={"token": "hello"})
        assert event.type == StreamEventType.TOKEN
        assert event.data["token"] == "hello"

    def test_stream_event_string_type(self):
        event = StreamEvent(type="token", data={"token": "hello"})
        assert event.type == "token"
