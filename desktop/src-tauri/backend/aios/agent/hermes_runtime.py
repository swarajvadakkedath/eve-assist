"""HermesRuntime — the FIRST implementation of the AgentRuntime abstraction.

Hermes (Nous Research Hermes Agent, https://hermes-agent.nousresearch.com) is
the reference Agent Runtime for EVE v2. All Hermes-specific knowledge lives in
this module and nowhere else in EVE Core.

Design contract:
  - EVE Core imports ONLY ``aios.agent`` (AgentRuntime, EveAgentAdapter).
  - This module is the ONLY place allowed to import ``hermes_*``.
  - Every LLM request made by Hermes is forwarded to the injected
    :class:`EveAgentAdapter`, which routes through EVE's Smart Router.
  - Hermes carries NO provider knowledge: it never talks to OpenAI, Gemini,
    Groq, OpenRouter, DeepInfra, NVIDIA, Ollama, or any future provider.

Implementation status:
  - The `hermes-agent` Python package is not yet bundled. The integration is
    intentionally gated: importing Hermes APIs is deferred until the package is
    available, so EVE Core imports cleanly regardless.
  - See ``EVE_V2.0_PHASE_A_ARCHITECTURE.md`` for the full integration plan.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from aios.agent.adapter import EveAgentAdapter
from aios.agent.runtime import (
    AgentEvent,
    AgentHealth,
    AgentMetadata,
    AgentResult,
    AgentRuntime,
    AgentRuntimeStatus,
    AgentTurnRequest,
)

logger = logging.getLogger("aios.agent.hermes")

_HERMES_IMPORT_ERROR: str | None = None

try:  # Hermes-specific imports are isolated here (Step 2 rule).
    # Hermes Agent exposes its engine through ``hermes_agent`` once installed
    # (pip install hermes-agent). The exact import path is finalized during
    # the integration milestone; the guard below keeps EVE Core import-safe.
    import hermes_agent  # type: ignore

    _HERMES_AVAILABLE = True
except Exception as e:  # pragma: no cover - exercised only without hermes
    _HERMES_AVAILABLE = False
    _HERMES_IMPORT_ERROR = str(e)


class HermesRuntime(AgentRuntime):
    """AgentRuntime implementation backed by the Hermes agent engine."""

    runtime_id = "hermes"
    display_name = "Hermes Agent"
    version = "0.0.0"

    def __init__(self, adapter: EveAgentAdapter):
        self._adapter = adapter
        self._status = AgentRuntimeStatus.IDLE
        self._engine: Any = None

    # -- Lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        if not _HERMES_AVAILABLE:
            logger.warning(
                "hermes-agent not installed; HermesRuntime is unavailable "
                "(%s)", _HERMES_IMPORT_ERROR,
            )
            self._status = AgentRuntimeStatus.ERROR
            return
        self._engine = _initialize_hermes_engine()
        self._status = AgentRuntimeStatus.IDLE

    async def shutdown(self) -> None:
        if self._engine is not None:
            self._engine = None
        self._status = AgentRuntimeStatus.SHUTDOWN

    # -- Turn execution -------------------------------------------------------

    async def think(self, request: AgentTurnRequest) -> AsyncIterator[AgentEvent]:
        if self._engine is None:
            yield AgentEvent(type="error", content=_HERMES_IMPORT_ERROR or "Hermes engine not initialized")
            return

        # Forward the request to EVE's Smart Router via the adapter.
        # Hermes provides the reasoning loop; EVE provides inference routing.
        self._status = AgentRuntimeStatus.THINKING
        try:
            async for event in self._adapter.route_stream(request):
                yield event
        except Exception as e:  # pragma: no cover - defensive
            yield AgentEvent(type="error", content=str(e))
        finally:
            self._status = AgentRuntimeStatus.IDLE

    async def plan(self, request: AgentTurnRequest) -> AgentResult:
        result = await self._adapter.route(request)
        self._status = AgentRuntimeStatus.PLANNING
        return result

    async def execute(self, request: AgentTurnRequest) -> AsyncIterator[AgentEvent]:
        self._status = AgentRuntimeStatus.EXECUTING
        try:
            async for event in self._adapter.route_stream(request):
                yield event
        finally:
            self._status = AgentRuntimeStatus.IDLE

    async def observe(self, request: AgentTurnRequest) -> dict[str, Any]:
        return dict(request.context.context)

    # -- Control ---------------------------------------------------------------

    async def cancel(self) -> None:
        self._status = AgentRuntimeStatus.CANCELLING

    async def health(self) -> AgentHealth:
        return AgentHealth(
            runtime_id=self.runtime_id,
            status=self._status.value,
            available=_HERMES_AVAILABLE,
            details={"import_error": _HERMES_IMPORT_ERROR},
        )

    async def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            runtime_id=self.runtime_id,
            display_name=self.display_name,
            version=self.version,
            capabilities=["reasoning", "planning", "tool_calling", "streaming"],
            skills=[],
            provider_aware=False,
            requires_config=_HERMES_AVAILABLE is False,
            description="Nous Research Hermes Agent wrapped as an EVE AgentRuntime.",
        )


def _initialize_hermes_engine() -> Any:
    """Construct the Hermes engine instance.

    Hermes is configured as an EVE provider (base_url points at EVE's
    OpenAI-compatible endpoint). This function centralizes Hermes construction
    so EVE Core never touches Hermes internals.
    """
    raise NotImplementedError(
        "Hermes engine wiring lands in the integration milestone. "
        "Configure Hermes as an EVE provider via ~/.hermes/config.yaml "
        "(see EVE_V2.0_PHASE_A_ARCHITECTURE.md Step 5)."
    )
