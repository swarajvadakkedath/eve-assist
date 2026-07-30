"""Per-provider health monitoring with isolation — one failure never affects another."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from aios.core.adapters.base import AIProviderAdapter, ProviderStatus
from aios.core.timeout_retry import call_with_timeout, ProviderTimeoutError

logger = structlog.get_logger(__name__)


class HealthState(Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    INVALID_KEY = "invalid_key"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"


@dataclass
class ProviderHealth:
    provider_id: str
    state: HealthState = HealthState.UNKNOWN
    status: ProviderStatus = ProviderStatus.DISCONNECTED
    last_check: float = 0.0
    last_success: float = 0.0
    last_failure: float = 0.0
    consecutive_failures: int = 0
    latency_ms: float = 0.0
    error_message: str = ""
    history: list[dict] = field(default_factory=lambda: [])

    def record_success(self, latency_ms: float):
        now = time.monotonic()
        self.state = HealthState.HEALTHY
        self.status = ProviderStatus.CONNECTED
        self.last_check = now
        self.last_success = now
        self.consecutive_failures = 0
        self.latency_ms = latency_ms
        self.error_message = ""
        self._add_history("success", latency_ms=latency_ms)

    def record_failure(self, status: ProviderStatus, error: str, latency_ms: float = 0.0):
        now = time.monotonic()
        self.status = status
        self.last_check = now
        self.last_failure = now
        self.consecutive_failures += 1
        self.error_message = error
        self.latency_ms = latency_ms

        if status in (ProviderStatus.INVALID_KEY, ProviderStatus.AUTH_FAILED):
            self.state = HealthState.INVALID_KEY
        elif status == ProviderStatus.RATE_LIMITED:
            self.state = HealthState.RATE_LIMITED
        elif status == ProviderStatus.QUOTA_EXCEEDED:
            self.state = HealthState.QUOTA_EXCEEDED
        elif status == ProviderStatus.TIMEOUT:
            self.state = HealthState.DEGRADED
        elif status in (ProviderStatus.OFFLINE, ProviderStatus.DISCONNECTED):
            self.state = HealthState.UNREACHABLE
        else:
            self.state = HealthState.DEGRADED if self.consecutive_failures < 3 else HealthState.UNREACHABLE

        self._add_history("failure", status=status.value, error=error, latency_ms=latency_ms)

    def _add_history(self, event_type: str, **kwargs):
        self.history.append({"type": event_type, "timestamp": time.monotonic(), **kwargs})
        if len(self.history) > 100:
            self.history = self.history[-100:]


class HealthMonitor:
    """Monitors health of all providers independently.

    Each provider is isolated — one failure never cascades.
    """

    def __init__(self, check_interval: float = 60.0):
        self._check_interval = check_interval
        self._health: dict[str, ProviderHealth] = {}
        self._task: asyncio.Task | None = None

    def register_provider(self, provider_id: str):
        if provider_id not in self._health:
            self._health[provider_id] = ProviderHealth(provider_id=provider_id)

    def unregister_provider(self, provider_id: str):
        self._health.pop(provider_id, None)

    def get_health(self, provider_id: str) -> ProviderHealth | None:
        return self._health.get(provider_id)

    def get_all_health(self) -> dict[str, ProviderHealth]:
        return dict(self._health)

    async def check_provider(self, provider_id: str, adapter: AIProviderAdapter) -> ProviderHealth:
        """Check a single provider's health."""
        health = self._health.setdefault(provider_id, ProviderHealth(provider_id=provider_id))

        start = time.monotonic()
        try:
            await call_with_timeout(
                adapter.health(),
                timeout=10.0,
                provider_id=provider_id,
                operation="health",
            )
            elapsed = (time.monotonic() - start) * 1000
            health.record_success(elapsed)
        except ProviderTimeoutError:
            elapsed = (time.monotonic() - start) * 1000
            health.record_failure(ProviderStatus.TIMEOUT, "Health check timed out", elapsed)
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            err_str = str(e)
            if "401" in err_str or "403" in err_str or "unauthorized" in err_str.lower():
                health.record_failure(ProviderStatus.AUTH_FAILED, err_str, elapsed)
            elif "429" in err_str or "rate" in err_str.lower():
                health.record_failure(ProviderStatus.RATE_LIMITED, err_str, elapsed)
            elif "quota" in err_str.lower():
                health.record_failure(ProviderStatus.QUOTA_EXCEEDED, err_str, elapsed)
            else:
                health.record_failure(ProviderStatus.ERROR, err_str, elapsed)

        return health

    async def check_all(
        self,
        adapters: dict[str, AIProviderAdapter],
    ) -> dict[str, ProviderHealth]:
        """Check all providers concurrently with full isolation."""
        tasks = {}
        for pid, adapter in adapters.items():
            tasks[pid] = asyncio.create_task(self.check_provider(pid, adapter))

        results = {}
        for pid, task in tasks.items():
            try:
                results[pid] = await task
            except Exception as e:
                health = self._health.get(pid, ProviderHealth(provider_id=pid))
                health.record_failure(ProviderStatus.ERROR, str(e))
                results[pid] = health

        return results

    def start_background_check(
        self,
        adapters_fn,
        interval: float | None = None,
    ):
        """Start periodic health checks in the background."""
        if self._task and not self._task.done():
            return

        async def _loop():
            while True:
                try:
                    adapters = adapters_fn()
                    await self.check_all(adapters)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("health_monitor.background_error", error=str(e))
                await asyncio.sleep(interval or self._check_interval)

        self._task = asyncio.create_task(_loop())

    def stop_background_check(self):
        if self._task:
            self._task.cancel()
            self._task = None
