"""Configurable timeout and retry utilities for all external provider requests."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ProviderTimeoutError(asyncio.TimeoutError):
    """Raised when a provider request exceeds its configured timeout."""

    def __init__(self, provider_id: str, operation: str, timeout: float):
        self.provider_id = provider_id
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Provider {provider_id} {operation} timed out after {timeout}s")


class ProviderRetryExhausted(Exception):
    """Raised when all retry attempts fail."""

    def __init__(self, provider_id: str, operation: str, attempts: int, last_error: str):
        self.provider_id = provider_id
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Provider {provider_id} {operation} failed after {attempts} attempts: {last_error}")


# ---------------------------------------------------------------------------
# Timeout config
# ---------------------------------------------------------------------------

@dataclass
class TimeoutConfig:
    """Per-operation timeout configuration."""

    validate_key: float = 10.0
    list_models: float = 30.0
    chat: float = 60.0
    streaming: float = 120.0
    vision: float = 60.0
    embeddings: float = 30.0
    speech: float = 30.0
    image: float = 60.0
    health: float = 10.0

    def for_operation(self, operation: str) -> float:
        return getattr(self, operation, 30.0)


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

class RetryStrategy(Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    JITTER = "jitter"


@dataclass
class RetryPolicy:
    """Retry policy for provider requests."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_statuses: set[int] = field(default_factory=lambda: {408, 429, 500, 502, 503, 504})
    retryable_exceptions: tuple[type[Exception], ...] = (
        asyncio.TimeoutError,
        ConnectionError,
        TimeoutError,
    )


# ---------------------------------------------------------------------------
# Core timeout + retry
# ---------------------------------------------------------------------------

async def call_with_timeout(
    coro: Any,
    timeout: float,
    provider_id: str = "",
    operation: str = "request",
) -> Any:
    """Execute a coroutine with a hard timeout, raising ProviderTimeoutError."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise ProviderTimeoutError(provider_id, operation, timeout)


async def retry_with_backoff(
    fn: Callable[[], Any],
    policy: RetryPolicy | None = None,
    provider_id: str = "",
    operation: str = "request",
) -> Any:
    """Execute fn with retries per the retry policy."""
    policy = policy or RetryPolicy()
    last_error: Exception | None = None

    for attempt in range(policy.max_retries + 1):
        try:
            return await fn()
        except policy.retryable_exceptions as e:
            last_error = e
            if attempt < policy.max_retries:
                delay = _compute_delay(attempt, policy)
                logger.warning(
                    "retry.schedule",
                    provider=provider_id,
                    operation=operation,
                    attempt=attempt + 1,
                    max_retries=policy.max_retries,
                    delay=round(delay, 2),
                    error=str(e),
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "retry.exhausted",
                    provider=provider_id,
                    operation=operation,
                    attempts=policy.max_retries + 1,
                    error=str(e),
                )
                raise ProviderRetryExhausted(
                    provider_id, operation, policy.max_retries + 1, str(e)
                ) from e
        except Exception as e:
            raise

    raise ProviderRetryExhausted(provider_id, operation, policy.max_retries + 1, str(last_error or "unknown"))


def _compute_delay(attempt: int, policy: RetryPolicy) -> float:
    """Compute delay for a given attempt based on strategy."""
    if policy.strategy == RetryStrategy.FIXED:
        delay = policy.base_delay
    elif policy.strategy == RetryStrategy.EXPONENTIAL:
        delay = policy.base_delay * (2 ** attempt)
    else:
        import random
        delay = policy.base_delay * (2 ** attempt)
        delay = delay * (0.5 + random.random() * 0.5)

    return min(delay, policy.max_delay)


# ---------------------------------------------------------------------------
# Per-provider timeout registry
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUTS: dict[str, TimeoutConfig] = {}


def get_timeout_config(provider_type: str) -> TimeoutConfig:
    """Get timeout config for a provider type, falling back to defaults."""
    return DEFAULT_TIMEOUTS.get(provider_type, TimeoutConfig())


def set_timeout_config(provider_type: str, config: TimeoutConfig):
    """Override timeout config for a specific provider type."""
    DEFAULT_TIMEOUTS[provider_type] = config
