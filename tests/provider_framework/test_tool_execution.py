"""Focused regression tests for end-to-end LLM tool execution.

Proves the full tool-calling path is intact:
  1. Tool definitions (from the existing ToolManager registry) are present
     on the AIRequest built by ConversationManager._run_tool_loop.
  2. stream_message() uses the identical mechanism.
  3. SmartRouter converts the AIRequest into a ChatRequest whose ``tools``
     list is populated (and ``tool_choice`` is carried through).
  4. The OpenAI-compatible adapter serializes tools + tool_choice into the
     outbound request payload.
  5. tool_calls returned by the provider are parsed by the tool loop.
  6. ToolMediator executes the requested tool through the real registry.
  7. The ToolResult is fed back to the LLM as a role="tool" message.
  8. The final response is natural language, not raw <tool_call> markup.
"""

import json
import pytest
from unittest.mock import MagicMock

import httpx

from aios.conversation.manager import ConversationManager
from aios.conversation.models import MessageRole
from aios.core.adapters.base import ChatRequest
from aios.core.adapters.openai_compatible_adapter import OpenAICompatibleAdapter
from aios.core.smart_router import SmartRouter
from aios.core.tool_manager import ToolContract, ToolManager
from aios.core.permission_manager import PermissionManager
from aios.mediation.tools import ToolMediator


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

TOOL_DEF = {
    "type": "function",
    "function": {
        "name": "file.read",
        "description": "Read the contents of a file",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
}

TOOL_CALL = {
    "id": "call_1",
    "type": "function",
    "function": {"name": "file.read", "arguments": '{"path": "test.txt"}'},
}


async def build_real_registry():
    """Real ToolManager + one registered tool (the existing registry)."""
    tm = ToolManager(PermissionManager())
    executed = {"calls": []}

    async def read_file(params):
        executed["calls"].append(params)
        return {"content": f"hello from {params.get('path')}"}

    await tm.register_tool(
        ToolContract(
            id="file.read",
            name="file.read",
            description="Read the contents of a file",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            category="file",
        ),
        handler=read_file,
    )
    return tm, executed


def make_conv(**kwargs):
    conv = MagicMock()
    conv.max_tokens = kwargs.get("max_tokens", 4096)
    conv.temperature = kwargs.get("temperature", 0.7)
    conv.provider_id = kwargs.get("provider_id")
    conv.model_id = kwargs.get("model_id")
    conv.routing_policy = kwargs.get("routing_policy")
    return conv


class ScriptedRouter:
    """Records every request; replays a scripted sequence of responses."""

    def __init__(self, turns):
        self.turns = turns
        self.requests = []

    async def route(self, request, **kwargs):
        self.requests.append(request)
        idx = len(self.requests) - 1
        turn = self.turns[min(idx, len(self.turns) - 1)]
        return MagicMock(
            content=turn.get("content", ""),
            tool_calls=turn.get("tool_calls", []),
            tokens_total=5,
        )


# ---------------------------------------------------------------------------
# 1) Tool definitions present in AIRequest (_run_tool_loop)
# ---------------------------------------------------------------------------

class TestAIToolRequest:
    @pytest.mark.asyncio
    async def test_ai_request_contains_tool_definitions(self):
        tm, _ = await build_real_registry()
        mediator = ToolMediator(tool_manager=tm)
        router = ScriptedRouter([{"content": "No tools needed"}])
        mgr = ConversationManager(ai_router=router, tool_manager=tm, tool_mediator=mediator)

        await mgr._run_tool_loop(
            "c1", [{"role": "user", "content": "hi"}], make_conv(),
        )

        assert len(router.requests) == 1
        req = router.requests[0]
        assert req.tools == [TOOL_DEF]
        assert req.tool_choice == "auto"

    @pytest.mark.asyncio
    async def test_ai_request_tools_are_schema_shaped(self):
        tm, _ = await build_real_registry()
        router = ScriptedRouter([{"content": "ok"}])
        mgr = ConversationManager(ai_router=router, tool_manager=tm)

        await mgr._run_tool_loop(
            "c2", [{"role": "user", "content": "hi"}], make_conv(),
        )

        tool = router.requests[0].tools[0]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "file.read"
        assert tool["function"]["parameters"]["type"] == "object"

    @pytest.mark.asyncio
    async def test_empty_registry_yields_empty_tools(self):
        router = ScriptedRouter([{"content": "ok"}])
        mgr = ConversationManager(ai_router=router)

        await mgr._run_tool_loop(
            "c3", [{"role": "user", "content": "hi"}], make_conv(),
        )

        req = router.requests[0]
        assert req.tools == []
        assert req.tool_choice == "auto"

    @pytest.mark.asyncio
    async def test_build_tool_definitions_handles_dict_entries(self):
        class DictToolManager:
            async def list_tools(self):
                return [{"id": "file.read", "name": "file.read",
                         "description": "Read a file", "parameters": {"type": "object"}}]

        mgr = ConversationManager(ai_router=ScriptedRouter([{"content": "ok"}]), tool_manager=DictToolManager())
        definitions = await mgr._build_tool_definitions()
        assert definitions[0]["function"]["name"] == "file.read"


# ---------------------------------------------------------------------------
# 2) stream_message uses the identical mechanism
# ---------------------------------------------------------------------------

class TestStreamRequestTools:
    class StreamCapturingRouter:
        def __init__(self):
            self.stream_requests = []
            self.route_calls = []

        async def route(self, request, **kwargs):
            self.route_calls.append(request)
            return MagicMock(content="Title", tool_calls=[], tokens_total=1)

        async def route_stream(self, request, **kwargs):
            self.stream_requests.append(request)
            result = MagicMock()
            result.request_id = "stream-1"
            result.trace.to_dict = lambda: {}
            result.tokens = _gen_tokens()
            result.token_factory = None
            return result

    @pytest.mark.asyncio
    async def test_stream_request_contains_tool_definitions(self):
        tm, _ = await build_real_registry()
        router = self.StreamCapturingRouter()
        mgr = ConversationManager(
            ai_router=router,
            tool_manager=tm,
            tool_mediator=ToolMediator(tool_manager=tm),
        )
        conv = await mgr.create_conversation(title="Stream Tools")

        events = [ev async for ev in mgr.stream_message(conv.id, "Hello")]
        assert len(events) > 0

        assert len(router.stream_requests) == 1
        req = router.stream_requests[0]
        assert req.stream is True
        assert req.tools == [TOOL_DEF]
        assert req.tool_choice == "auto"


async def _gen_tokens():
    yield "Hello"
    yield " "
    yield "world"


# ---------------------------------------------------------------------------
# 3) SmartRouter receives a populated ChatRequest.tools
# ---------------------------------------------------------------------------

class TestSmartRouterTools:
    def test_to_chat_request_carries_tools(self):
        req = MagicMock()
        req.messages = [{"role": "user", "content": "hi"}]
        req.model = "m"
        req.max_tokens = 4096
        req.temperature = 0.7
        req.top_p = 1.0
        req.tools = [TOOL_DEF]
        req.tool_choice = "auto"
        req.stream = False
        req.stop = None
        req.provider_id = None

        chat_req = SmartRouter._to_chat_request(req)

        assert chat_req.tools == [TOOL_DEF]
        assert chat_req.tool_choice == "auto"

    def test_to_chat_request_defaults_tools_none(self):
        req = type("AIRequest", (), {
            "messages": [{"role": "user", "content": "hi"}],
            "model": "m",
            "max_tokens": 4096,
            "temperature": 0.7,
            "stream": False,
            "provider_id": None,
        })()

        chat_req = SmartRouter._to_chat_request(req)
        assert chat_req.tools is None
        assert chat_req.tool_choice is None

    def test_make_request_preserves_tools_and_tool_choice(self):
        router = SmartRouter()
        original = ChatRequest(
            messages=[{"role": "user", "content": "hi"}],
            model="old",
            tools=[TOOL_DEF],
            tool_choice="auto",
        )
        new_req = router._make_request(original, model_id="new")
        assert new_req.model == "new"
        assert new_req.tools == [TOOL_DEF]
        assert new_req.tool_choice == "auto"


# ---------------------------------------------------------------------------
# 4) Provider adapter serializes tools into the outbound payload
# ---------------------------------------------------------------------------

class TestProviderPayloadSerialization:
    def _make_adapter(self):
        adapter = OpenAICompatibleAdapter(
            provider_type="test",
            provider_name="Test",
            api_key="k",
            base_url="http://test.local/v1",
        )
        captured = {}

        def handler(request):
            captured["body"] = json.loads(request.content)
            payload = {
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "model": request.content and json.loads(request.content).get("model", "test-model"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [TOOL_CALL],
                    },
                    "finish_reason": "tool_calls",
                }],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            }
            return httpx.Response(200, json=payload, request=request)

        adapter._http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            timeout=adapter._timeout_config.chat,
        )
        return adapter, captured

    @pytest.mark.asyncio
    async def test_payload_contains_tools(self):
        adapter, captured = self._make_adapter()
        try:
            resp = await adapter.chat(ChatRequest(
                messages=[{"role": "user", "content": "read it"}],
                model="test-model",
                tools=[TOOL_DEF],
                tool_choice="auto",
            ))
        finally:
            await adapter.disconnect()

        body = captured["body"]
        assert body["tools"] == [TOOL_DEF]
        assert body["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_payload_omits_tools_when_absent(self):
        adapter, captured = self._make_adapter()
        try:
            await adapter.chat(ChatRequest(
                messages=[{"role": "user", "content": "hi"}],
                model="test-model",
            ))
        finally:
            await adapter.disconnect()

        assert "tools" not in captured["body"]

    @pytest.mark.asyncio
    async def test_provider_tool_calls_are_returned(self):
        adapter, captured = self._make_adapter()
        try:
            resp = await adapter.chat(ChatRequest(
                messages=[{"role": "user", "content": "read it"}],
                model="test-model",
                tools=[TOOL_DEF],
                tool_choice="auto",
            ))
        finally:
            await adapter.disconnect()

        assert len(resp.tool_calls) == 1
        tc = resp.tool_calls[0]
        assert tc["id"] == "call_1"
        assert tc["function"]["name"] == "file.read"
        assert json.loads(tc["function"]["arguments"]) == {"path": "test.txt"}


# ---------------------------------------------------------------------------
# 5-8) Full execution loop: ToolMediator executes, ToolResult fed back,
#      final response is natural language
# ---------------------------------------------------------------------------

class TestToolExecutionLoop:
    @pytest.mark.asyncio
    async def test_tool_mediator_executes_and_final_is_natural_language(self):
        tm, executed = await build_real_registry()
        mediator = ToolMediator(tool_manager=tm)
        router = ScriptedRouter([
            {"content": "", "tool_calls": [TOOL_CALL]},
            {"content": "The file contains: hello from test.txt", "tool_calls": []},
        ])
        mgr = ConversationManager(ai_router=router, tool_manager=tm, tool_mediator=mediator)

        content, tokens = await mgr._run_tool_loop(
            "c4", [{"role": "user", "content": "Read the file"}], make_conv(),
        )

        # 5) tool_calls returned → loop re-queried
        assert len(router.requests) == 2
        # 6) ToolMediator executed the tool through the real registry
        assert executed["calls"] == [{"path": "test.txt"}]
        audit = mediator.get_audit_log()
        assert any(e["tool_id"] == "file.read" and e["success"] for e in audit)
        # 8) final response is natural language, not raw markup
        assert content == "The file contains: hello from test.txt"
        assert "<tool_call>" not in content
        assert tokens == 10

    @pytest.mark.asyncio
    async def test_tool_result_sent_back_to_llm(self):
        tm, _ = await build_real_registry()
        mediator = ToolMediator(tool_manager=tm)
        router = ScriptedRouter([
            {"content": "", "tool_calls": [TOOL_CALL]},
            {"content": "The file contains: hello from test.txt", "tool_calls": []},
        ])
        mgr = ConversationManager(ai_router=router, tool_manager=tm, tool_mediator=mediator)

        await mgr._run_tool_loop(
            "c5", [{"role": "user", "content": "Read the file"}], make_conv(),
        )

        second = router.requests[1]
        tool_msgs = [m for m in second.messages if m.get("role") == "tool"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0]["tool_call_id"] == "file.read"
        assert "hello from test.txt" in tool_msgs[0]["content"]

    @pytest.mark.asyncio
    async def test_final_response_has_no_raw_tool_markup_in_history(self):
        tm, _ = await build_real_registry()
        mediator = ToolMediator(tool_manager=tm)
        router = ScriptedRouter([
            {"content": "", "tool_calls": [TOOL_CALL]},
            {"content": "The file contains: hello from test.txt", "tool_calls": []},
        ])
        mgr = ConversationManager(ai_router=router, tool_manager=tm, tool_mediator=mediator)

        content, _ = await mgr._run_tool_loop(
            "c6", [{"role": "user", "content": "Read the file"}], make_conv(),
        )

        assistant_msgs = [m for m in mgr._messages.get("c6", [])
                          if m.role == MessageRole.ASSISTANT]
        assert len(assistant_msgs) == 1
        # The stored intermediate assistant message carries tool_calls, not raw markup
        assert assistant_msgs[0].tool_calls
        assert "<tool_call>" not in assistant_msgs[0].content
        # The content returned by the loop is the final natural-language response
        assert "<tool_call>" not in content
        assert content == "The file contains: hello from test.txt"

    @pytest.mark.asyncio
    async def test_tool_result_message_added_to_conversation(self):
        tm, _ = await build_real_registry()
        mediator = ToolMediator(tool_manager=tm)
        router = ScriptedRouter([
            {"content": "", "tool_calls": [TOOL_CALL]},
            {"content": "The file contains: hello from test.txt", "tool_calls": []},
        ])
        mgr = ConversationManager(ai_router=router, tool_manager=tm, tool_mediator=mediator)

        await mgr._run_tool_loop(
            "c7", [{"role": "user", "content": "Read the file"}], make_conv(),
        )

        result_msgs = [m for m in mgr._messages.get("c7", []) if m.tool_results]
        assert len(result_msgs) == 1
        assert result_msgs[0].tool_results[0]["tool_name"] == "file.read"
