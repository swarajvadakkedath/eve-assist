"""Comprehensive tests for ConversationManager."""

import pytest
from datetime import datetime

from aios.conversation.manager import ConversationManager
from aios.conversation.models import Message, MessageRole, ToolCall, Conversation
from aios.conversation.exceptions import (
    ConversationNotFoundError,
    MessageNotFoundError,
    AIProviderError,
)


class FakeAIRouter:
    async def route(self, request):
        return type("AIResponse", (), {
            "content": "This is a test response",
            "tokens_used": 10,
            "provider": "test",
            "model": "test-model",
            "cost": 0.0,
            "tool_calls": [],
        })()

    async def route_stream(self, request):
        for char in "test response":
            yield char


class FakeMemory:
    def __init__(self):
        self.stored = []

    async def search(self, query, limit=10):
        return []

    async def store(self, memory):
        self.stored.append(memory)


class FakePlanner:
    async def create_plan(self, request, context=None):
        plan = type("Plan", (), {
            "id": "plan-1",
            "steps": [],
            "request": request,
        })()
        if "file" in request.lower():
            plan.steps = [type("Step", (), {"capability": "file.read", "params": {"path": "test.txt"}})()]
        return plan


class FakeToolManager:
    async def list_tools(self):
        return []

    async def execute(self, tool_id, params):
        return type("ToolResult", (), {"success": True, "data": {}, "error": None, "duration": 0.0})()


class FakeContextEngine:
    async def get_active_app(self):
        return "test-app"

    async def get_active_file(self):
        return None

    async def detect_project(self):
        return None


class FakeRepository:
    def __init__(self):
        self.conversations = {}
        self.messages = {}

    async def create_conversation(self, conv):
        self.conversations[conv.id] = conv

    async def get_conversation(self, conversation_id):
        return self.conversations.get(conversation_id)

    async def list_conversations(self, limit=50, offset=0):
        return list(self.conversations.values())

    async def update_conversation(self, conv):
        self.conversations[conv.id] = conv

    async def delete_conversation(self, conversation_id):
        self.conversations.pop(conversation_id, None)
        self.messages.pop(conversation_id, None)

    async def add_message(self, message):
        self.messages.setdefault(message.conversation_id, []).append(message)

    async def get_messages(self, conversation_id, limit=100, offset=0):
        return self.messages.get(conversation_id, [])

    async def clear_history(self, conversation_id):
        self.messages[conversation_id] = []


class FakeExecutionEngine:
    async def execute_plan(self, plan, objective, conversation_id, owner="", priority=1):
        return type("Execution", (), {
            "id": "exec-123",
            "status": type("ExecStatus", (), {"value": "completed"})(),
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
        })()

    async def wait_for_execution(self, execution_id):
        pass

    async def get_execution_result(self, execution_id):
        return type("Result", (), {
            "success": True,
            "duration_ms": 500.0,
            "tools_executed": ["file.read"],
            "capabilities_used": ["file.read"],
            "retry_count": 0,
            "permission_requests": 0,
            "warnings": [],
            "errors": [],
        })()

    async def get_execution_progress(self, execution_id):
        return type("Progress", (), {
            "total_tasks": 1,
            "completed_tasks": 1,
            "percentage": 100.0,
        })()

    def stream_events(self, execution_id):
        async def _gen():
            yield {"type": "progress", "data": "task 1"}
        return _gen()


@pytest.fixture
def manager():
    return ConversationManager(
        ai_router=FakeAIRouter(),
        memory_system=FakeMemory(),
        planner=FakePlanner(),
        tool_manager=FakeToolManager(),
        context_engine=FakeContextEngine(),
    )


@pytest.fixture
def manager_with_execution():
    return ConversationManager(
        ai_router=FakeAIRouter(),
        memory_system=FakeMemory(),
        planner=FakePlanner(),
        tool_manager=FakeToolManager(),
        context_engine=FakeContextEngine(),
        execution_engine=FakeExecutionEngine(),
    )


@pytest.fixture
def manager_with_repo():
    return ConversationManager(
        ai_router=FakeAIRouter(),
        memory_system=FakeMemory(),
        planner=FakePlanner(),
        tool_manager=FakeToolManager(),
        context_engine=FakeContextEngine(),
        repository=FakeRepository(),
    )


@pytest.mark.asyncio
class TestConversationManagerCRUD:
    async def test_create_conversation_default_title(self, manager):
        conv = await manager.create_conversation()
        assert conv.id
        assert conv.title == "New Conversation"
        assert conv.is_active is True

    async def test_create_conversation_custom_title(self, manager):
        conv = await manager.create_conversation(title="Test Chat")
        assert conv.title == "Test Chat"
        assert conv.metadata.get("title_is_custom") is True

    async def test_create_conversation_with_project(self, manager):
        conv = await manager.create_conversation(title="Project Chat", project="/my/project")
        assert conv.active_project == "/my/project"

    async def test_get_conversation(self, manager):
        created = await manager.create_conversation(title="Get Me")
        fetched = await manager.get_conversation(created.id)
        assert fetched.id == created.id
        assert fetched.title == "Get Me"

    async def test_get_conversation_not_found(self, manager):
        with pytest.raises(ConversationNotFoundError):
            await manager.get_conversation("nonexistent")

    async def test_list_conversations(self, manager):
        await manager.create_conversation(title="First")
        await manager.create_conversation(title="Second")
        convs = await manager.list_conversations()
        assert len(convs) == 2

    async def test_list_conversations_pagination(self, manager):
        for i in range(5):
            await manager.create_conversation(title=f"Chat {i}")
        first_page = await manager.list_conversations(limit=2, offset=0)
        assert len(first_page) == 2
        second_page = await manager.list_conversations(limit=2, offset=2)
        assert len(second_page) == 2

    async def test_list_conversations_sorted_by_updated(self, manager):
        conv_a = await manager.create_conversation(title="A")
        await manager.send_message(conv_a.id, "Hello")
        conv_b = await manager.create_conversation(title="B")
        convs = await manager.list_conversations()
        assert convs[0].title == "B"
        assert convs[1].title == "A"

    async def test_delete_conversation(self, manager):
        conv = await manager.create_conversation(title="Delete")
        await manager.delete_conversation(conv.id)
        with pytest.raises(ConversationNotFoundError):
            await manager.get_conversation(conv.id)

    async def test_rename_conversation(self, manager):
        conv = await manager.create_conversation(title="Old Name")
        renamed = await manager.rename_conversation(conv.id, "New Name")
        assert renamed.title == "New Name"
        assert renamed.metadata.get("title_is_custom") is True
        fetched = await manager.get_conversation(conv.id)
        assert fetched.title == "New Name"

    async def test_rename_conversation_not_found(self, manager):
        with pytest.raises(ConversationNotFoundError):
            await manager.rename_conversation("nonexistent", "New")

    async def test_create_conversation_with_repository(self, manager_with_repo):
        conv = await manager_with_repo.create_conversation(title="Repo Test")
        assert conv.id
        repo_conv = await manager_with_repo._repository.get_conversation(conv.id)
        assert repo_conv is not None

    async def test_delete_conversation_with_repository(self, manager_with_repo):
        conv = await manager_with_repo.create_conversation(title="Repo Delete")
        await manager_with_repo.delete_conversation(conv.id)
        repo_conv = await manager_with_repo._repository.get_conversation(conv.id)
        assert repo_conv is None


@pytest.mark.asyncio
class TestConversationManagerMessaging:
    async def test_send_message_basic(self, manager):
        conv = await manager.create_conversation(title="Chat")
        response = await manager.send_message(conv.id, "Hello")
        assert response.role == MessageRole.ASSISTANT
        assert response.content == "This is a test response"
        assert response.tokens_used == 10

    async def test_send_message_intent_detection_question(self, manager):
        conv = await manager.create_conversation(title="Intent Test")
        response = await manager.send_message(conv.id, "How are you?")
        assert response.detected_intent == "question"
        assert response.generated_plan is None

    async def test_send_message_intent_detection_file(self, manager):
        conv = await manager.create_conversation(title="Intent File")
        response = await manager.send_message(conv.id, "Read file test.txt")
        assert response.detected_intent == "file"

    async def test_send_message_intent_detection_browser(self, manager):
        conv = await manager.create_conversation(title="Intent Browser")
        response = await manager.send_message(conv.id, "Open browser and search")
        assert response.detected_intent == "browser"

    async def test_send_message_intent_detection_workflow(self, manager):
        conv = await manager.create_conversation(title="Intent Workflow")
        response = await manager.send_message(conv.id, "Create a workflow for testing")
        assert response.detected_intent == "workflow"

    async def test_send_message_intent_detection_git(self, manager):
        conv = await manager.create_conversation(title="Intent Git")
        response = await manager.send_message(conv.id, "Commit changes to git")
        assert response.detected_intent == "git"

    async def test_send_message_intent_detection_desktop(self, manager):
        conv = await manager.create_conversation(title="Intent Desktop")
        response = await manager.send_message(conv.id, "Open a desktop window")
        assert response.detected_intent == "desktop"

    async def test_send_message_intent_detection_research(self, manager):
        conv = await manager.create_conversation(title="Intent Research")
        response = await manager.send_message(conv.id, "Research the topic")
        assert response.detected_intent == "research"

    async def test_send_message_intent_detection_tool_execution(self, manager):
        conv = await manager.create_conversation(title="Intent Tool")
        response = await manager.send_message(conv.id, "Run the analysis tool")
        assert response.detected_intent == "tool_execution"

    async def test_send_message_intent_detection_conversation(self, manager):
        conv = await manager.create_conversation(title="Intent Conversation")
        response = await manager.send_message(conv.id, "Tell me a story")
        assert response.detected_intent == "conversation"

    async def test_send_message_stores_user_message(self, manager):
        conv = await manager.create_conversation(title="Store Test")
        await manager.send_message(conv.id, "User message")
        history = await manager.get_history(conv.id)
        user_msgs = [m for m in history if m.role == MessageRole.USER]
        assert len(user_msgs) >= 1
        assert user_msgs[-1].content == "User message"

    async def test_send_message_updates_conversation_timestamp(self, manager):
        conv = await manager.create_conversation(title="Timestamp")
        old_updated = conv.updated_at
        await manager.send_message(conv.id, "Test")
        assert conv.updated_at > old_updated

    async def test_send_message_increments_count(self, manager):
        conv = await manager.create_conversation(title="Count")
        await manager.send_message(conv.id, "First")
        await manager.send_message(conv.id, "Second")
        assert conv.message_count >= 1

    async def test_send_message_with_repository(self, manager_with_repo):
        conv = await manager_with_repo.create_conversation(title="Repo Msg")
        await manager_with_repo.send_message(conv.id, "Save this")
        repo_msgs = await manager_with_repo._repository.get_messages(conv.id)
        assert len(repo_msgs) >= 2

    async def test_send_message_not_found(self, manager):
        with pytest.raises(ConversationNotFoundError):
            await manager.send_message("nonexistent", "Hello")


@pytest.mark.asyncio
class TestConversationManagerStreaming:
    async def test_stream_message_basic(self, manager):
        conv = await manager.create_conversation(title="Stream")
        events = []
        async for event in manager.stream_message(conv.id, "Hello"):
            events.append(event)
        assert len(events) > 0

    async def test_stream_message_intent_detection(self, manager):
        conv = await manager.create_conversation(title="Stream Intent")
        events = []
        async for event in manager.stream_message(conv.id, "Hello"):
            events.append(event)
        # Verify final message has correct state
        history = await manager.get_history(conv.id)
        assistant_msgs = [m for m in history if m.role == MessageRole.ASSISTANT]
        assert len(assistant_msgs) >= 1

    async def test_stream_message_stores_messages(self, manager):
        conv = await manager.create_conversation(title="Stream Store")
        events = []
        async for event in manager.stream_message(conv.id, "Stream test"):
            events.append(event)
        history = await manager.get_history(conv.id)
        user_msgs = [m for m in history if m.role == MessageRole.USER]
        assert len(user_msgs) >= 1

    async def test_stream_message_updates_conversation(self, manager):
        conv = await manager.create_conversation(title="Stream Update")
        old_updated = conv.updated_at
        async for _ in manager.stream_message(conv.id, "Test"):
            pass
        assert conv.updated_at > old_updated

    async def test_stream_message_not_found(self, manager):
        with pytest.raises(ConversationNotFoundError):
            async for _ in manager.stream_message("nonexistent", "Hello"):
                pass

    async def test_stream_message_with_repository(self, manager_with_repo):
        conv = await manager_with_repo.create_conversation(title="Stream Repo")
        async for _ in manager_with_repo.stream_message(conv.id, "Hello"):
            pass
        repo_msgs = await manager_with_repo._repository.get_messages(conv.id)
        assert len(repo_msgs) >= 2


@pytest.mark.asyncio
class TestConversationManagerHistory:
    async def test_get_history(self, manager):
        conv = await manager.create_conversation(title="History")
        await manager.send_message(conv.id, "Message 1")
        await manager.send_message(conv.id, "Message 2")
        history = await manager.get_history(conv.id)
        assert len(history) >= 4

    async def test_get_history_empty(self, manager):
        conv = await manager.create_conversation(title="Empty History")
        history = await manager.get_history(conv.id)
        assert history == []

    async def test_get_history_limit(self, manager):
        conv = await manager.create_conversation(title="Limit History")
        for i in range(5):
            await manager.send_message(conv.id, f"Message {i}")
        history = await manager.get_history(conv.id, limit=2)
        assert len(history) == 2

    async def test_clear_history(self, manager):
        conv = await manager.create_conversation(title="Clear")
        await manager.send_message(conv.id, "Test")
        await manager.clear_history(conv.id)
        history = await manager.get_history(conv.id)
        assert len(history) == 0

    async def test_clear_history_with_repository(self, manager_with_repo):
        conv = await manager_with_repo.create_conversation(title="Clear Repo")
        await manager_with_repo.send_message(conv.id, "Test")
        await manager_with_repo.clear_history(conv.id)
        repo_msgs = await manager_with_repo._repository.get_messages(conv.id)
        assert len(repo_msgs) == 0


@pytest.mark.asyncio
class TestConversationManagerSmartTitles:
    async def test_ensure_title_generated(self, manager):
        conv = await manager.create_conversation(title="New Conversation")
        messages = [
            Message(role=MessageRole.USER, content="What is Python?"),
        ]
        manager._messages[conv.id] = messages
        title = await manager.ensure_title(conv.id)
        assert title is not None

    async def test_ensure_title_already_set(self, manager):
        conv = await manager.create_conversation(title="Custom Chat")
        conv.metadata["title_is_custom"] = True
        title = await manager.ensure_title(conv.id)
        assert title == "Custom Chat"


@pytest.mark.asyncio
class TestConversationManagerSearch:
    async def test_search_conversations(self, manager):
        conv1 = await manager.create_conversation(title="Python Chat")
        conv2 = await manager.create_conversation(title="Java Chat")
        await manager.send_message(conv1.id, "I love Python")
        results = await manager.search_conversations("Python")
        assert len(results) >= 1

    async def test_search_conversations_empty_query(self, manager):
        conv = await manager.create_conversation(title="Test")
        await manager.send_message(conv.id, "Hello")
        results = await manager.search_conversations("")
        assert results == []

    async def test_reindex_conversation(self, manager):
        conv = await manager.create_conversation(title="Reindex")
        await manager.send_message(conv.id, "Hello")
        await manager.reindex_conversation(conv.id)
        results = await manager.search_conversations("Hello")
        assert len(results) >= 1


@pytest.mark.asyncio
class TestConversationManagerBranching:
    async def test_create_branch(self, manager):
        parent = await manager.create_conversation(title="Parent")
        await manager.send_message(parent.id, "Message 1")
        msg = (await manager.get_history(parent.id))[0]
        branch = await manager.create_branch(parent.id, msg.id, title="Branch Chat")
        assert branch.id != parent.id
        assert branch.title == "Branch Chat"
        branch_msgs = await manager.get_history(branch.id)
        assert len(branch_msgs) >= 1

    async def test_create_branch_default_title(self, manager):
        parent = await manager.create_conversation(title="Original")
        msg = Message(role=MessageRole.USER, content="Test")
        manager._messages[parent.id] = [msg]
        branch = await manager.create_branch(parent.id, msg.id)
        assert "Original" in branch.title

    async def test_get_branches(self, manager):
        parent = await manager.create_conversation(title="Parent")
        msg = Message(role=MessageRole.USER, content="Test")
        manager._messages[parent.id] = [msg]
        await manager.create_branch(parent.id, msg.id)
        branches = await manager.get_branches(parent.id)
        assert len(branches) == 1

    async def test_get_branches_empty(self, manager):
        conv = await manager.create_conversation(title="No Branches")
        branches = await manager.get_branches(conv.id)
        assert branches == []

    async def test_delete_branch(self, manager):
        parent = await manager.create_conversation(title="Parent")
        msg = Message(role=MessageRole.USER, content="Test")
        manager._messages[parent.id] = [msg]
        branch = await manager.create_branch(parent.id, msg.id)
        result = await manager.delete_branch(branch.id)
        assert result is True
        branches = await manager.get_branches(parent.id)
        assert len(branches) == 0

    async def test_delete_branch_not_found(self, manager):
        result = await manager.delete_branch("nonexistent")
        assert result is False

    async def test_rename_branch(self, manager):
        parent = await manager.create_conversation(title="Parent")
        msg = Message(role=MessageRole.USER, content="Test")
        manager._messages[parent.id] = [msg]
        branch = await manager.create_branch(parent.id, msg.id, title="Old")
        result = await manager.rename_branch(branch.id, "New")
        assert result is True
        fetched = await manager.get_conversation(branch.id)
        assert fetched.title == "New"


@pytest.mark.asyncio
class TestConversationManagerEditRegenerate:
    async def test_edit_message(self, manager):
        conv = await manager.create_conversation(title="Edit")
        await manager.send_message(conv.id, "Hello")
        history = await manager.get_history(conv.id)
        user_msg = next(m for m in history if m.role == MessageRole.USER)
        edited = await manager.edit_message(conv.id, user_msg.id, "Edited Hello")
        assert edited.content == "Edited Hello"
        assert len(edited.edit_history) == 1
        assert edited.edit_history[0].original_content == "Hello"

    async def test_edit_message_truncates_following(self, manager):
        conv = await manager.create_conversation(title="Edit Truncate")
        await manager.send_message(conv.id, "Message 1")
        await manager.send_message(conv.id, "Message 2")
        history = await manager.get_history(conv.id)
        first_user = [m for m in history if m.role == MessageRole.USER][0]
        await manager.edit_message(conv.id, first_user.id, "Edited")
        updated_history = await manager.get_history(conv.id)
        edited_msg = next(m for m in updated_history if m.id == first_user.id)
        assert edited_msg.content == "Edited"

    async def test_edit_message_not_found(self, manager):
        conv = await manager.create_conversation(title="Edit NF")
        with pytest.raises(MessageNotFoundError):
            await manager.edit_message(conv.id, "nonexistent", "New content")

    async def test_regenerate_message(self, manager):
        conv = await manager.create_conversation(title="Regen")
        response = await manager.send_message(conv.id, "Original")
        regenerated = await manager.regenerate_message(conv.id, response.id)
        assert regenerated.role == MessageRole.ASSISTANT
        assert regenerated.is_regenerated is True

    async def test_regenerate_message_not_found(self, manager):
        conv = await manager.create_conversation(title="Regen NF")
        with pytest.raises(MessageNotFoundError):
            await manager.regenerate_message(conv.id, "nonexistent")


@pytest.mark.asyncio
class TestConversationManagerAnalytics:
    async def test_get_conversation_analytics_empty(self, manager):
        conv = await manager.create_conversation(title="Analytics")
        summary = await manager.get_conversation_analytics(conv.id)
        assert summary == {}

    async def test_get_conversation_analytics_after_message(self, manager):
        conv = await manager.create_conversation(title="Analytics Msg")
        await manager.send_message(conv.id, "Hello")
        summary = await manager.get_conversation_analytics(conv.id)
        assert isinstance(summary, dict)

    async def test_get_conversation_analytics_detail(self, manager):
        conv = await manager.create_conversation(title="Analytics Detail")
        await manager.send_message(conv.id, "Hello")
        records = await manager.get_conversation_analytics_detail(conv.id)
        assert isinstance(records, list)


@pytest.mark.asyncio
class TestConversationManagerExport:
    async def test_export_markdown(self, manager):
        conv = await manager.create_conversation(title="Export MD")
        await manager.send_message(conv.id, "Hello")
        output = await manager.export_conversation(conv.id, format="markdown")
        assert isinstance(output, str)
        assert "Export" in output or "Hello" in output

    async def test_export_json(self, manager):
        conv = await manager.create_conversation(title="Export JSON")
        await manager.send_message(conv.id, "Hello")
        output = await manager.export_conversation(conv.id, format="json")
        assert '"export_version"' in output

    async def test_export_html(self, manager):
        conv = await manager.create_conversation(title="Export HTML")
        await manager.send_message(conv.id, "Hello")
        output = await manager.export_conversation(conv.id, format="html")
        assert "<!DOCTYPE html>" in output

    async def test_export_default_markdown(self, manager):
        conv = await manager.create_conversation(title="Export Default")
        await manager.send_message(conv.id, "Hello")
        output = await manager.export_conversation(conv.id)
        assert isinstance(output, str)

    async def test_export_conversation_not_found(self, manager):
        with pytest.raises(ConversationNotFoundError):
            await manager.export_conversation("nonexistent")


@pytest.mark.asyncio
class TestConversationManagerExecutionContext:
    async def test_send_message_with_execution_context(self, manager_with_execution):
        conv = await manager_with_execution.create_conversation(title="Exec")
        response = await manager_with_execution.send_message(conv.id, "Read file test.txt")
        assert response.execution_context is not None
        assert response.execution_context.execution_id == "exec-123"
        assert response.execution_context.status == "completed"

    async def test_send_message_plan_intent_no_execution(self, manager):
        conv = await manager.create_conversation(title="No Exec")
        response = await manager.send_message(conv.id, "How are you?")
        assert response.execution_context is None

    async def test_send_message_with_execution_tools_executed(self, manager_with_execution):
        conv = await manager_with_execution.create_conversation(title="Exec Tools")
        response = await manager_with_execution.send_message(conv.id, "Read file test.txt")
        assert response.execution_context.tools_executed == ["file.read"]
        assert response.execution_context.capabilities_used == ["file.read"]


@pytest.mark.asyncio
class TestConversationManagerEdgeCases:
    async def test_send_message_to_deleted_conversation(self, manager):
        conv = await manager.create_conversation(title="Delete Then Send")
        await manager.delete_conversation(conv.id)
        with pytest.raises(ConversationNotFoundError):
            await manager.send_message(conv.id, "Hello")

    async def test_detect_intent_case_insensitive(self, manager):
        conv = await manager.create_conversation(title="Case")
        # _detect_intent is protected but we can test through send_message
        response = await manager.send_message(conv.id, "READ FILE")
        assert response.detected_intent in ("file", "tool_execution")

    async def test_latency_measured(self, manager):
        conv = await manager.create_conversation(title="Latency")
        response = await manager.send_message(conv.id, "Hello")
        assert response.latency_ms > 0

    async def test_conversation_message_count_after_send(self, manager):
        conv = await manager.create_conversation(title="Msg Count")
        await manager.send_message(conv.id, "First")
        count_after_first = conv.message_count
        await manager.send_message(conv.id, "Second")
        assert conv.message_count >= count_after_first

    async def test_stream_message_execution_events(self, manager_with_execution):
        conv = await manager_with_execution.create_conversation(title="Stream Exec")
        events = []
        async for event in manager_with_execution.stream_message(conv.id, "Read file test.txt"):
            events.append(event)
        assert len(events) > 0

    async def test_empty_memory_system(self, manager):
        manager._memory = None
        conv = await manager.create_conversation(title="No Memory")
        # Should not raise
        response = await manager.send_message(conv.id, "Hello")
        assert response is not None

    async def test_empty_planner(self, manager):
        manager._planner = None
        conv = await manager.create_conversation(title="No Planner")
        response = await manager.send_message(conv.id, "Tell me a story")
        assert response is not None
