"""Tests for the AI Error Intelligence package (P2)."""

import pytest

from aios.core.adapters.base import ProviderStatus
from aios.core.routing_types import (
    NoEligibleRouteError,
    RouteAuthError,
    RouteQuotaExhaustedError,
    RouteRateLimitedError,
)
from aios.core.timeout_retry import ProviderTimeoutError
from aios.conversation.exceptions import (
    MemoryError,
    PlannerError,
    StreamError,
    ToolExecutionError,
)
from aios.error_intelligence import (
    AutoRecoveryStrategy,
    ErrorCategory,
    ErrorEvent,
    Severity,
    classify_error,
    error_to_stream_event,
)
from aios.error_intelligence.service import ErrorIntelligenceService


class TestTaxonomy:
    def test_twenty_one_categories(self):
        cats = list(ErrorCategory)
        assert len(cats) == 21
        expected = {
            "PROVIDER", "ROUTING", "NETWORK", "VOICE", "VISION", "MEMORY",
            "WORKSPACE", "FILE_SEARCH", "OCR", "PLUGIN", "TOOL_EXECUTION",
            "DATABASE", "AUTHENTICATION", "PERMISSION", "CONFIGURATION",
            "API", "TIMEOUT", "STREAMING", "RATE_LIMIT", "INTERNAL_BUG",
            "UNKNOWN",
        }
        assert {c.value for c in cats} == expected

    def test_error_event_round_trip(self):
        e = ErrorEvent(
            error_id=ErrorEvent.new_id(),
            timestamp=ErrorEvent.now_iso(),
            category=ErrorCategory.RATE_LIMIT,
            severity=Severity.HIGH,
            message="rate limited",
            module="smart_router",
            provider="google",
            model="gemini-2.5-flash",
        )
        d = e.to_dict()
        assert d["category"] == "RATE_LIMIT"
        assert d["severity"] == "HIGH"
        assert d["provider"] == "google"
        assert d["message"] == "rate limited"


class TestClassifier:
    def test_route_no_eligible(self):
        cls = classify_error(NoEligibleRouteError(reason="nothing available"))
        assert cls.category == ErrorCategory.ROUTING
        assert cls.auto_recovery_strategy == AutoRecoveryStrategy.SUGGEST_ONLY
        assert cls.recoverable

    def test_route_auth_error(self):
        cls = classify_error(RouteAuthError(provider_instance_id="openai", model_id="gpt-4o"))
        assert cls.category == ErrorCategory.AUTHENTICATION
        assert not cls.retryable
        assert not cls.recoverable
        assert "provider=openai" in cls.root_cause

    def test_route_rate_limited(self):
        cls = classify_error(RouteRateLimitedError(retry_after=5.0))
        assert cls.category == ErrorCategory.RATE_LIMIT
        assert cls.auto_recovery_strategy == AutoRecoveryStrategy.COOLDOWN

    def test_route_quota(self):
        cls = classify_error(RouteQuotaExhaustedError())
        assert cls.category == ErrorCategory.RATE_LIMIT
        assert cls.severity == Severity.HIGH

    def test_route_error_type_override_without_exc(self):
        cls = classify_error(error_type="PAID_ROUTING_DISABLED")
        assert cls.category == ErrorCategory.CONFIGURATION

    def test_provider_status_timeout(self):
        cls = classify_error(provider_status=ProviderStatus.TIMEOUT)
        assert cls.category == ErrorCategory.TIMEOUT
        assert cls.auto_recovery_strategy == AutoRecoveryStrategy.RETRY_OR_SWITCH

    def test_provider_status_offline(self):
        cls = classify_error(provider_status=ProviderStatus.OFFLINE)
        assert cls.category == ErrorCategory.NETWORK
        assert cls.auto_recovery_strategy == AutoRecoveryStrategy.SWITCH_PROVIDER

    def test_provider_status_quota(self):
        cls = classify_error(provider_status=ProviderStatus.QUOTA_EXCEEDED)
        assert cls.category == ErrorCategory.RATE_LIMIT

    def test_provider_status_invalid_key(self):
        cls = classify_error(provider_status=ProviderStatus.INVALID_KEY)
        assert cls.category == ErrorCategory.AUTHENTICATION

    def test_http_404_refresh_models(self):
        cls = classify_error(http_status=404)
        assert cls.category == ErrorCategory.PROVIDER
        assert cls.auto_recovery_strategy == AutoRecoveryStrategy.REFRESH_MODELS
        assert "Refresh the model list" in cls.recovery_suggestions

    def test_http_429(self):
        cls = classify_error(http_status=429)
        assert cls.category == ErrorCategory.RATE_LIMIT
        assert cls.auto_recovery_strategy == AutoRecoveryStrategy.COOLDOWN

    def test_http_503(self):
        cls = classify_error(http_status=503)
        assert cls.category == ErrorCategory.PROVIDER
        assert cls.auto_recovery_strategy == AutoRecoveryStrategy.RETRY_OR_SWITCH

    def test_exception_tool(self):
        cls = classify_error(ToolExecutionError(tool_name="web_search", reason="timeout"))
        assert cls.category == ErrorCategory.TOOL_EXECUTION
        assert "web_search" in str(cls.root_cause)

    def test_exception_memory(self):
        cls = classify_error(MemoryError())
        assert cls.category == ErrorCategory.MEMORY

    def test_exception_planner(self):
        cls = classify_error(PlannerError())
        assert cls.category == ErrorCategory.INTERNAL_BUG

    def test_exception_stream(self):
        cls = classify_error(StreamError())
        assert cls.category == ErrorCategory.STREAMING

    def test_exception_timeout(self):
        cls = classify_error(ProviderTimeoutError("google", "chat", 60.0))
        assert cls.category == ErrorCategory.TIMEOUT
        assert cls.auto_recovery_strategy == AutoRecoveryStrategy.RETRY_OR_SWITCH
        assert "google" in cls.root_cause

    def test_exception_connection(self):
        cls = classify_error(ConnectionError("refused"))
        assert cls.category == ErrorCategory.NETWORK

    def test_exception_permission(self):
        cls = classify_error(PermissionError("denied"))
        assert cls.category == ErrorCategory.PERMISSION
        assert not cls.recoverable

    def test_module_heuristic_voice(self):
        cls = classify_error(RuntimeError("boom"), module="voice.stt")
        assert cls.category == ErrorCategory.VOICE

    def test_module_heuristic_db(self):
        cls = classify_error(RuntimeError("boom"), module="aios.core.database")
        assert cls.category == ErrorCategory.DATABASE

    def test_module_heuristic_does_not_shadow_provider(self):
        cls = classify_error(ConnectionError("down"), module="voice.stt")
        assert cls.category == ErrorCategory.NETWORK

    def test_fallback_unknown(self):
        cls = classify_error(RuntimeError("mystery"))
        assert cls.category == ErrorCategory.UNKNOWN


class TestService:
    def test_capture_plain(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=10)
        e = svc.capture(
            "provider 503",
            category=ErrorCategory.PROVIDER,
            severity=Severity.HIGH,
            module="smart_router",
            provider="nvidia",
            http_status=503,
        )
        assert e is not None
        assert e.category == ErrorCategory.PROVIDER
        assert len(svc.list_events()) == 1

    def test_capture_exception_fields(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=10)
        try:
            raise RuntimeError("empty response")
        except RuntimeError as exc:
            e = svc.capture_exception(
                exc,
                module="conversation.manager",
                provider="google",
                model="gemini-1.5-flash",
                request_id="req-1",
                conversation_id="conv-1",
                http_status=500,
            )
        assert e is not None
        assert e.exception_type == "RuntimeError"
        assert e.provider == "google"
        assert e.model == "gemini-1.5-flash"
        assert e.request_id == "req-1"
        assert e.conversation_id == "conv-1"
        assert e.stack_trace and "RuntimeError" in e.stack_trace
        assert e.category in ErrorCategory

    def test_bounded_ring(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=5)
        ids = []
        for i in range(12):
            e = svc.capture(f"error {i}", module="m")
            ids.append(e.error_id)
        assert len(svc.list_events()) == 5
        kept = svc.list_events()
        assert kept[0].error_id == ids[-1]
        assert kept[-1].error_id == ids[-5]

    def test_persistence_round_trip(self, tmp_path):
        path = tmp_path / "errors.json"
        svc = ErrorIntelligenceService(errors_path=path, max_events=10)
        svc.capture("hello", category=ErrorCategory.NETWORK, module="m")
        reloaded = ErrorIntelligenceService(errors_path=path, max_events=10)
        events = reloaded.list_events()
        assert len(events) == 1
        assert events[0].message == "hello"
        assert events[0].category == ErrorCategory.NETWORK

    def test_persistence_round_trip_enum_coercion(self, tmp_path):
        path = tmp_path / "errors.json"
        svc = ErrorIntelligenceService(errors_path=path, max_events=10)
        svc.capture("net fail", category=ErrorCategory.NETWORK, severity=Severity.HIGH, module="m")
        svc.capture("quota", category=ErrorCategory.RATE_LIMIT, severity=Severity.MEDIUM, module="m", provider="nvidia")
        reloaded = ErrorIntelligenceService(errors_path=path, max_events=10)
        for e in reloaded.list_events():
            assert isinstance(e.category, ErrorCategory)
            assert isinstance(e.severity, Severity)
        stats = reloaded.stats()
        assert stats["total"] == 2
        assert stats["by_category"]["NETWORK"] == 1
        assert stats["by_category"]["RATE_LIMIT"] == 1
        assert stats["by_severity"]["HIGH"] == 1
        filtered = reloaded.list_events(category="RATE_LIMIT", severity="MEDIUM")
        assert len(filtered) == 1
        assert filtered[0].provider == "nvidia"

    def test_stats(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=50)
        for i in range(3):
            svc.capture("timeout", category=ErrorCategory.TIMEOUT, severity=Severity.HIGH, module="m", provider="google")
        svc.capture("quota", category=ErrorCategory.RATE_LIMIT, severity=Severity.MEDIUM, module="m", provider="nvidia")
        stats = svc.stats()
        assert stats["total"] == 4
        assert stats["by_category"]["TIMEOUT"] == 3
        assert stats["top_failing_providers"]["google"] == 3
        assert stats["most_common_errors"]["timeout"] == 3

    def test_timeline_and_recoveries(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=50)
        e = svc.capture("boom", category=ErrorCategory.PROVIDER, module="m")
        tl = svc.timeline()
        assert tl[0]["type"] == "error"
        assert tl[0]["error_id"] == e.error_id
        assert svc.recoveries() == []
        svc.record_recovery_result(e.error_id, success=True, note="switched provider")
        rec = svc.recoveries()
        assert len(rec) == 1
        assert rec[0].recovery_result == "recovered"
        assert rec[0].resolved
        assert svc.stats()["auto_recoveries"]["recovered"] == 1
        assert svc.stats()["recovery_success_rate"] == 100.0

    def test_report_formats(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=10)
        e = svc.capture("boom", category=ErrorCategory.RATE_LIMIT, module="m")
        md = svc.report(e.error_id, fmt="markdown")
        js = svc.report(e.error_id, fmt="json")
        pl = svc.report(e.error_id, fmt="plain")
        assert md and "Error ID" in md and "RATE_LIMIT" in md
        assert js and '"category": "RATE_LIMIT"' in js
        assert pl and "RATE_LIMIT" in pl
        assert svc.report("does-not-exist") is None

    def test_clear(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=10)
        svc.capture("x", module="m")
        svc.clear()
        assert svc.list_events() == []
        assert svc.timeline() == []
        assert svc.stats()["total"] == 0

    def test_capture_never_raises(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=10)
        e = svc.capture_exception(object())  # not a BaseException subclass path
        # capture_exception with a non-exception coerces safely or returns None
        assert e is None or isinstance(e, ErrorEvent)

    def test_bad_persistence_file_tolerated(self, tmp_path):
        path = tmp_path / "errors.json"
        path.write_text("{not valid json", encoding="utf-8")
        svc = ErrorIntelligenceService(errors_path=path, max_events=10)
        assert svc.list_events() == []


class TestStreamEventAdapter:
    def test_backward_compatible_shape(self, tmp_path):
        svc = ErrorIntelligenceService(errors_path=tmp_path / "errors.json", max_events=10)
        e = svc.capture(
            "provider failed",
            category=ErrorCategory.PROVIDER,
            module="smart_router",
            recoverable=True,
        )
        ev = error_to_stream_event(e)
        assert ev["type"] == "error"
        data = ev["data"]
        assert data["error"] == "provider failed"
        assert data["recoverable"] is True
        assert data["category"] == "PROVIDER"
        assert data["error_id"] == e.error_id


class TestRecoveryEngine:
    @pytest.mark.asyncio
    async def test_suggest_only_returns_no_action(self, tmp_path):
        from aios.error_intelligence.recovery_engine import RecoveryEngine
        from aios.error_intelligence.service import configure_error_intelligence
        svc = configure_error_intelligence(errors_path=tmp_path / "errors.json", max_events=10)
        e = svc.capture("bad key", category=ErrorCategory.AUTHENTICATION, module="m")
        cls = classify_error(message="bad key", module="m")
        engine = RecoveryEngine()
        result = await engine.attempt_recovery(e, cls)
        assert not result.success
        assert result.action == "none"

    @pytest.mark.asyncio
    async def test_retry_no_router_returns_failure(self, tmp_path):
        from aios.error_intelligence.recovery_engine import RecoveryEngine
        from aios.error_intelligence.service import configure_error_intelligence
        svc = configure_error_intelligence(errors_path=tmp_path / "errors.json", max_events=10)
        e = svc.capture("timeout", category=ErrorCategory.TIMEOUT, module="m")
        cls = classify_error(message="timeout", module="m")
        engine = RecoveryEngine()
        result = await engine.attempt_recovery(e, cls)
        assert not result.success
        assert result.action in ("retry", "switch", "cooldown")

    @pytest.mark.asyncio
    async def test_recovery_records_result(self, tmp_path):
        from aios.error_intelligence.recovery_engine import RecoveryEngine
        from aios.error_intelligence.service import configure_error_intelligence
        svc = configure_error_intelligence(errors_path=tmp_path / "errors.json", max_events=10)
        e = svc.capture("timeout", category=ErrorCategory.TIMEOUT, module="m")
        cls = classify_error(message="timeout", module="m")
        engine = RecoveryEngine()
        await engine.attempt_recovery(e, cls)
        rec = svc.recoveries()
        assert len(rec) == 1
        assert rec[0].error_id == e.error_id
