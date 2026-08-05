"""OpenAI-compatible inference endpoint — EVE's public inference interface.

Exposes ``GET /v1/models`` and ``POST /v1/chat/completions`` in the OpenAI
wire format so any OpenAI-wire client (Hermes configured as a custom provider,
OpenCode, SDKs, etc.) can use EVE as its model backend.

Every request is translated into an :class:`AgentTurnRequest` and forwarded to
the :class:`EveAgentAdapter`, so ALL inference flows through:

    AgentRuntime -> EVE Agent Adapter -> Smart Router
        -> Provider Manager -> Health Monitor -> Recovery

Model addressing:
  - ``eve:*`` capability aliases (``eve:general``, ``eve:reasoning``,
    ``eve:coding``, ``eve:vision``, ``eve:fast``, ``eve:free``) are resolved by
    the Smart Router at request time.
  - Exact model ids (``provider_id/model_id``) pass through as a preferred
    route.

Auth: enforced via the shared EVE bearer-token dependency (``verify_auth``).
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aios.agent.adapter import EveAgentAdapter, resolve_model_alias
from aios.agent.runtime import AgentContext, AgentEvent, AgentTurnRequest
from aios.api.auth_deps import verify_auth

router = APIRouter(tags=["openai-compatible"])


# ---------------------------------------------------------------------------
# Request/response models (OpenAI wire format)
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str | list[dict] | None = None
    name: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "eve:general"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=200000)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    stop: list[str] | str | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
    user: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_messages(messages: list[ChatMessage]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        content = m.content
        if isinstance(content, list):
            # Multi-part content (e.g. image URLs) — pass through as-is.
            content = json.dumps(content, ensure_ascii=False)
        entry: dict[str, Any] = {"role": m.role, "content": content or ""}
        if m.tool_calls:
            entry["tool_calls"] = m.tool_calls
        if m.tool_call_id:
            entry["tool_call_id"] = m.tool_call_id
        if m.name:
            entry["name"] = m.name
        out.append(entry)
    return out


def _normalize_stop(stop: list[str] | str | None) -> list[str] | None:
    if stop is None:
        return None
    if isinstance(stop, str):
        return [stop] if stop else None
    return stop or None


def _to_turn_request(
    body: ChatCompletionRequest, provider_ids: set[str] | None = None
) -> AgentTurnRequest:
    provider_id, model_id = _split_model_ref(body.model or "", provider_ids or set())
    return AgentTurnRequest(
        context=AgentContext(
            objective=body.messages[-1].content
            if body.messages and isinstance(body.messages[-1].content, str)
            else "",
            messages=_normalize_messages(body.messages),
            tools=body.tools,
            tool_choice=body.tool_choice,
            context={"openai_compatible": True},
        ),
        stream=body.stream,
        max_tokens=body.max_tokens or 4096,
        temperature=body.temperature if body.temperature is not None else 0.7,
        top_p=body.top_p if body.top_p is not None else 1.0,
        stop=_normalize_stop(body.stop),
        model=model_id or body.model or "eve:general",
        provider_id=provider_id,
    )


def _split_model_ref(model: str, provider_ids: set[str]) -> tuple[str | None, str]:
    """Split ``provider_instance/model_id`` into (provider_id, model_id).

    Only recognized provider instances are split; anything else (``eve:*``
    aliases, plain model ids) passes through as a capability/auto route.
    """
    if not model or "/" not in model:
        return None, model
    prefix, _, rest = model.partition("/")
    if prefix in provider_ids:
        return prefix, rest
    return None, model


def _response_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:24]}"


def _usage(prompt_tokens: int, completion_tokens: int) -> dict[str, Any]:
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


# ---------------------------------------------------------------------------
# GET /v1/models
# ---------------------------------------------------------------------------

@router.get("/v1/models", dependencies=[Depends(verify_auth)])
async def list_models(request: Request):
    """Return EVE's aggregated model catalog + capability aliases."""
    adapter: EveAgentAdapter = request.app.state.agent_adapter
    data = adapter.list_models()
    data.extend(adapter.list_capability_aliases())
    return {"object": "list", "data": data}


# ---------------------------------------------------------------------------
# POST /v1/chat/completions
# ---------------------------------------------------------------------------

@router.post("/v1/chat/completions", dependencies=[Depends(verify_auth)])
async def chat_completions(body: ChatCompletionRequest, request: Request):
    adapter: EveAgentAdapter = request.app.state.agent_adapter
    turn = _to_turn_request(body, provider_ids=adapter.provider_instance_ids())

    if body.stream:
        return _stream_response(adapter, turn, body)

    result = await adapter.route(turn)
    if result.status.value == "error" or result.error:
        raise HTTPException(status_code=502, detail=result.error or "inference failed")

    message: dict[str, Any] = {"role": "assistant", "content": result.output or None}
    if result.tool_calls:
        message["tool_calls"] = _format_tool_calls(result.tool_calls)
    if not message["content"] and not message.get("tool_calls"):
        message["content"] = ""

    finish = result.finish_reason or ("tool_calls" if result.tool_calls else "stop")

    return {
        "id": _response_id(),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": result.model or body.model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish,
            }
        ],
        "usage": _usage(0, 0),
        "eve": {
            "provider": result.provider,
            "model": result.model,
            "trace": result.trace,
            "routing_policy": body.model,
        },
    }


def _format_tool_calls(tool_calls: list[dict]) -> list[dict]:
    formatted: list[dict] = []
    for i, tc in enumerate(tool_calls):
        name = tc.get("name") or (tc.get("function") or {}).get("name", "")
        args = tc.get("arguments") or (tc.get("function") or {}).get("arguments", "{}")
        if isinstance(args, dict):
            args = json.dumps(args, ensure_ascii=False)
        formatted.append(
            {
                "id": tc.get("id") or f"call_{i}",
                "type": "function",
                "function": {"name": name, "arguments": str(args)},
            }
        )
    return formatted


def _stream_response(
    adapter: EveAgentAdapter, turn: AgentTurnRequest, body: ChatCompletionRequest
) -> StreamingResponse:
    model = body.model
    created = int(time.time())
    response_id = _response_id()

    async def _generate():
        # Tool-calling requests are routed non-streaming: the streaming token
        # pipeline only carries content tokens, so tool_calls would be silently
        # dropped (an OpenAI client like Hermes would see an empty reply). The
        # non-streaming path also keeps the full failover chain. The single-shot
        # result is then re-emitted as a valid SSE stream (delta.tool_calls).
        if body.tools or body.tool_choice:
            result = await adapter.route(turn)
            if result.status.value == "error" or result.error:
                payload = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": None}],
                    "eve": {"error": result.error or "inference failed"},
                }
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"
                return
            delta: dict[str, Any] = {"role": "assistant"}
            if result.output:
                delta["content"] = result.output
            if result.tool_calls:
                delta["tool_calls"] = _format_tool_calls(result.tool_calls)
            payload = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": result.model or model,
                "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
                "eve": {"provider": result.provider, "model": result.model, "routing_policy": model},
            }
            yield f"data: {json.dumps(payload)}\n\n"
            finish = result.finish_reason or ("tool_calls" if result.tool_calls else "stop")
            final = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": result.model or model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"
            return

        async for event in adapter.route_stream(turn):
            if event.type == "error":
                payload = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": None,
                        }
                    ],
                    "eve": {"error": event.content},
                }
                yield f"data: {json.dumps(payload)}\n\n"
                yield "data: [DONE]\n\n"
                return
            if event.type != "token":
                continue
            payload = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": event.content},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(payload)}\n\n"

        final = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(final)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
