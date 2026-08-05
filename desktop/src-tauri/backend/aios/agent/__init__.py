"""EVE Agent Runtime — framework-agnostic agent abstraction.

EVE Core never depends on a specific agent framework. Hermes is the first
implementation (``HermesRuntime``); future runtimes (OpenAI Agents SDK,
CrewAI, LangGraph, OpenHands, AutoGen, native EVE planner) plug in without
modifying EVE Core.

Layering:

    AgentRuntime (HermesRuntime | FutureRuntime | NativeRuntime)
        -> EveAgentAdapter
        -> Smart Router -> Provider Manager -> Health Monitor -> Recovery

Public surface:
    AgentRuntime, AgentRuntimeStatus
    AgentContext, AgentTurnRequest, AgentEvent, AgentResult, AgentHealth, AgentMetadata
    EveAgentAdapter, CAPABILITY_ALIASES, resolve_model_alias
"""

from __future__ import annotations

from aios.agent.runtime import (
    AgentContext,
    AgentEvent,
    AgentHealth,
    AgentMetadata,
    AgentResult,
    AgentRuntime,
    AgentRuntimeStatus,
    AgentTurnRequest,
)
from aios.agent.adapter import (
    CAPABILITY_ALIASES,
    EveAgentAdapter,
    resolve_model_alias,
)

__all__ = [
    "AgentRuntime",
    "AgentRuntimeStatus",
    "AgentContext",
    "AgentTurnRequest",
    "AgentEvent",
    "AgentResult",
    "AgentHealth",
    "AgentMetadata",
    "EveAgentAdapter",
    "CAPABILITY_ALIASES",
    "resolve_model_alias",
]
