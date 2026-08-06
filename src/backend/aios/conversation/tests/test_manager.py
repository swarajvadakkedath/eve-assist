"""Unit tests for ConversationManager."""

import pytest
from datetime import datetime

from aios.conversation.manager import ConversationManager
from aios.conversation.models import Message, MessageRole
from aios.conversation.exceptions import ConversationNotFoundError


class FakeAIRouter:
    async def route(self, request, **kwargs):
        return type("AIResponse", (), {
            "content": "This is a test response",
            "tokens_used": 10,
            "provider": "test",
            "model": "test-model",
            "cost": 0.0,
            "tool_calls": [],
        })()

    async def route_stream(self, request, **kwargs):
        for char in "test response":
            yield char


class FakeMemory:
    async def search(self, query, limit=10):
        return []

    async def store(self, memory):
        pass


class FakePlanner:
    async def create_plan(self, request, context=None):
        from aios.core.planner import Plan, Step
        plan = Plan(request=request)
        if "file" in request.lower():
            plan.steps = [Step(capability="file.read", params={"path": "test.txt"})]
        else:
            plan.steps = []
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


@pytest.fixture
def manager():
    return ConversationManager(
        ai_router=FakeAIRouter(),
        memory_system=FakeMemory(),
        planner=FakePlanner(),
        tool_manager=FakeToolManager(),
        context_engine=FakeContextEngine(),
    )


class FakeExecutionEngine:
    async def execute_plan(self, plan, objective, conversation_id, owner="", priority=1):
        from aios.execution.models import Execution, ExecutionStatus
        return Execution(id="exec-123", status=ExecutionStatus.COMPLETED)

    async def wait_for_execution(self, execution_id):
        pass

    async def get_execution_result(self, execution_id):
        from aios.execution.models import ExecutionResult
        return ExecutionResult(success=True)

    async def get_execution_progress(self, execution_id):
        from aios.execution.models import ExecutionProgress
        return ExecutionProgress(total_tasks=1, completed_tasks=1, percentage=100.0)

    async def stream_events(self, execution_id):
        async def _gen():
            yield {"type": "progress", "data": "task 1"}
        return _gen()


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


class TestConversationManager:
    @pytest.mark.asyncio
    async def test_create_conversation(self, manager):
        conv = await manager.create_conversation(title="Test")
        assert conv.id
        assert conv.title == "Test"

    @pytest.mark.asyncio
    async def test_get_conversation(self, manager):
        created = await manager.create_conversation(title="Test")
        fetched = await manager.get_conversation(created.id)
        assert fetched.id == created.id

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, manager):
        with pytest.raises(ConversationNotFoundError):
            await manager.get_conversation("nonexistent")

    @pytest.mark.asyncio
    async def test_list_conversations(self, manager):
        await manager.create_conversation(title="First")
        await manager.create_conversation(title="Second")
        convs = await manager.list_conversations()
        assert len(convs) >= 2

    @pytest.mark.asyncio
    async def test_delete_conversation(self, manager):
        conv = await manager.create_conversation(title="Delete Me")
        await manager.delete_conversation(conv.id)
        with pytest.raises(ConversationNotFoundError):
            await manager.get_conversation(conv.id)

    @pytest.mark.asyncio
    async def test_rename_conversation(self, manager):
        conv = await manager.create_conversation(title="Old Name")
        renamed = await manager.rename_conversation(conv.id, "New Name")
        assert renamed.title == "New Name"

    @pytest.mark.asyncio
    async def test_send_message(self, manager):
        conv = await manager.create_conversation(title="Chat")
        response = await manager.send_message(conv.id, "Hello")
        assert response.role == MessageRole.ASSISTANT
        assert response.content

    @pytest.mark.asyncio
    async def test_get_history(self, manager):
        conv = await manager.create_conversation(title="History")
        await manager.send_message(conv.id, "Message 1")
        await manager.send_message(conv.id, "Message 2")
        history = await manager.get_history(conv.id)
        assert len(history) >= 4

    @pytest.mark.asyncio
    async def test_clear_history(self, manager):
        conv = await manager.create_conversation(title="Clear")
        await manager.send_message(conv.id, "Test")
        await manager.clear_history(conv.id)
        history = await manager.get_history(conv.id)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_stream_message(self, manager):
        conv = await manager.create_conversation(title="Stream")
        events = []
        async for event in manager.stream_message(conv.id, "Hello"):
            events.append(event)
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_send_message_intent_detection(self, manager):
        conv = await manager.create_conversation(title="Intent Test")
        
        # Test question intent
        response1 = await manager.send_message(conv.id, "How are you?")
        assert response1.detected_intent == "question"
        assert response1.generated_plan is None
        
        # Test tool intent
        response2 = await manager.send_message(conv.id, "Read file test.txt")
        assert response2.detected_intent == "file"
        assert response2.generated_plan is not None
        assert "file.read" in response2.selected_capabilities

    @pytest.mark.asyncio
    async def test_stream_message_intent_detection(self, manager):
        conv = await manager.create_conversation(title="Intent Stream Test")
        
        # Test tool intent in streaming
        events = []
        async for event in manager.stream_message(conv.id, "Read file test.txt"):
            events.append(event)
        
        # Check if the final message has the intent
        history = await manager.get_history(conv.id)
        assistant_msg = next((m for m in history if m.role == MessageRole.ASSISTANT), None)
        assert assistant_msg is not None
        assert assistant_msg.detected_intent == "file"
        assert assistant_msg.generated_plan is not None
        assert "file.read" in assistant_msg.selected_capabilities

    @pytest.mark.asyncio
    async def test_send_message_execution_context(self, manager_with_execution):
        conv = await manager_with_execution.create_conversation(title="Execution Test")
        
        # Test tool intent with execution
        response = await manager_with_execution.send_message(conv.id, "Read file test.txt")
        
        assert response.execution_context is not None
        assert response.execution_context.execution_id == "exec-123"
        assert response.execution_context.status == "completed"


class CapturingAIRouter:
    """Router that captures the last request for assertion."""

    def __init__(self):
        self.last_request = None

    async def route(self, request, **kwargs):
        self.last_request = request
        return type("AIResponse", (), {
            "content": "regenerated response",
            "tokens_used": 5,
            "provider": getattr(request, "provider_id", None) or "default",
            "model": getattr(request, "model", None) or "default-model",
            "cost": 0.0,
            "tool_calls": [],
        })()

    async def route_stream(self, request, **kwargs):
        self.last_request = request
        yield "regenerated"


@pytest.fixture
def capturing_manager():
    router = CapturingAIRouter()
    return ConversationManager(
        ai_router=router,
        memory_system=FakeMemory(),
        planner=FakePlanner(),
        tool_manager=FakeToolManager(),
        context_engine=FakeContextEngine(),
    ), router


class TestRegeneratePropagation:
    """Regression: regenerate_message must propagate provider_id, model_id,
    temperature, and max_tokens from the conversation to the AI request."""

    @pytest.mark.asyncio
    async def test_regenerate_propagates_provider_id(self, capturing_manager):
        mgr, router = capturing_manager
        conv = await mgr.create_conversation(
            title="Regen Test",
            provider_id="google-test-abc123",
            model_id="gemini-2.5-flash",
        )
        await mgr.send_message(conv.id, "Hello")
        history = await mgr.get_history(conv.id)
        assistant_msg = next(m for m in history if m.role == MessageRole.ASSISTANT)

        await mgr.regenerate_message(conv.id, assistant_msg.id)

        assert router.last_request is not None
        assert getattr(router.last_request, "provider_id", None) == "google-test-abc123"

    @pytest.mark.asyncio
    async def test_regenerate_propagates_model_id(self, capturing_manager):
        mgr, router = capturing_manager
        conv = await mgr.create_conversation(
            title="Regen Model Test",
            provider_id="google-test-abc123",
            model_id="gemini-2.5-pro",
        )
        await mgr.send_message(conv.id, "Hello")
        history = await mgr.get_history(conv.id)
        assistant_msg = next(m for m in history if m.role == MessageRole.ASSISTANT)

        await mgr.regenerate_message(conv.id, assistant_msg.id)

        assert router.last_request is not None
        assert getattr(router.last_request, "model", None) == "gemini-2.5-pro"

    @pytest.mark.asyncio
    async def test_regenerate_propagates_temperature(self, capturing_manager):
        mgr, router = capturing_manager
        conv = await mgr.create_conversation(title="Regen Temp Test")
        conv.temperature = 0.3
        await mgr.send_message(conv.id, "Hello")
        history = await mgr.get_history(conv.id)
        assistant_msg = next(m for m in history if m.role == MessageRole.ASSISTANT)

        await mgr.regenerate_message(conv.id, assistant_msg.id)

        assert router.last_request is not None
        assert getattr(router.last_request, "temperature", None) == 0.3

    @pytest.mark.asyncio
    async def test_regenerate_propagates_max_tokens(self, capturing_manager):
        mgr, router = capturing_manager
        conv = await mgr.create_conversation(title="Regen MaxTokens Test")
        conv.max_tokens = 8192
        await mgr.send_message(conv.id, "Hello")
        history = await mgr.get_history(conv.id)
        assistant_msg = next(m for m in history if m.role == MessageRole.ASSISTANT)

        await mgr.regenerate_message(conv.id, assistant_msg.id)

        assert router.last_request is not None
        assert getattr(router.last_request, "max_tokens", None) == 8192

    @pytest.mark.asyncio
    async def test_regenerate_uses_defaults_when_not_set(self, capturing_manager):
        mgr, router = capturing_manager
        conv = await mgr.create_conversation(title="Regen Defaults Test")
        await mgr.send_message(conv.id, "Hello")
        history = await mgr.get_history(conv.id)
        assistant_msg = next(m for m in history if m.role == MessageRole.ASSISTANT)

        await mgr.regenerate_message(conv.id, assistant_msg.id)

        assert router.last_request is not None
        assert getattr(router.last_request, "temperature", None) == 0.7
        assert getattr(router.last_request, "max_tokens", None) == 4096

    @pytest.mark.asyncio
    async def test_regenerate_all_params_combined(self, capturing_manager):
        mgr, router = capturing_manager
        conv = await mgr.create_conversation(
            title="Full Regen Test",
            provider_id="openai-test-xyz789",
            model_id="gpt-4o",
        )
        conv.temperature = 0.5
        conv.max_tokens = 16384
        await mgr.send_message(conv.id, "Hello")
        history = await mgr.get_history(conv.id)
        assistant_msg = next(m for m in history if m.role == MessageRole.ASSISTANT)

        await mgr.regenerate_message(conv.id, assistant_msg.id)

        req = router.last_request
        assert req is not None
        assert getattr(req, "provider_id", None) == "openai-test-xyz789"
        assert getattr(req, "model", None) == "gpt-4o"
        assert getattr(req, "temperature", None) == 0.5
        assert getattr(req, "max_tokens", None) == 16384


class TestSendMemoryUpdate:
    """Regression: send_message must pass assistant response content to
    _safe_update_memory, not reference an out-of-scope ai_response variable."""

    @pytest.mark.asyncio
    async def test_send_message_no_name_error(self, manager):
        """send_message must not raise NameError on ai_response."""
        conv = await manager.create_conversation(title="NameError Test")
        response = await manager.send_message(conv.id, "Hello")
        assert response.role == MessageRole.ASSISTANT
        assert response.content == "This is a test response"

    @pytest.mark.asyncio
    async def test_safe_update_memory_receives_response_content(self, manager):
        """_safe_update_memory must receive the AI response content."""
        update_calls = []
        original = manager._safe_update_memory

        async def capturing_update(user_input, response, conversation_id):
            update_calls.append({"user_input": user_input, "response": response})
            await original(user_input, response, conversation_id)

        manager._safe_update_memory = capturing_update
        conv = await manager.create_conversation(title="Memory Test")
        await manager.send_message(conv.id, "Hello")

        assert len(update_calls) == 1
        assert update_calls[0]["user_input"] == "Hello"
        assert update_calls[0]["response"] == "This is a test response"

    @pytest.mark.asyncio
    async def test_conversation_history_unchanged(self, manager):
        """send_message stores correct messages in history."""
        conv = await manager.create_conversation(title="History Test")
        await manager.send_message(conv.id, "Hello")
        history = await manager.get_history(conv.id)

        roles = [m.role for m in history]
        assert MessageRole.USER in roles
        assert MessageRole.ASSISTANT in roles

    @pytest.mark.asyncio
    async def test_stream_message_still_works(self, manager):
        """Streaming path remains unaffected."""
        conv = await manager.create_conversation(title="Stream Test")
        events = []
        async for event in manager.stream_message(conv.id, "Hello"):
            events.append(event)
        assert len(events) > 0
