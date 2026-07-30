"""Per-provider health monitoring with isolation — one failure never affects another."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from aios.core.adapters.base import AIProviderAdapter, ProviderStatus, sanitize_error
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


class RateLimitState(Enum):
    NONE = "none"
    LOCAL_COOLDOWN = "local"
    PROVIDER_COOLDOWN = "provider"
    QUOTA_EXHAUSTED = "quota"


@dataclass
class RateLimitInfo:
    state: RateLimitState = RateLimitState.NONE
    cooldown_until: float = 0.0
    retry_after_seconds: float = 0.0
    last_429_at: float = 0.0
    consecutive_429s: int = 0
    daily_quota_exhausted: bool = False

    def record_429(self, retry_after: float | None = None, quota_exhausted: bool = False):
        now = time.monotonic()
        self.last_429_at = now
        self.consecutive_429s += 1
        if quota_exhausted:
            self.state = RateLimitState.QUOTA_EXHAUSTED
            self.daily_quota_exhausted = True
            self.cooldown_until = now + 3600.0
        elif retry_after and retry_after > 0:
            self.state = RateLimitState.PROVIDER_COOLDOWN
            self.retry_after_seconds = retry_after
            self.cooldown_until = now + retry_after
        else:
            backoff = min(30.0 * (2 ** (self.consecutive_429s - 1)), 600.0)
            self.state = RateLimitState.LOCAL_COOLDOWN
            self.cooldown_until = now + backoff

    def clear(self):
        self.state = RateLimitState.NONE
        self.cooldown_until = 0.0
        self.retry_after_seconds = 0.0
        self.consecutive_429s = 0
        self.daily_quota_exhausted = False

    def is_in_cooldown(self) -> bool:
        if self.state == RateLimitState.NONE:
            return False
        if self.state == RateLimitState.QUOTA_EXHAUSTED:
            return True
        return time.monotonic() < self.cooldown_until

    def cooldown_remaining(self) -> float:
        if not self.is_in_cooldown():
            return 0.0
        return max(0.0, self.cooldown_until - time.monotonic())

    def to_dict(self) -> dict[str, Any]:
        remaining = self.cooldown_remaining()
        return {
            "state": self.state.value,
            "cooldown_remaining": round(remaining, 1),
            "retry_after_seconds": self.retry_after_seconds,
            "consecutive_429s": self.consecutive_429s,
            "daily_quota_exhausted": self.daily_quota_exhausted,
        }


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
    history: list[dict] = field(default_factory=list)
    rate_limit: RateLimitInfo = field(default_factory=RateLimitInfo)

    def record_success(self, latency_ms: float):
        now = time.monotonic()
        self.state = HealthState.HEALTHY
        self.status = ProviderStatus.CONNECTED
        self.last_check = now
        self.last_success = now
        self.consecutive_failures = 0
        self.latency_ms = latency_ms
        self.error_message = ""
        self.rate_limit.clear()
        self._add_history("success", latency_ms=latency_ms)

    def record_failure(self, status: ProviderStatus, error: str, latency_ms: float = 0.0, retry_after: float | None = None):
        now = time.monotonic()
        self.status = status
        self.last_check = now
        self.last_failure = now
        self.consecutive_failures += 1
        self.error_message = sanitize_error(error)
        self.latency_ms = latency_ms

        if status in (ProviderStatus.INVALID_KEY, ProviderStatus.AUTH_FAILED):
            self.state = HealthState.INVALID_KEY
        elif status == ProviderStatus.RATE_LIMITED:
            self.state = HealthState.RATE_LIMITED
            self.rate_limit.record_429(retry_after=retry_after)
        elif status == ProviderStatus.QUOTA_EXCEEDED:
            self.state = HealthState.QUOTA_EXCEEDED
            self.rate_limit.record_429(quota_exhausted=True)
        elif status == ProviderStatus.TIMEOUT:
            self.state = HealthState.DEGRADED
        elif status in (ProviderStatus.OFFLINE, ProviderStatus.DISCONNECTED):
            self.state = HealthState.UNREACHABLE
        else:
            self.state = HealthState.DEGRADED if self.consecutive_failures < 3 else HealthState.UNREACHABLE

        self._add_history("failure", status=status.value, error=sanitize_error(error), latency_ms=latency_ms)

    def _add_history(self, event_type: str, **kwargs):
        self.history.append({"type": event_type, "timestamp": time.monotonic(), **kwargs})
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "state": self.state.value,
            "status": self.status.value,
            "last_check": self.last_check,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
            "consecutive_failures": self.consecutive_failures,
            "latency_ms": self.latency_ms,
            "error_message": self.error_message,
            "rate_limit": self.rate_limit.to_dict(),
        }


class HealthMonitor:
    """Monitors health of all providers independently.

    Each provider is isolated — one failure never cascades.
    Also tracks per-model rate-limit state via `get_model_rate_limit()`.
    """

    def __init__(self, check_interval: float = 60.0):
        self._check_interval = check_interval
        self._health: dict[str, ProviderHealth] = {}
        self._model_rate_limits: dict[str, RateLimitInfo] = {}
        self._task: asyncio.Task | None = None

    def register_provider(self, provider_id: str):
        if provider_id not in self._health:
            self._health[provider_id] = ProviderHealth(provider_id=provider_id)

    def unregister_provider(self, provider_id: str):
        self._health.pop(provider_id, None)
        keys_to_remove = [k for k in self._model_rate_limits if k.startswith(provider_id + ":")]
        for k in keys_to_remove:
            del self._model_rate_limits[k]

    def get_health(self, provider_id: str) -> ProviderHealth | None:
        return self._health.get(provider_id)

    def get_all_health(self) -> dict[str, ProviderHealth]:
        return dict(self._health)

    def get_model_rate_limit(self, provider_id: str, model_id: str) -> RateLimitInfo:
        key = f"{provider_id}:{model_id}"
        if key not in self._model_rate_limits:
            self._model_rate_limits[key] = RateLimitInfo()
        return self._model_rate_limits[key]

    def record_model_429(self, provider_id: str, model_id: str, retry_after: float | None = None, quota_exhausted: bool = False):
        rl = self.get_model_rate_limit(provider_id, model_id)
        rl.record_429(retry_after=retry_after, quota_exhausted=quota_exhausted)
        logger.warning(
            "model_rate_limited",
            provider_id=provider_id,
            model_id=model_id,
            state=rl.state.value,
            cooldown_remaining=rl.cooldown_remaining(),
        )

    def clear_model_rate_limit(self, provider_id: str, model_id: str):
        key = f"{provider_id}:{model_id}"
        if key in self._model_rate_limits:
            self._model_rate_limits[key].clear()

    def is_model_available(self, provider_id: str, model_id: str) -> bool:
        rl = self.get_model_rate_limit(provider_id, model_id)
        return not rl.is_in_cooldown()

    def get_all_model_rate_limits(self) -> dict[str, dict[str, Any]]:
        return {k: v.to_dict() for k, v in self._model_rate_limits.items()}

    async def check_provider(self, provider_id: str, adapter: AIProviderAdapter) -> ProviderHealth:
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
            retry_after = self._parse_retry_after(err_str)
            if "401" in err_str or "403" in err_str or "unauthorized" in err_str.lower():
                health.record_failure(ProviderStatus.AUTH_FAILED, err_str, elapsed)
            elif "429" in err_str or "rate" in err_str.lower():
                health.record_failure(ProviderStatus.RATE_LIMITED, err_str, elapsed, retry_after=retry_after)
            elif "quota" in err_str.lower():
                health.record_failure(ProviderStatus.QUOTA_EXCEEDED, err_str, elapsed)
            else:
                health.record_failure(ProviderStatus.ERROR, err_str, elapsed)
        return health

    def _parse_retry_after(self, error_str: str) -> float | None:
        import re
        match = re.search(r"retry.after[:\s]*(\d+)", error_str, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    async def check_all(
        self,
        adapters: dict[str, AIProviderAdapter],
    ) -> dict[str, ProviderHealth]:
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
                    logger.error("health_monitor.background_error", error=sanitize_error(str(e)[:200]))
                await asyncio.sleep(interval or self._check_interval)

        self._task = asyncio.create_task(_loop())

    def stop_background_check(self):
        if self._task:
            self._task.cancel()
            self._task = None
