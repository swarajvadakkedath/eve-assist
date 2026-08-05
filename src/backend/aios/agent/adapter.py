"""EVE Agent Adapter — bridge between AgentRuntime and EVE Core.

The adapter is the ONLY layer that talks to EVE Core on behalf of a runtime.
It translates an :class:`AgentTurnRequest` into an EVE ``ChatRequest`` and
forwards it to the Smart Router, ensuring every inference request flows
through routing, health monitoring, credential pools, commercial policy, and
recovery.

The adapter never imports Hermes or any other agent framework. It only speaks
the :class:`AgentRuntime` vocabulary on one side and EVE Core on the other.
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator

from aios.agent.runtime import (
    AgentContext,
    AgentEvent,
    AgentResult,
    AgentTurnRequest,
    AgentRuntimeStatus,
)
from aios.core.adapters.base import ChatRequest, ChatResponse
from aios.core.health_monitor import HealthMonitor
from aios.core.provider_manager import ProviderManager
from aios.core.routing_types import CommercialPolicy
from aios.core.smart_router import RoutingPolicy, SmartRouter
from aios.core.tool_manager import ToolManager


# ---------------------------------------------------------------------------
# Capability alias resolution
# ---------------------------------------------------------------------------

# EVE capability aliases -> (routing category, commercial policy override)
CAPABILITY_ALIASES: dict[str, tuple[str, CommercialPolicy | None]] = {
    "eve:general": ("general_chat", None),
    "eve:chat": ("general_chat", None),
    "eve:reasoning": ("reasoning", None),
    "eve:coding": ("coding", None),
    "eve:vision": ("vision", None),
    "eve:fast": ("general_chat", None),
    "eve:free": ("general_chat", CommercialPolicy.FREE_ONLY),
    "eve:json": ("structured_output", None),
    "eve:tool": ("tool_calling", None),
}


def resolve_model_alias(model: str) -> tuple[str, CommercialPolicy | None] | None:
    """Map an ``eve:*`` alias to (category, commercial_policy). Returns None if
    the model is not a capability alias (i.e. an exact model id passthrough)."""
    if not model or not model.startswith("eve:"):
        return None
    alias = model.lower()
    if alias in CAPABILITY_ALIASES:
        return CAPABILITY_ALIASES[alias]
    # Fall back to treating the alias suffix as a routing category directly,
    # e.g. ``eve:audio`` -> category ``audio`` when one exists.
    category = alias[len("eve:"):]
    return (category, None)


class EveAgentAdapter:
    """Translates AgentRuntime requests into EVE Core calls."""

    def __init__(
        self,
        smart_router: SmartRouter,
        provider_manager: ProviderManager,
        health_monitor: HealthMonitor,
        tool_manager: ToolManager,
    ):
        self._smart_router = smart_router
        self._provider_manager = provider_manager
        self._health_monitor = health_monitor
        self._tool_manager = tool_manager

    # -- Routing core -------------------------------------------------------

    def _build_chat_request(self, request: AgentTurnRequest) -> ChatRequest:
        ctx: AgentContext = request.context
        resolved = resolve_model_alias(request.model)
        category = resolved[0] if resolved else "general_chat"
        commercial_policy = resolved[1] if resolved else None

        chat_req = ChatRequest(
            messages=ctx.messages or [{"role": "user", "content": ctx.objective}],
            model="" if resolved else request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop,
            stream=request.stream,
            tools=ctx.tools,
            tool_choice=ctx.tool_choice,
            metadata=dict(ctx.metadata),
            provider_id=request.provider_id,
        )
        chat_req.metadata["agent_category"] = category
        if commercial_policy is not None:
            chat_req.metadata["agent_commercial_policy"] = commercial_policy.value
        return chat_req

    def _resolve_routing(
        self, request: AgentTurnRequest
    ) -> tuple[str, RoutingPolicy, CommercialPolicy | None]:
        resolved = resolve_model_alias(request.model)
        category = resolved[0] if resolved else "general_chat"
        try:
            policy = RoutingPolicy(request.routing_policy)
        except ValueError:
            policy = RoutingPolicy.AUTO
        commercial_policy = resolved[1] if resolved else None
        if request.commercial_policy:
            try:
                commercial_policy = CommercialPolicy(request.commercial_policy)
            except ValueError:
                pass
        return category, policy, commercial_policy

    # -- Public API ----------------------------------------------------------

    async def route(
        self, request: AgentTurnRequest
    ) -> AgentResult:
        """Non-streaming inference through the Smart Router."""
        chat_req = self._build_chat_request(request)
        category, policy, commercial_policy = self._resolve_routing(request)
        start = time.monotonic()
        try:
            resp: ChatResponse = await self._smart_router.route(
                chat_req,
                category=category,
                routing_policy=policy,
                commercial_policy=commercial_policy,
            )
        except Exception as e:
            return AgentResult(
                status=AgentRuntimeStatus.ERROR,
                error=str(e),
                model=request.model,
            )
        return AgentResult(
            output=resp.content,
            tool_calls=resp.tool_calls,
            trace=resp.metadata.get("routing_trace", {}),
            status=AgentRuntimeStatus.IDLE,
            model=resp.model or request.model,
            provider=resp.provider or "",
            finish_reason=resp.finish_reason,
            metadata={"latency_ms": (time.monotonic() - start) * 1000},
        )

    async def route_stream(
        self, request: AgentTurnRequest
    ) -> AsyncIterator[AgentEvent]:
        """Streaming inference through the Smart Router.

        Emits ``token`` events per chunk and a final ``done`` event carrying the
        routing trace. Errors emit an ``error`` event and stop.
        """
        chat_req = self._build_chat_request(request)
        category, policy, commercial_policy = self._resolve_routing(request)
        try:
            stream = await self._smart_router.route_stream(
                chat_req,
                category=category,
                routing_policy=policy,
                commercial_policy=commercial_policy,
            )
        except Exception as e:
            yield AgentEvent(type="error", content=str(e))
            return
        try:
            async for token in stream.tokens:
                yield AgentEvent(type="token", content=token)
            yield AgentEvent(
                type="done",
                metadata={
                    "trace": stream.trace.to_dict(),
                    "model": stream.trace.selected_model_id or request.model,
                    "provider": stream.trace.selected_provider_instance_id or "",
                    "finish_reason": "stop",
                    "request_id": stream.request_id,
                },
            )
        except Exception as e:
            yield AgentEvent(type="error", content=str(e))

    # -- Tool execution ------------------------------------------------------

    async def execute_tool(self, name: str, params: dict[str, Any]) -> Any:
        """Execute a tool by id through EVE's ToolManager."""
        result = await self._tool_manager.execute(name, params)
        if hasattr(result, "success") and not result.success:
            return {"success": False, "error": getattr(result, "error", "unknown")}
        return getattr(result, "result", result)

    # -- Model surface --------------------------------------------------------

    def provider_instance_ids(self) -> set[str]:
        """Return the set of configured provider instance ids."""
        return {
            p.get("id", "")
            for p in self._provider_manager.list_providers()
            if p.get("id")
        }

    def split_model_ref(
        self, model: str
    ) -> tuple[str | None, str]:
        """Split ``provider_instance/model_id`` into (provider_id, model_id).

        Returns ``(None, model)`` when the model is not an exact reference
        (e.g. an ``eve:*`` capability alias) or the prefix is not a known
        provider instance.
        """
        if not model or "/" not in model:
            return None, model
        prefix, _, rest = model.partition("/")
        if prefix in self.provider_instance_ids():
            return prefix, rest
        return None, model

    def list_models(self) -> list[dict[str, Any]]:
        """Aggregate all models across configured providers (dedup'd by id)."""
        seen: dict[str, dict[str, Any]] = {}
        for provider in self._provider_manager.list_providers():
            pid = provider.get("id", "")
            for m in provider.get("models", []):
                if not m.get("enabled", True):
                    continue
                mid = m.get("id") or m.get("model") or m.get("model_id")
                if not mid:
                    continue
                key = f"{pid}/{mid}"
                seen[key] = {
                    "id": f"{pid}/{mid}",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": pid,
                    "model_id": mid,
                    "provider_id": pid,
                    "provider_type": provider.get("type", ""),
                    "capabilities": {
                        k: bool(m.get(k))
                        for k in (
                            "supports_vision",
                            "supports_reasoning",
                            "supports_tools",
                            "supports_function_calling",
                            "supports_json",
                            "supports_embeddings",
                            "supports_audio",
                        )
                    },
                    "commercial_status": m.get("commercialStatus", m.get("commercial_status")),
                    "is_free": bool(m.get("isFree", m.get("is_free", False))),
                    "context_window": m.get("context_window"),
                }
        return list(seen.values())

    def list_capability_aliases(self) -> list[dict[str, Any]]:
        return [
            {
                "id": alias,
                "object": "model",
                "created": 0,
                "owned_by": "eve",
                "capability": category,
            }
            for alias, (category, _) in sorted(CAPABILITY_ALIASES.items())
        ]

    # -- Health ----------------------------------------------------------------

    def health_snapshot(self) -> dict[str, Any]:
        """Return a provider-health snapshot for diagnostics."""
        return {
            pid: h.to_dict()
            for pid, h in self._health_monitor.get_all_health().items()
        }
