"""Tests for the Agent Runtime abstraction + EVE Agent Adapter + HermesRuntime.

Phase A deliverables 1/2/4:
  - AgentRuntime ABC + domain models + run_turn() helper.
  - EveAgentAdapter bridge (alias resolution, route, route_stream, tools,
    model aggregation, health snapshot).
  - HermesRuntime isolation rule: EVE Core imports cleanly WITHOUT hermes-agent
    installed, and the only Hermes import lives in hermes_runtime.py.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from aios.agent import (
    CAPABILITY_ALIASES,
    AgentContext,
    AgentEvent,
    AgentHealth,
    AgentMetadata,
    AgentResult,
    AgentRuntime,
    AgentRuntimeStatus,
    AgentTurnRequest,
    EveAgentAdapter,
    resolve_model_alias,
)
from aios.agent import hermes_runtime as hermes_mod
from aios.agent.runtime import AgentRuntime as _ABCRuntime
from aios.core.adapters.base import ChatRequest, ChatResponse
from aios.core.routing_types import CommercialPolicy, RoutingTrace


# ---------------------------------------------------------------------------
# Fake EVE Core collaborators
# ---------------------------------------------------------------------------

class FakeSmartRouter:
    def __init__(self, content: str = "Fake routed reply", stream_tokens: list[str] | None = None):
        self.content = content
        self.stream_tokens = stream_tokens or ["Hello ", "from ", "EVE"]
        self.last_chat_request: ChatRequest | None = None
        self.last_kwargs: dict[str, Any] = {}

    async def route(
        self,
        request: ChatRequest,
        category: str = "general_chat",
        routing_policy: Any = None,
        commercial_policy: CommercialPolicy | None = None,
    ) -> ChatResponse:
        self.last_chat_request = request
        self.last_kwargs = {"category": category, "commercial_policy": commercial_policy}
        return ChatResponse(
            content=self.content,
            model="gemini-2.5-flash",
            provider="google",
            finish_reason="stop",
            metadata={"routing_trace": {"selected_model_id": "gemini-2.5-flash"}},
        )

    async def route_stream(
        self,
        request: ChatRequest,
        category: str = "general_chat",
        routing_policy: Any = None,
        commercial_policy: CommercialPolicy | None = None,
    ):
        self.last_chat_request = request
        self.last_kwargs = {"category": category, "commercial_policy": commercial_policy}
        trace = RoutingTrace(
            selected_provider_type="google",
            selected_provider_instance_id="google",
            selected_model_id="gemini-2.5-flash",
        )
        return _StreamResult(self.stream_tokens, trace)


class _StreamResult:
    def __init__(self, tokens: list[str], trace: RoutingTrace):
        self.tokens: AsyncIterator[str] = _aiter(tokens)
        self.trace = trace
        self.request_id = "req-test-1"
        self.token_factory = None


async def _aiter(items: list[str]) -> AsyncIterator[str]:
    for i in items:
        yield i


class FakeProviderManager:
    def __init__(self):
        self._providers = [
            {
                "id": "google",
                "type": "google",
                "models": [
                    {
                        "id": "gemini-2.5-flash",
                        "supports_vision": True,
                        "supports_reasoning": False,
                        "isFree": True,
                        "commercialStatus": "free",
                        "enabled": True,
                    }
                ],
            },
            {
                "id": "openai",
                "type": "openai",
                "models": [
                    {
                        "id": "gpt-4o",
                        "supports_reasoning": True,
                        "supports_tools": True,
                        "isFree": False,
                        "commercialStatus": "paid",
                        "enabled": False,
                    }
                ],
            },
        ]

    def list_providers(self) -> list[dict]:
        return self._providers


class FakeHealthMonitor:
    def get_all_health(self) -> dict[str, Any]:
        return {"google": _FakeHealth()}


class _FakeHealth:
    def to_dict(self) -> dict[str, Any]:
        return {"provider_id": "google", "status": "healthy"}


class FakeToolManager:
    async def execute(self, name: str, params: dict[str, Any]) -> Any:
        if name == "boom":
            return {"success": False, "error": "tool exploded"}
        return {"success": True, "result": f"ran {name}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_adapter(**kwargs) -> EveAgentAdapter:
    return EveAgentAdapter(
        smart_router=kwargs.get("smart_router", FakeSmartRouter()),
        provider_manager=kwargs.get("provider_manager", FakeProviderManager()),
        health_monitor=kwargs.get("health_monitor", FakeHealthMonitor()),
        tool_manager=kwargs.get("tool_manager", FakeToolManager()),
    )


def make_request(**kwargs) -> AgentTurnRequest:
    ctx = kwargs.pop("context", AgentContext(objective="Say hello", messages=[]))
    return AgentTurnRequest(context=ctx, **kwargs)


# ---------------------------------------------------------------------------
# AgentRuntime abstraction
# ---------------------------------------------------------------------------

def test_runtime_abstraction_is_abc():
    assert issubclass(AgentRuntime, _ABCRuntime)
    assert AgentRuntime.__abstractmethods__  # still abstract


def test_runtime_status_enum():
    assert AgentRuntimeStatus.IDLE.value == "idle"
    assert AgentRuntimeStatus.ERROR.value == "error"
    assert AgentRuntimeStatus.SHUTDOWN.value == "shutdown"


def test_agent_turn_request_defaults():
    req = AgentTurnRequest()
    assert req.model == "eve:general"
    assert req.stream is False
    assert req.max_tokens == 4096


def test_run_turn_collects_output_and_trace():
    class DummyRuntime(AgentRuntime):
        runtime_id = "dummy"

        async def start(self):
            pass

        async def shutdown(self):
            pass

        async def think(self, request):
            yield AgentEvent(type="status", content="thinking")
            yield AgentEvent(type="token", content="Hello ")
            yield AgentEvent(type="token", content="world")
            yield AgentEvent(
                type="done",
                metadata={"trace": {"model": "x"}, "model": "x", "provider": "p"},
            )

        async def plan(self, request):
            return AgentResult()

        async def execute(self, request):
            yield AgentEvent(type="status", content="executing")

        async def observe(self, request):
            return {}

        async def cancel(self):
            pass

        async def health(self):
            return AgentHealth()

        async def metadata(self):
            return AgentMetadata()

    result = asyncio_run(DummyRuntime().run_turn(make_request()))
    assert result.output == "Hello world"
    assert result.trace == {"model": "x"}


def test_run_turn_surfaces_error_event():
    class ErrorRuntime(AgentRuntime):
        runtime_id = "err"

        async def start(self):
            pass

        async def shutdown(self):
            pass

        async def think(self, request):
            yield AgentEvent(type="error", content="provider blew up")

        async def plan(self, request):
            return AgentResult()

        async def execute(self, request):
            yield AgentEvent(type="status", content="executing")

        async def observe(self, request):
            return {}

        async def cancel(self):
            pass

        async def health(self):
            return AgentHealth()

        async def metadata(self):
            return AgentMetadata()

    result = asyncio_run(ErrorRuntime().run_turn(make_request()))
    assert result.status == AgentRuntimeStatus.ERROR
    assert result.error == "provider blew up"


def test_run_turn_collects_tool_calls():
    class ToolRuntime(AgentRuntime):
        runtime_id = "tools"

        async def start(self):
            pass

        async def shutdown(self):
            pass

        async def think(self, request):
            yield AgentEvent(
                type="tool_call", name="read_file", arguments={"path": "/tmp/x"}
            )
            yield AgentEvent(type="done", metadata={})

        async def plan(self, request):
            return AgentResult()

        async def execute(self, request):
            yield AgentEvent(type="status", content="executing")

        async def observe(self, request):
            return {}

        async def cancel(self):
            pass

        async def health(self):
            return AgentHealth()

        async def metadata(self):
            return AgentMetadata()

    result = asyncio_run(ToolRuntime().run_turn(make_request()))
    assert result.tool_calls == [{"name": "read_file", "arguments": {"path": "/tmp/x"}}]


# ---------------------------------------------------------------------------
# Capability alias resolution
# ---------------------------------------------------------------------------

def test_resolve_alias_known():
    assert resolve_model_alias("eve:reasoning") == ("reasoning", None)
    assert resolve_model_alias("eve:free") == ("general_chat", CommercialPolicy.FREE_ONLY)
    assert resolve_model_alias("eve:coding") == ("coding", None)


def test_resolve_alias_unknown_category_fallback():
    assert resolve_model_alias("eve:audio") == ("audio", None)


def test_resolve_alias_exact_model_passthrough():
    assert resolve_model_alias("openai/gpt-4o") is None
    assert resolve_model_alias("gemini-2.5-flash") is None
    assert resolve_model_alias("") is None


def test_capability_alias_map_shape():
    for alias, (category, policy) in CAPABILITY_ALIASES.items():
        assert alias.startswith("eve:")
        assert isinstance(category, str)
        assert policy is None or isinstance(policy, CommercialPolicy)


# ---------------------------------------------------------------------------
# EveAgentAdapter — route
# ---------------------------------------------------------------------------

def test_adapter_route_returns_agent_result():
    router = FakeSmartRouter(content="Routed reply")
    adapter = make_adapter(smart_router=router)
    result = asyncio_run(
        adapter.route(make_request(model="eve:coding", max_tokens=2048))
    )
    assert result.output == "Routed reply"
    assert result.provider == "google"
    assert result.model == "gemini-2.5-flash"
    assert result.status == AgentRuntimeStatus.IDLE
    assert router.last_kwargs["category"] == "coding"
    assert "latency_ms" in result.metadata


def test_adapter_route_exact_model_passthrough():
    router = FakeSmartRouter()
    adapter = make_adapter(smart_router=router)
    asyncio_run(adapter.route(make_request(model="openai/gpt-4o")))
    assert router.last_kwargs["category"] == "general_chat"
    assert router.last_chat_request.model == "openai/gpt-4o"


def test_adapter_route_alias_sets_chat_request_model_empty():
    router = FakeSmartRouter()
    adapter = make_adapter(smart_router=router)
    asyncio_run(adapter.route(make_request(model="eve:general")))
    assert router.last_chat_request.model == ""
    assert router.last_chat_request.metadata["agent_category"] == "general_chat"


def test_adapter_route_free_alias_forwards_commercial_policy():
    router = FakeSmartRouter()
    adapter = make_adapter(smart_router=router)
    asyncio_run(adapter.route(make_request(model="eve:free")))
    assert router.last_kwargs["commercial_policy"] == CommercialPolicy.FREE_ONLY


def test_adapter_route_swallows_router_exception():
    class BoomRouter(FakeSmartRouter):
        async def route(self, *args, **kwargs):
            raise RuntimeError("no route")

    adapter = make_adapter(smart_router=BoomRouter())
    result = asyncio_run(adapter.route(make_request()))
    assert result.status == AgentRuntimeStatus.ERROR
    assert "no route" in result.error


# ---------------------------------------------------------------------------
# EveAgentAdapter — route_stream
# ---------------------------------------------------------------------------

def test_adapter_stream_emits_tokens_then_done():
    router = FakeSmartRouter(stream_tokens=["a", "b", "c"])
    adapter = make_adapter(smart_router=router)
    events = asyncio_run(_collect(adapter.route_stream(make_request())))
    assert [e.type for e in events] == ["token", "token", "token", "done"]
    assert [e.content for e in events if e.type == "token"] == ["a", "b", "c"]
    done = events[-1]
    assert done.metadata["model"] == "gemini-2.5-flash"
    assert done.metadata["provider"] == "google"
    assert done.metadata["trace"]["selected"]["model_id"] == "gemini-2.5-flash"


def test_adapter_stream_surfaces_router_error():
    class BoomStreamRouter(FakeSmartRouter):
        async def route_stream(self, *args, **kwargs):
            raise ConnectionError("stream failed")

    adapter = make_adapter(smart_router=BoomStreamRouter())
    events = asyncio_run(_collect(adapter.route_stream(make_request())))
    assert [e.type for e in events] == ["error"]
    assert "stream failed" in events[0].content


# ---------------------------------------------------------------------------
# EveAgentAdapter — tools, models, health
# ---------------------------------------------------------------------------

def test_adapter_execute_tool_success():
    adapter = make_adapter()
    result = asyncio_run(adapter.execute_tool("ls", {"dir": "."}))
    assert result == {"success": True, "result": "ran ls"}


def test_adapter_execute_tool_failure():
    adapter = make_adapter()
    result = asyncio_run(adapter.execute_tool("boom", {}))
    assert result == {"success": False, "error": "tool exploded"}


def test_adapter_list_models_dedups_and_skips_disabled():
    adapter = make_adapter()
    models = adapter.list_models()
    ids = [m["id"] for m in models]
    assert "google/gemini-2.5-flash" in ids
    assert "openai/gpt-4o" not in ids  # disabled
    g = next(m for m in models if m["id"] == "google/gemini-2.5-flash")
    assert g["is_free"] is True
    assert g["capabilities"]["supports_vision"] is True


def test_adapter_list_capability_aliases():
    adapter = make_adapter()
    aliases = adapter.list_capability_aliases()
    ids = [a["id"] for a in aliases]
    assert "eve:general" in ids
    assert "eve:reasoning" in ids
    assert "eve:coding" in ids
    for a in aliases:
        assert a["object"] == "model"
        assert a["owned_by"] == "eve"


def test_adapter_health_snapshot():
    adapter = make_adapter()
    snap = adapter.health_snapshot()
    assert snap["google"]["status"] == "healthy"


# ---------------------------------------------------------------------------
# HermesRuntime — isolation rule
# ---------------------------------------------------------------------------

def test_hermes_runtime_imports_without_hermes_installed():
    # Guarded import: even if hermes-agent is not installed, EVE Core imports.
    assert hasattr(hermes_mod, "HermesRuntime")
    assert hermes_mod._HERMES_AVAILABLE is False


def test_hermes_runtime_health_reports_unavailable():
    runtime = hermes_mod.HermesRuntime(adapter=make_adapter())
    health = asyncio_run(runtime.health())
    assert health.runtime_id == "hermes"
    assert health.available is False


def test_hermes_runtime_metadata():
    runtime = hermes_mod.HermesRuntime(adapter=make_adapter())
    meta = asyncio_run(runtime.metadata())
    assert meta.runtime_id == "hermes"
    assert meta.provider_aware is False
    assert meta.requires_config is True


def test_hermes_runtime_think_yields_error_without_engine():
    runtime = hermes_mod.HermesRuntime(adapter=make_adapter())
    events = asyncio_run(_collect(runtime.think(make_request())))
    assert events[0].type == "error"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def asyncio_run(coro):
    import asyncio

    try:
        return asyncio.run(coro)
    except RuntimeError:
        # Nested loop in some test setups — use a fresh event loop.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


async def _collect(agen: AsyncIterator[AgentEvent]) -> list[AgentEvent]:
    return [e async for e in agen]
