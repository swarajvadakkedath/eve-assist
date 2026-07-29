"""Tests for AnalyticsTracker."""

import pytest
from aios.conversation.analytics import AnalyticsTracker, ConversationAnalytics


class TestConversationAnalytics:
    def test_default_fields(self):
        analytics = ConversationAnalytics()
        assert analytics.id
        assert analytics.total_tokens == 0
        assert analytics.estimated_cost == 0.0
        assert analytics.prompt_tokens == 0
        assert analytics.completion_tokens == 0

    def test_conversation_id_set(self):
        analytics = ConversationAnalytics(conversation_id="conv-1")
        assert analytics.conversation_id == "conv-1"

    def test_custom_id(self):
        analytics = ConversationAnalytics(id="custom-id")
        assert analytics.id == "custom-id"

    def test_total_tokens_calculation(self):
        analytics = ConversationAnalytics(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert analytics.total_tokens == 150


class TestAnalyticsTracker:
    @pytest.mark.asyncio
    async def test_record(self):
        tracker = AnalyticsTracker()
        record = await tracker.record(
            conversation_id="conv-1",
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=500.0,
            tool_count=2,
            memory_count=1,
            planner_count=1,
            retries=0,
            fallback="",
            context_size=4096,
        )
        assert record.conversation_id == "conv-1"
        assert record.ai_provider == "openai"
        assert record.total_tokens == 150
        assert record.response_latency_ms == 500.0
        assert record.tool_executions == 2

    @pytest.mark.asyncio
    async def test_record_cost_estimate(self):
        tracker = AnalyticsTracker()
        record = await tracker.record(
            conversation_id="conv-1",
            provider="openai",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        prompt_cost = 1000 * 0.00001
        completion_cost = 500 * 0.00003
        expected_cost = prompt_cost + completion_cost
        assert record.estimated_cost == expected_cost

    @pytest.mark.asyncio
    async def test_record_ollama_zero_cost(self):
        tracker = AnalyticsTracker()
        record = await tracker.record(
            conversation_id="conv-1",
            provider="ollama",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        assert record.estimated_cost == 0.0

    @pytest.mark.asyncio
    async def test_record_anthropic_cost(self):
        tracker = AnalyticsTracker()
        record = await tracker.record(
            conversation_id="conv-1",
            provider="anthropic",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        prompt_cost = 1000 * 0.000008
        completion_cost = 500 * 0.000024
        expected_cost = prompt_cost + completion_cost
        assert record.estimated_cost == expected_cost

    @pytest.mark.asyncio
    async def test_record_unknown_provider(self):
        tracker = AnalyticsTracker()
        record = await tracker.record(
            conversation_id="conv-1",
            provider="unknown",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        assert record.estimated_cost > 0

    @pytest.mark.asyncio
    async def test_get_conversation_analytics(self):
        tracker = AnalyticsTracker()
        await tracker.record(conversation_id="conv-1")
        await tracker.record(conversation_id="conv-1")
        records = await tracker.get_conversation_analytics("conv-1")
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_get_conversation_analytics_empty(self):
        tracker = AnalyticsTracker()
        records = await tracker.get_conversation_analytics("nonexistent")
        assert records == []

    @pytest.mark.asyncio
    async def test_get_conversation_summary(self):
        tracker = AnalyticsTracker()
        await tracker.record(
            conversation_id="conv-1",
            provider="openai",
            model="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=500.0,
            tool_count=2,
            memory_count=1,
            planner_count=1,
            retries=0,
            fallback="",
            context_size=4096,
        )
        summary = await tracker.get_conversation_summary("conv-1")
        assert summary["conversation_id"] == "conv-1"
        assert summary["total_exchanges"] == 1
        assert summary["total_tokens"] == 150
        assert summary["total_tool_executions"] == 2
        assert summary["total_memory_retrievals"] == 1
        assert summary["total_planner_invocations"] == 1
        assert summary["avg_latency_ms"] == 500.0
        assert summary["provider"] == "openai"
        assert summary["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_get_conversation_summary_empty(self):
        tracker = AnalyticsTracker()
        summary = await tracker.get_conversation_summary("nonexistent")
        assert summary == {}

    @pytest.mark.asyncio
    async def test_get_conversation_summary_multiple_records(self):
        tracker = AnalyticsTracker()
        await tracker.record(conversation_id="conv-1", prompt_tokens=100, completion_tokens=50, latency_ms=200.0)
        await tracker.record(conversation_id="conv-1", prompt_tokens=200, completion_tokens=100, latency_ms=400.0)
        summary = await tracker.get_conversation_summary("conv-1")
        assert summary["total_exchanges"] == 2
        assert summary["total_tokens"] == 450
        assert summary["avg_latency_ms"] == 300.0

    @pytest.mark.asyncio
    async def test_record_defaults(self):
        tracker = AnalyticsTracker()
        record = await tracker.record(conversation_id="conv-1")
        assert record.prompt_tokens == 0
        assert record.completion_tokens == 0
        assert record.total_tokens == 0
        assert record.ai_provider == ""

    def test_estimate_cost_ollama_zero(self):
        tracker = AnalyticsTracker()
        cost = tracker._estimate_cost("ollama", 100, 50)
        assert cost == 0.0

    def test_estimate_cost_unknown_provider(self):
        tracker = AnalyticsTracker()
        cost = tracker._estimate_cost("unknown_provider", 100, 50)
        assert cost > 0
