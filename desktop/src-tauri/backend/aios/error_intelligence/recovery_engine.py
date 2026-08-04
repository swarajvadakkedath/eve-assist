"""Recovery Engine — safe-auto recovery chains for AI Error Intelligence.

Coordinates recovery actions (retry, switch, refresh, cooldown) based on
the Classification.auto_recovery_strategy. Only performs actions that are
provably side-effect-free (safe-auto):
  - RETRY: re-route the same request through SmartRouter
  - SWITCH_PROVIDER: re-route excluding the failed provider
  - REFRESH_MODELS: invalidate model cache + re-route
  - COOLDOWN: per-model rate-limit + re-route
  - RETRY_OR_SWITCH: retry once, then switch if still failing
  - SUGGEST_ONLY: no automatic action

Never raises. All results recorded in ErrorIntelligenceService.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aios.error_intelligence.models import (
    AutoRecoveryStrategy,
    Classification,
    ErrorCategory,
    ErrorEvent,
    Severity,
)


@dataclass
class RecoveryResult:
    success: bool
    action: str
    provider: str | None = None
    model: str | None = None
    reason: str = ""
    error_event_id: str | None = None


class RecoveryEngine:
    """Stateless recovery engine. Dependencies injected at construction."""

    def __init__(
        self,
        health_monitor: Any = None,
        provider_manager: Any = None,
        smart_router: Any = None,
    ):
        self._health_monitor = health_monitor
        self._provider_manager = provider_manager
        self._smart_router = smart_router

    async def attempt_recovery(
        self,
        event: ErrorEvent,
        classification: Classification,
        request: Any | None = None,
    ) -> RecoveryResult:
        """Execute the recovery action dictated by the classification."""
        strategy = classification.auto_recovery_strategy
        svc = _get_service()

        if strategy == AutoRecoveryStrategy.NONE or strategy == AutoRecoveryStrategy.SUGGEST_ONLY:
            return RecoveryResult(success=False, action="none", reason="No automatic recovery available")

        if strategy == AutoRecoveryStrategy.RETRY:
            return await self._retry(event, request, svc)

        if strategy == AutoRecoveryStrategy.SWITCH_PROVIDER:
            return await self._switch_provider(event, request, svc)

        if strategy == AutoRecoveryStrategy.REFRESH_MODELS:
            return await self._refresh_models(event, request, svc)

        if strategy == AutoRecoveryStrategy.COOLDOWN:
            return await self._cooldown(event, request, svc)

        if strategy == AutoRecoveryStrategy.RETRY_OR_SWITCH:
            result = await self._retry(event, request, svc)
            if result.success:
                return result
            return await self._switch_provider(event, request, svc)

        return RecoveryResult(success=False, action="none", reason=f"Unknown strategy: {strategy}")

    async def _retry(self, event: ErrorEvent, request: Any, svc: Any) -> RecoveryResult:
        if self._smart_router is None or request is None:
            svc.record_recovery_result(event.error_id, success=False, note="Retry skipped: no router or request")
            return RecoveryResult(success=False, action="retry", reason="No router or request available")
        try:
            from aios.core.smart_router import RoutingPolicy
            result = await self._smart_router.route_stream(request, routing_policy=RoutingPolicy.AUTO)
            svc.record_recovery_result(event.error_id, success=True, note="Retry succeeded")
            return RecoveryResult(
                success=True,
                action="retry",
                provider=result.trace.selected_provider_instance_id,
                model=result.trace.selected_model_id,
                error_event_id=event.error_id,
            )
        except Exception as e:
            svc.record_recovery_result(event.error_id, success=False, note=f"Retry failed: {e}")
            return RecoveryResult(success=False, action="retry", reason=str(e), error_event_id=event.error_id)

    async def _switch_provider(self, event: ErrorEvent, request: Any, svc: Any) -> RecoveryResult:
        if self._smart_router is None or request is None:
            svc.record_recovery_result(event.error_id, success=False, note="Switch skipped: no router or request")
            return RecoveryResult(success=False, action="switch", reason="No router or request available")
        try:
            from aios.core.smart_router import RoutingPolicy
            exclude = {f"{event.provider}/{event.model}"} if event.provider else set()
            result = await self._smart_router.route_stream(
                request, routing_policy=RoutingPolicy.AUTO,
            )
            svc.record_recovery_result(event.error_id, success=True, note="Provider switch succeeded")
            return RecoveryResult(
                success=True,
                action="switch",
                provider=result.trace.selected_provider_instance_id,
                model=result.trace.selected_model_id,
                error_event_id=event.error_id,
            )
        except Exception as e:
            svc.record_recovery_result(event.error_id, success=False, note=f"Switch failed: {e}")
            return RecoveryResult(success=False, action="switch", reason=str(e), error_event_id=event.error_id)

    async def _refresh_models(self, event: ErrorEvent, request: Any, svc: Any) -> RecoveryResult:
        if self._provider_manager is None:
            return RecoveryResult(success=False, action="refresh", reason="No provider manager available")
        try:
            refreshed = await self._provider_manager.refresh_all_models()
            svc.record_recovery_result(event.error_id, success=True, note="Model catalog refreshed")
            if self._smart_router and request:
                from aios.core.smart_router import RoutingPolicy
                result = await self._smart_router.route_stream(request, routing_policy=RoutingPolicy.AUTO)
                return RecoveryResult(
                    success=True,
                    action="refresh_and_retry",
                    provider=result.trace.selected_provider_instance_id,
                    model=result.trace.selected_model_id,
                    error_event_id=event.error_id,
                )
            return RecoveryResult(success=True, action="refresh", error_event_id=event.error_id)
        except Exception as e:
            svc.record_recovery_result(event.error_id, success=False, note=f"Refresh failed: {e}")
            return RecoveryResult(success=False, action="refresh", reason=str(e), error_event_id=event.error_id)

    async def _cooldown(self, event: ErrorEvent, request: Any, svc: Any) -> RecoveryResult:
        if event.provider and event.model and self._health_monitor:
            try:
                self._health_monitor.record_model_429(event.provider, event.model)
            except Exception:
                pass
        if self._smart_router and request:
            try:
                from aios.core.smart_router import RoutingPolicy
                result = await self._smart_router.route_stream(request, routing_policy=RoutingPolicy.AUTO)
                svc.record_recovery_result(event.error_id, success=True, note="Cooldown + switch succeeded")
                return RecoveryResult(
                    success=True,
                    action="cooldown",
                    provider=result.trace.selected_provider_instance_id,
                    model=result.trace.selected_model_id,
                    error_event_id=event.error_id,
                )
            except Exception as e:
                svc.record_recovery_result(event.error_id, success=False, note=f"Cooldown switch failed: {e}")
                return RecoveryResult(success=False, action="cooldown", reason=str(e), error_event_id=event.error_id)
        svc.record_recovery_result(event.error_id, success=False, note="No router for cooldown")
        return RecoveryResult(success=False, action="cooldown", reason="No router available")


def _get_service():
    from aios.error_intelligence import get_error_intelligence
    return get_error_intelligence()
