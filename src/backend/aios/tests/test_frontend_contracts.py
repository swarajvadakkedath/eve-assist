"""Integration tests for routing_policy persistence, fallback serialization,
commercial policy endpoints, and diagnostics endpoint."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from aios.conversation.models import Conversation, Message, MessageRole
from aios.conversation.formatter import (
    format_conversation_response,
    create_done_event,
    format_message_response,
)
from aios.core.routing_types import (
    CommercialPolicy,
    NoEligibleRouteError,
    FallbackReason,
    RoutingTrace,
)
from aios.core.smart_router import RoutingPolicy
from aios.core.adapters.base import sanitize_error


# ── Conversation routing_policy persistence ────────────────────────────────

class TestConversationRoutingPolicy:
    def test_conversation_default_routing_policy(self):
        c = Conversation()
        assert c.routing_policy is None

    def test_conversation_with_routing_policy(self):
        c = Conversation(routing_policy="strict")
        assert c.routing_policy == "strict"

    def test_conversation_routing_policy_serialization(self):
        c = Conversation(
            provider_id="google-abc",
            model_id="gemini-2.5-flash",
            routing_policy="auto",
        )
        resp = format_conversation_response(c)
        assert resp["routing_policy"] == "auto"
        assert resp["provider_id"] == "google-abc"
        assert resp["model_id"] == "gemini-2.5-flash"

    def test_conversation_routing_policy_none_serialization(self):
        c = Conversation()
        resp = format_conversation_response(c)
        assert resp["routing_policy"] is None


# ── Done event with routing trace ──────────────────────────────────────────

class TestDoneEventSerialization:
    def test_done_event_with_routing_trace(self):
        trace = {
            "policy": "auto",
            "fallback_reason": "free_alternate_provider",
            "selected_provider_id": "groq-abc",
            "selected_model_id": "llama-3.3-70b-versatile",
            "requested_provider_id": "openai-xyz",
            "requested_model_id": "gpt-4o",
        }
        event = create_done_event("msg-1", tokens_used=42, routing_trace=trace)
        assert event["type"] == "done"
        assert event["data"]["routing_trace"]["fallback_reason"] == "free_alternate_provider"
        assert event["data"]["routing_trace"]["selected_provider_id"] == "groq-abc"
        assert event["data"]["tokens_used"] == 42

    def test_done_event_without_routing_trace(self):
        event = create_done_event("msg-2", tokens_used=10)
        assert "routing_trace" not in event["data"]
        assert event["data"]["message_id"] == "msg-2"

    def test_done_event_with_error_type(self):
        event = create_done_event("msg-3", error_type="strict_failure")
        assert event["data"]["error_type"] == "strict_failure"

    def test_done_event_with_metadata(self):
        meta = {"routing_trace": {"fallback_reason": "paid_alternate"}}
        event = create_done_event("msg-4", metadata=meta)
        assert event["data"]["metadata"]["routing_trace"]["fallback_reason"] == "paid_alternate"


# ── RoutingTrace serialization ─────────────────────────────────────────────

class TestRoutingTraceSerialization:
    def test_trace_to_dict_includes_fallback_reason(self):
        trace = RoutingTrace(
            policy="auto",
            fallback_reason=FallbackReason.FREE_ALTERNATE_PROVIDER.value,
        )
        d = trace.to_dict()
        assert d["fallback_reason"] == "free_alternate_provider"

    def test_trace_to_dict_includes_commercial_policy(self):
        trace = RoutingTrace(
            policy="allow_fallback",
            commercial_policy=CommercialPolicy.FREE_ONLY.value,
        )
        d = trace.to_dict()
        assert d["commercial_policy"] == "free_only"

    def test_trace_candidate_count(self):
        trace = RoutingTrace(policy="auto")
        trace.candidate_count = 12
        d = trace.to_dict()
        assert d["candidate_count"] == 12


# ── sanitize_error coverage ────────────────────────────────────────────────

class TestSanitizeErrorCoverage:
    def test_sanitize_google_key(self):
        result = sanitize_error("Error: AIzaSyD1234567890abcdefghijklmnopqrstuv")
        assert "AIza***" in result
        assert "AIzaSyD1234" not in result

    def test_sanitize_anthropic_key(self):
        result = sanitize_error("error: sk-ant-api03-abcdefghijklmnopqrstuvwxyz")
        assert "sk-ant-api03" not in result
        assert "REDACTED" in result or "***" in result

    def test_sanitize_groq_key(self):
        result = sanitize_error("Error: gsk_1234567890abcdefghijklmnopqrstuvwxyz")
        assert "gsk_1234" not in result
        assert "REDACTED" in result or "***" in result

    def test_sanitize_bearer_token(self):
        result = sanitize_error("Header: Bearer eyJhbGciOiJIUzI1NiJ9.eyJ0ZXN0IjoxfQ.abc123")
        assert "eyJhbGci" not in result
        assert "REDACTED" in result or "***" in result

    def test_sanitize_api_key_in_string(self):
        result = sanitize_error("request failed with api_key=sk-proj-1234567890")
        assert "sk-proj-1234" not in result
        assert "REDACTED" in result or "***" in result

    def test_sanitize_no_credentials_in_output(self):
        """Ensure sanitized output never contains credential patterns."""
        test_cases = [
            "Error connecting to AIzaSyD1234567890abcdefghijklmnopqrstuv endpoint",
            "Failed with Bearer eyJhbGciOiJIUzI1NiJ9.eyJ0ZXN0IjoxfQ.abc123",
            "gsk_1234567890abcdefghijklmnopqrstuvwxyz was rejected",
        ]
        for case in test_cases:
            result = sanitize_error(case)
            assert "AIzaSyD" not in result
            assert "eyJhbGci" not in result
            assert "gsk_1234" not in result


# ── NoEligibleRouteError ───────────────────────────────────────────────────

class TestNoEligibleRouteError:
    def test_strict_failure_error(self):
        err = NoEligibleRouteError(
            reason="No eligible route found (STRICT, no explicit selection)",
            candidates_attempted=5,
        )
        assert "STRICT" in err.reason
        assert err.candidates_attempted == 5

    def test_strict_failure_error_to_dict(self):
        err = NoEligibleRouteError(
            reason="Provider offline",
            candidates_attempted=3,
        )
        d = err.to_dict()
        assert d["reason"] == "Provider offline"
        assert d["candidates_attempted"] == 3
