"""Tests for the OpenAI-compatible endpoint (Phase A deliverable 3).

Exercises translation between the OpenAI wire format and the EVE Agent
Adapter without starting the full app: we build a minimal FastAPI app that
registers the openai_compat router and stubs ``app.state.agent_adapter``.
"""

from __future__ import annotations

from typing import Any, AsyncIterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aios.agent.runtime import (
    AgentContext,
    AgentEvent,
    AgentResult,
    AgentRuntimeStatus,
    AgentTurnRequest,
)
from aios.api import openai_compat


# ---------------------------------------------------------------------------
# Stub adapter
# ---------------------------------------------------------------------------

class StubAdapter:
    """Minimal adapter exposing only what the router touches."""

    def __init__(self, content: str = "Hello from EVE", stream_tokens: list[str] | None = None):
        self.content = content
        self.stream_tokens = stream_tokens or ["Hello ", "from ", "EVE"]
        self.last_turn: AgentTurnRequest | None = None

    async def route(self, turn: AgentTurnRequest) -> AgentResult:
        self.last_turn = turn
        return AgentResult(
            output=self.content,
            status=AgentRuntimeStatus.IDLE,
            model="google/gemini-2.5-flash",
            provider="google",
            finish_reason="stop",
            trace={"selected": {"model_id": "google/gemini-2.5-flash"}},
        )

    async def route_stream(self, turn: AgentTurnRequest) -> AsyncIterator[AgentEvent]:
        self.last_turn = turn
        for t in self.stream_tokens:
            yield AgentEvent(type="token", content=t)
        yield AgentEvent(type="done", metadata={"model": turn.model})

    def list_models(self) -> list[dict[str, Any]]:
        return [{"id": "google/gemini-2.5-flash", "object": "model", "owned_by": "google"}]

    def list_capability_aliases(self) -> list[dict[str, Any]]:
        return [{"id": "eve:general", "object": "model", "owned_by": "eve"}]

    def provider_instance_ids(self) -> set[str]:
        return {"google-167d1a93", "openrouter-fff84e84"}

    def split_model_ref(self, model: str) -> tuple[str | None, str]:
        if not model or "/" not in model:
            return None, model
        prefix, _, rest = model.partition("/")
        if prefix in self.provider_instance_ids():
            return prefix, rest
        return None, model


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app = FastAPI()
    app.state.agent_adapter = StubAdapter()
    app.state.auth_manager = _NoAuth()
    app.include_router(openai_compat.router)
    return TestClient(app)


class _NoAuth:
    def verify(self, header: str | None) -> bool:
        return True


@pytest.fixture
def authed_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


# ---------------------------------------------------------------------------
# GET /v1/models
# ---------------------------------------------------------------------------

def test_get_v1_models(client, authed_headers):
    r = client.get("/v1/models", headers=authed_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "list"
    ids = [m["id"] for m in body["data"]]
    assert "google/gemini-2.5-flash" in ids
    assert "eve:general" in ids


def test_get_v1_models_requires_auth(client):
    class _Deny:
        def verify(self, header):
            return False

    client.app.state.auth_manager = _Deny()
    r = client.get("/v1/models")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# POST /v1/chat/completions — non-streaming
# ---------------------------------------------------------------------------

def test_chat_completions_non_streaming(client, authed_headers):
    payload = {
        "model": "eve:general",
        "messages": [{"role": "user", "content": "Say hi"}],
    }
    r = client.post("/v1/chat/completions", json=payload, headers=authed_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "Hello from EVE"
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["eve"]["provider"] == "google"
    assert body["id"].startswith("chatcmpl-")


def test_chat_completions_translates_turn(client, authed_headers):
    payload = {
        "model": "eve:coding",
        "messages": [{"role": "user", "content": "write tests"}],
        "max_tokens": 512,
        "temperature": 0.2,
        "stop": ["END"],
    }
    client.post("/v1/chat/completions", json=payload, headers=authed_headers)
    turn: AgentTurnRequest = client.app.state.agent_adapter.last_turn
    assert turn.model == "eve:coding"
    assert turn.max_tokens == 512
    assert turn.temperature == 0.2
    assert turn.stop == ["END"]
    assert turn.context.messages == [{"role": "user", "content": "write tests"}]


def test_chat_completions_tool_call_output(client, authed_headers):
    class ToolAdapter(StubAdapter):
        async def route(self, turn):
            self.last_turn = turn
            return AgentResult(
                tool_calls=[{"id": "c1", "name": "ls", "arguments": {"dir": "."}}],
                status=AgentRuntimeStatus.IDLE,
                model="openai/gpt-4o",
                provider="openai",
                finish_reason="tool_calls",
            )

    client.app.state.agent_adapter = ToolAdapter()
    r = client.post(
        "/v1/chat/completions",
        json={"model": "eve:tool", "messages": [{"role": "user", "content": "list"}]},
        headers=authed_headers,
    )
    body = r.json()
    tc = body["choices"][0]["message"]["tool_calls"][0]
    assert tc["type"] == "function"
    assert tc["function"]["name"] == "ls"
    assert body["choices"][0]["finish_reason"] == "tool_calls"


def test_chat_completions_validation_errors(client, authed_headers):
    r = client.post(
        "/v1/chat/completions",
        json={"model": "eve:general", "messages": [{"role": "user", "content": "x"}], "max_tokens": 0},
        headers=authed_headers,
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /v1/chat/completions — streaming (SSE)
# ---------------------------------------------------------------------------

def test_chat_completions_pins_exact_provider_model(client, authed_headers):
    payload = {
        "model": "openrouter-fff84e84/google/gemini-2.5-flash",
        "messages": [{"role": "user", "content": "hi"}],
    }
    r = client.post("/v1/chat/completions", json=payload, headers=authed_headers)
    assert r.status_code == 200
    turn: AgentTurnRequest = client.app.state.agent_adapter.last_turn
    assert turn.model == "google/gemini-2.5-flash"
    assert turn.provider_id == "openrouter-fff84e84"


def test_chat_completions_does_not_pin_alias(client, authed_headers):
    payload = {
        "model": "eve:general",
        "messages": [{"role": "user", "content": "hi"}],
    }
    client.post("/v1/chat/completions", json=payload, headers=authed_headers)
    turn: AgentTurnRequest = client.app.state.agent_adapter.last_turn
    assert turn.model == "eve:general"
    assert turn.provider_id is None


def test_chat_completions_stream_sse(client, authed_headers):
    payload = {
        "model": "eve:general",
        "messages": [{"role": "user", "content": "stream"}],
        "stream": True,
    }
    with client.stream("POST", "/v1/chat/completions", json=payload, headers=authed_headers) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        chunks = list(r.iter_lines())
    sse = [ln for ln in chunks if ln and ln.startswith("data: ")]
    assert sse[-1] == "data: [DONE]"
    import json

    parsed = [json.loads(ln[len("data: "):]) for ln in sse[:-1]]
    contents = []
    for p in parsed:
        for c in p["choices"]:
            if c["delta"].get("content"):
                contents.append(c["delta"]["content"])
    assert "".join(contents) == "Hello from EVE"
    assert parsed[-1]["choices"][0]["finish_reason"] == "stop"


def test_chat_completions_stream_relays_tool_calls(client, authed_headers):
    class ToolAdapter(StubAdapter):
        async def route(self, turn):
            self.last_turn = turn
            return AgentResult(
                tool_calls=[{"id": "c1", "name": "check_time", "arguments": {}}],
                status=AgentRuntimeStatus.IDLE,
                model="openrouter/inclusionai/ling-3.0-flash:free",
                provider="openrouter",
                finish_reason="tool_calls",
            )

    client.app.state.agent_adapter = ToolAdapter()
    payload = {
        "model": "eve:tool",
        "messages": [{"role": "user", "content": "what time is it"}],
        "tools": [{"type": "function", "function": {"name": "check_time", "parameters": {}}}],
        "stream": True,
    }
    with client.stream("POST", "/v1/chat/completions", json=payload, headers=authed_headers) as r:
        assert r.status_code == 200
        chunks = list(r.iter_lines())
    import json

    sse = [ln for ln in chunks if ln and ln.startswith("data: ")]
    assert sse[-1] == "data: [DONE]"
    parsed = [json.loads(ln[len("data: "):]) for ln in sse[:-1]]
    tool_calls = None
    for p in parsed:
        for c in p["choices"]:
            if c["delta"].get("tool_calls"):
                tool_calls = c["delta"]["tool_calls"]
    assert tool_calls is not None
    assert tool_calls[0]["type"] == "function"
    assert tool_calls[0]["function"]["name"] == "check_time"
    assert parsed[-1]["choices"][0]["finish_reason"] == "tool_calls"
    assert parsed[0]["eve"]["provider"] == "openrouter"


def test_chat_completions_stream_error_event(client, authed_headers):
    class ErrorAdapter(StubAdapter):
        async def route_stream(self, turn):
            self.last_turn = turn
            yield AgentEvent(type="error", content="routing failed")

    client.app.state.agent_adapter = ErrorAdapter()
    with client.stream(
        "POST", "/v1/chat/completions",
        json={"model": "eve:general", "messages": [{"role": "user", "content": "s"}], "stream": True},
        headers=authed_headers,
    ) as r:
        chunks = list(r.iter_lines())
    sse = [ln for ln in chunks if ln and ln.startswith("data: ")]
    import json

    parsed = [json.loads(ln[len("data: "):]) for ln in sse[:-1]]
    assert parsed[0]["eve"]["error"] == "routing failed"
