"""Agent Runtime abstraction for EVE v2.

EVE Core never depends on a specific agent framework. This module defines the
framework-agnostic contract any agent engine (Hermes, OpenAI Agents SDK,
CrewAI, LangGraph, OpenHands, AutoGen, native EVE planner) must implement to
plug into EVE.

A runtime owns the *thinking* of an agent (reasoning, planning, tool calls).
EVE owns the *operating system* around it: provider routing, health, recovery,
memory, permissions, and desktop integration. Runtimes carry no provider
knowledge — every inference request flows through the EVE Agent Adapter into
the Smart Router.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

class AgentRuntimeStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    WAITING = "waiting"
    CANCELLING = "cancelling"
    SHUTDOWN = "shutdown"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

@dataclass
class AgentContext:
    """Snapshot of the environment a runtime may use to ground its thinking.

    ``objective`` is the user's intent. ``messages`` carries conversation
    history in OpenAI wire format. ``tools`` are OpenAI-style tool schemas.
    ``context`` is free-form environment context (active window, clipboard,
    git branch, workspace, etc.) supplied by EVE's context engine.
    """

    objective: str = ""
    conversation_id: str = ""
    messages: list[dict] = field(default_factory=list)
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None
    capabilities: list[str] = field(default_factory=list)
    workspace: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTurnRequest:
    """A single inference request handed to a runtime.

    ``model`` is an EVE capability alias (``eve:general``, ``eve:reasoning``,
    ``eve:coding``, ``eve:vision``, ``eve:fast``, ``eve:free``) or an exact
    model id for passthrough. Runtimes never resolve providers themselves.
    """

    context: AgentContext = field(default_factory=AgentContext)
    stream: bool = False
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    stop: list[str] | None = None
    model: str = "eve:general"
    provider_id: str | None = None
    routing_policy: str = "auto"
    commercial_policy: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentEvent:
    """Streamed event produced by a runtime turn."""

    type: str  # token | tool_call | tool_result | status | done | error
    content: str = ""
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentResult:
    """Final outcome of a runtime turn."""

    output: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: AgentRuntimeStatus = AgentRuntimeStatus.IDLE
    error: str = ""
    model: str = ""
    provider: str = ""
    finish_reason: str = ""


@dataclass
class AgentHealth:
    runtime_id: str = ""
    status: str = "unknown"
    available: bool = False
    last_check: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMetadata:
    runtime_id: str = ""
    display_name: str = ""
    version: str = ""
    capabilities: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    provider_aware: bool = False
    requires_config: bool = False
    description: str = ""


# ---------------------------------------------------------------------------
# The interface
# ---------------------------------------------------------------------------

class AgentRuntime(ABC):
    """Framework-agnostic agent engine contract.

    Implementations own agent reasoning only. They must NEVER:
      - resolve providers or models themselves
      - import Hermes-specific code outside of ``HermesRuntime``
      - talk to OpenAI/Gemini/Groq/... directly

    Every LLM request must be forwarded to the EVE Agent Adapter so it flows
    through the Smart Router -> Provider Manager -> Health Monitor -> Recovery.
    """

    runtime_id: str = ""
    display_name: str = ""
    version: str = ""

    # -- Lifecycle ---------------------------------------------------------

    @abstractmethod
    async def start(self) -> None:
        """Initialize the runtime. Called once at EVE startup."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Release resources. Called once at EVE shutdown."""
        ...

    # -- Turn execution -----------------------------------------------------

    @abstractmethod
    async def think(self, request: AgentTurnRequest) -> AsyncIterator[AgentEvent]:
        """Reason over a request, streaming token/status/error events.

        Every inference call made here must go through the EVE Agent Adapter.
        """
        yield AgentEvent(type="status", content="not_implemented")

    @abstractmethod
    async def plan(self, request: AgentTurnRequest) -> AgentResult:
        """Produce a plan for an objective. Returns a structured result."""
        ...

    @abstractmethod
    async def execute(self, request: AgentTurnRequest) -> AsyncIterator[AgentEvent]:
        """Execute a plan / run a task, streaming tool_call and tool_result events."""
        yield AgentEvent(type="status", content="not_implemented")

    @abstractmethod
    async def observe(self, request: AgentTurnRequest) -> dict[str, Any]:
        """Gather environment context for the request. Returns a dict."""
        return {}

    # -- Control ------------------------------------------------------------

    @abstractmethod
    async def cancel(self) -> None:
        """Cancel any in-flight turn."""
        ...

    @abstractmethod
    async def health(self) -> AgentHealth:
        """Report runtime health."""
        ...

    @abstractmethod
    async def metadata(self) -> AgentMetadata:
        """Describe the runtime's capabilities and requirements."""
        ...

    # -- Helpers ------------------------------------------------------------

    async def run_turn(self, request: AgentTurnRequest) -> AgentResult:
        """Convenience: drain ``think`` events into a single AgentResult."""
        output_parts: list[str] = []
        tool_calls: list[dict] = []
        status = AgentRuntimeStatus.IDLE
        error = ""
        final_trace: dict[str, Any] = {}
        finish_reason = ""
        model = ""
        provider = ""

        async for event in self.think(request):
            if event.type == "token":
                output_parts.append(event.content)
            elif event.type == "tool_call":
                tool_calls.append(
                    {"name": event.name, "arguments": event.arguments}
                )
            elif event.type == "status":
                try:
                    status = AgentRuntimeStatus(event.content)
                except ValueError:
                    pass
            elif event.type == "error":
                status = AgentRuntimeStatus.ERROR
                error = event.content
            elif event.type == "done":
                finish_reason = event.metadata.get("finish_reason", finish_reason)
                model = event.metadata.get("model", model)
                provider = event.metadata.get("provider", provider)
                final_trace = event.metadata.get("trace", final_trace)

        return AgentResult(
            output="".join(output_parts),
            tool_calls=tool_calls,
            trace=final_trace,
            status=status,
            error=error,
            finish_reason=finish_reason,
            model=model,
            provider=provider,
        )
