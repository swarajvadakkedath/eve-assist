"""AI Router — provider abstraction, routing, failover, rate limiting, and cost tracking."""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator

import structlog

from aios.config.settings import AiosSettings
from aios.utils.tracer import trace_async, call_with_timeout, AsyncTimeoutError, trace_async_gen

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class AIRequest:
    messages: list[dict]
    tools: list[dict] | None = None
    stream: bool = False
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class AIResponse:
    content: str
    provider: str
    model: str
    tokens_used: int = 0
    cost: float = 0.0
    tool_calls: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Provider abstract base
# ---------------------------------------------------------------------------

class AIProvider(ABC):
    @abstractmethod
    async def chat(self, request: AIRequest) -> AIResponse:
        ...

    @abstractmethod
    async def chat_stream(self, request: AIRequest) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @property
    @abstractmethod
    def model(self) -> str: ...

    @property
    @abstractmethod
    def capabilities(self) -> set[str]: ...


# ---------------------------------------------------------------------------
# Routing strategy
# ---------------------------------------------------------------------------

class RoutingStrategy(Enum):
    PRIORITY = "priority"
    COST = "cost"
    LATENCY = "latency"
    PERFORMANCE = "performance"


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

@dataclass
class CircuitState:
    failures: int = 0
    last_failure: float = 0.0
    open_until: float = 0.0


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state: dict[str, CircuitState] = {}

    def is_open(self, provider: str) -> bool:
        state = self._state.get(provider)
        if not state:
            return False
        if state.failures >= self._failure_threshold:
            if time.monotonic() >= state.open_until:
                state.failures = 0
                return False
            return True
        return False

    def record_success(self, provider: str) -> None:
        self._state.pop(provider, None)

    def record_failure(self, provider: str) -> None:
        now = time.monotonic()
        state = self._state.setdefault(provider, CircuitState())
        state.failures += 1
        state.last_failure = now
        if state.failures >= self._failure_threshold:
            state.open_until = now + self._recovery_timeout
            logger.warning("circuit.opened", provider=provider, duration=self._recovery_timeout)

    def reset(self, provider: str) -> None:
        self._state.pop(provider, None)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

@dataclass
class TokenBucket:
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(self, requests_per_minute: int = 60, tokens_per_minute: int = 100000):
        self._rpm = requests_per_minute
        self._tpm = tokens_per_minute
        self._request_buckets: dict[str, TokenBucket] = {}
        self._token_buckets: dict[str, TokenBucket] = {}

    def check(self, provider: str, estimated_tokens: int = 0) -> bool:
        now = time.monotonic()

        req_bucket = self._request_buckets.setdefault(provider, TokenBucket(tokens=float(self._rpm), last_refill=now))
        req_bucket.tokens += (now - req_bucket.last_refill) * (self._rpm / 60.0)
        req_bucket.last_refill = now
        if req_bucket.tokens > self._rpm:
            req_bucket.tokens = float(self._rpm)
        if req_bucket.tokens < 1:
            return False
        req_bucket.tokens -= 1

        if estimated_tokens > 0:
            tok_bucket = self._token_buckets.setdefault(provider, TokenBucket(tokens=float(self._tpm), last_refill=now))
            tok_bucket.tokens += (now - tok_bucket.last_refill) * (self._tpm / 60.0)
            tok_bucket.last_refill = now
            if tok_bucket.tokens > self._tpm:
                tok_bucket.tokens = float(self._tpm)
            if tok_bucket.tokens < estimated_tokens:
                return False
            tok_bucket.tokens -= estimated_tokens

        return True

    def reset(self, provider: str) -> None:
        self._request_buckets.pop(provider, None)
        self._token_buckets.pop(provider, None)


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------

@dataclass
class ProviderCost:
    total_cost: float = 0.0
    total_tokens: int = 0
    request_count: int = 0


class CostTracker:
    def __init__(self):
        self._providers: dict[str, ProviderCost] = {}
        self._total_cost: float = 0.0

    def record(self, provider: str, cost: float, tokens: int) -> None:
        entry = self._providers.setdefault(provider, ProviderCost())
        entry.total_cost += cost
        entry.total_tokens += tokens
        entry.request_count += 1
        self._total_cost += cost

    def get_provider_cost(self, provider: str) -> ProviderCost:
        return self._providers.get(provider, ProviderCost())

    def get_total_cost(self) -> float:
        return self._total_cost

    def summary(self) -> dict[str, Any]:
        return {
            "total_cost": self._total_cost,
            "providers": {k: {"cost": v.total_cost, "tokens": v.total_tokens, "requests": v.request_count} for k, v in self._providers.items()},
        }

    def reset(self) -> None:
        self._providers.clear()
        self._total_cost = 0.0


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class AIRouter:
    def __init__(self, settings: AiosSettings | None = None):
        self._settings = settings or AiosSettings()
        self._providers: dict[str, AIProvider] = {}
        self._provider_order: list[str] = []
        self._strategy = RoutingStrategy.PRIORITY

        self._circuit_breaker = CircuitBreaker()
        self._rate_limiter = RateLimiter(
            requests_per_minute=self._settings.rate_limit_requests_per_minute,
            tokens_per_minute=self._settings.rate_limit_tokens_per_minute,
        )
        self._cost_tracker = CostTracker()
        self._latency_cache: dict[str, list[float]] = {}

    # -- Provider management ------------------------------------------------

    @trace_async
    async def register_provider(self, name: str, provider: AIProvider) -> None:
        self._providers[name] = provider
        if name not in self._provider_order:
            self._provider_order.append(name)

    @trace_async
    async def unregister_provider(self, name: str) -> None:
        self._providers.pop(name, None)
        if name in self._provider_order:
            self._provider_order.remove(name)

    def get_provider(self, name: str) -> AIProvider | None:
        return self._providers.get(name)

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        self._strategy = strategy
        logger.info("router.strategy.set", strategy=strategy.value)

    # -- Routing ------------------------------------------------------------

    def _rank_providers(self, request: AIRequest) -> list[str]:
        if self._strategy == RoutingStrategy.PRIORITY:
            return list(self._provider_order)

        ranked = list(self._provider_order)

        if self._strategy == RoutingStrategy.COST:
            ranked.sort(key=lambda name: self._cost_tracker.get_provider_cost(name).total_cost)

        elif self._strategy == RoutingStrategy.LATENCY:
            def avg_latency(name: str) -> float:
                samples = self._latency_cache.get(name, [])
                return sum(samples) / len(samples) if samples else 0.0
            ranked.sort(key=avg_latency)

        elif self._strategy == RoutingStrategy.PERFORMANCE:
            def score(name: str) -> float:
                c = self._cost_tracker.get_provider_cost(name)
                if c.request_count == 0:
                    return 0.0
                return c.total_cost / max(c.request_count, 1) if c.total_cost > 0 else float("inf")
            ranked.sort(key=score)

        return ranked

    @trace_async
    async def route(self, request: AIRequest) -> AIResponse:
        ranked = self._rank_providers(request)
        last_exception: Exception | None = None

        for provider_name in ranked:
            if self._circuit_breaker.is_open(provider_name):
                logger.debug("router.skipping.circuit_open", provider=provider_name)
                continue

            provider = self._providers[provider_name]
            if not self._rate_limiter.check(provider_name, request.max_tokens):
                logger.debug("router.skipping.rate_limited", provider=provider_name)
                continue

            try:
                start = time.monotonic()
                response = await call_with_timeout(
                    provider.chat(request),
                    timeout=30.0,
                    label=f"provider.{provider_name}.chat",
                )
                elapsed = time.monotonic() - start

                self._circuit_breaker.record_success(provider_name)
                self._cost_tracker.record(provider_name, response.cost, response.tokens_used)
                self._latency_cache.setdefault(provider_name, []).append(elapsed)
                if len(self._latency_cache[provider_name]) > 100:
                    self._latency_cache[provider_name] = self._latency_cache[provider_name][-100:]

                logger.info(
                    "router.route.success",
                    provider=provider_name,
                    latency_ms=round(elapsed * 1000),
                    cost=response.cost,
                )

                return response

            except Exception as e:
                last_exception = e
                self._circuit_breaker.record_failure(provider_name)
                logger.warning("router.route.failed", provider=provider_name, error=str(e))
                continue

        raise RuntimeError(f"All AI providers failed") from last_exception

    @trace_async_gen
    async def route_stream(self, request: AIRequest) -> AsyncIterator[str]:
        ranked = self._rank_providers(request)
        last_exception: Exception | None = None

        for provider_name in ranked:
            if self._circuit_breaker.is_open(provider_name):
                continue

            provider = self._providers[provider_name]
            if not self._rate_limiter.check(provider_name, request.max_tokens):
                continue

            try:
                start = time.monotonic()
                token_count = 0
                async for token in provider.chat_stream(request):
                    token_count += 1
                    yield token
                elapsed = time.monotonic() - start

                self._circuit_breaker.record_success(provider_name)
                self._latency_cache.setdefault(provider_name, []).append(elapsed)
                if len(self._latency_cache[provider_name]) > 100:
                    self._latency_cache[provider_name] = self._latency_cache[provider_name][-100:]

                logger.info(
                    "router.route_stream.success",
                    provider=provider_name,
                    latency_ms=round(elapsed * 1000),
                    tokens=token_count,
                )
                return

            except asyncio.TimeoutError:
                last_exception = TimeoutError(f"Provider {provider_name} timed out")
                self._circuit_breaker.record_failure(provider_name)
                logger.warning("router.route_stream.timeout", provider=provider_name)
                continue
            except Exception as e:
                last_exception = e
                self._circuit_breaker.record_failure(provider_name)
                logger.warning("router.route_stream.failed", provider=provider_name, error=str(e))
                continue

        raise RuntimeError(f"All AI providers failed for stream") from last_exception

    # -- Meta ---------------------------------------------------------------

    @trace_async
    async def health_check(self) -> dict[str, bool]:
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.health_check()
            except Exception:
                results[name] = False
        return results

    def get_capabilities(self) -> dict[str, list[str]]:
        return {name: list(provider.capabilities) for name, provider in self._providers.items()}

    @property
    def rate_limiter(self) -> RateLimiter:
        return self._rate_limiter

    @property
    def cost_tracker(self) -> CostTracker:
        return self._cost_tracker

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker
