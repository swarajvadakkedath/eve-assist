"""Conversation analytics — track tokens, cost, latency, tool usage."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class ConversationAnalytics:
    id: str = ""
    conversation_id: str = ""
    ai_provider: str = ""
    ai_model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    response_latency_ms: float = 0.0
    tool_executions: int = 0
    memory_retrievals: int = 0
    planner_invocations: int = 0
    retry_count: int = 0
    fallback_provider: str = ""
    context_size: int = 0
    created_at: datetime | None = None

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            self.created_at = datetime.utcnow()


class AnalyticsTracker:
    def __init__(self):
        self._analytics: dict[str, list[ConversationAnalytics]] = {}

    async def record(
        self,
        conversation_id: str,
        provider: str = "",
        model: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        tool_count: int = 0,
        memory_count: int = 0,
        planner_count: int = 0,
        retries: int = 0,
        fallback: str = "",
        context_size: int = 0,
    ) -> ConversationAnalytics:
        record = ConversationAnalytics(
            conversation_id=conversation_id,
            ai_provider=provider,
            ai_model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=self._estimate_cost(provider, prompt_tokens, completion_tokens),
            response_latency_ms=latency_ms,
            tool_executions=tool_count,
            memory_retrievals=memory_count,
            planner_invocations=planner_count,
            retry_count=retries,
            fallback_provider=fallback,
            context_size=context_size,
        )
        self._analytics.setdefault(conversation_id, []).append(record)
        return record

    async def get_conversation_analytics(self, conversation_id: str) -> list[ConversationAnalytics]:
        return self._analytics.get(conversation_id, [])

    async def get_conversation_summary(self, conversation_id: str) -> dict:
        records = self._analytics.get(conversation_id, [])
        if not records:
            return {}
        return {
            "conversation_id": conversation_id,
            "total_exchanges": len(records),
            "total_prompt_tokens": sum(r.prompt_tokens for r in records),
            "total_completion_tokens": sum(r.completion_tokens for r in records),
            "total_tokens": sum(r.total_tokens for r in records),
            "total_cost": sum(r.estimated_cost for r in records),
            "avg_latency_ms": sum(r.response_latency_ms for r in records) / len(records) if records else 0,
            "total_tool_executions": sum(r.tool_executions for r in records),
            "total_memory_retrievals": sum(r.memory_retrievals for r in records),
            "total_planner_invocations": sum(r.planner_invocations for r in records),
            "total_retries": sum(r.retry_count for r in records),
            "provider": records[-1].ai_provider if records else "",
            "model": records[-1].ai_model if records else "",
        }

    def _estimate_cost(self, provider: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = {
            "openai": {"prompt": 0.00001, "completion": 0.00003},
            "anthropic": {"prompt": 0.000008, "completion": 0.000024},
            "ollama": {"prompt": 0.0, "completion": 0.0},
        }
        rate = rates.get(provider, {"prompt": 0.00001, "completion": 0.00003})
        return (prompt_tokens * rate["prompt"]) + (completion_tokens * rate["completion"])
