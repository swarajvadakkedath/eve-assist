"""Tracing utilities for diagnosing async hangs and sync-blocking-in-async.

Provides structured log entries (entering/exiting/duration/threw) for every
instrumented function plus deadlock-safe asyncio.wait_for wrappers.
"""

import asyncio
import functools
import time
from contextlib import asynccontextmanager, contextmanager

from aios.utils.logger import get_logger

_log = get_logger("aios.tracer")


# ---------------------------------------------------------------------------
#  Async decorator & context-manager
# ---------------------------------------------------------------------------

FUTURE_WARN_SECONDS = 15.0


def trace_async(func=None, *, category: str = "trace"):
    """Log entering / exiting (+duration / +threw) for an async function.

    Can be used bare (``@trace_async``) or parametrised (``@trace_async(category="stream")``).
    The *category* prefix is used in the structured log event (e.g. "stream.entering").
    """
    if func is None:
        return lambda f: _make_async_tracer(f, category)
    return _make_async_tracer(func, category)


def _make_async_tracer(func, category: str):
    mod = func.__module__
    qual = func.__qualname__

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        _t = time.monotonic()
        _log.info(f"{category}.entering", function=f"{mod}.{qual}")
        try:
            result = await func(*args, **kwargs)
            elapsed = time.monotonic() - _t
            _log.info(f"{category}.exiting", function=f"{mod}.{qual}", duration_ms=round(elapsed * 1000))
            return result
        except Exception as e:
            elapsed = time.monotonic() - _t
            _log.error(f"{category}.threw", function=f"{mod}.{qual}", duration_ms=round(elapsed * 1000), error=str(e))
            raise

    return wrapper


@asynccontextmanager
async def trace_async_block(name: str, category: str = "trace"):
    """Context manager that logs entering/exiting for an async code block."""
    _t = time.monotonic()
    _log.info(f"{category}.entering", function=name)
    try:
        yield
    except Exception as e:
        elapsed = time.monotonic() - _t
        _log.error(f"{category}.threw", function=name, duration_ms=round(elapsed * 1000), error=str(e))
        raise
    else:
        elapsed = time.monotonic() - _t
        _log.info(f"{category}.exiting", function=name, duration_ms=round(elapsed * 1000))


# ---------------------------------------------------------------------------
#  Sync decorator & context-manager (warns when called from async context)
# ---------------------------------------------------------------------------

def trace_sync(func=None, *, category: str = "sync"):
    """Log entering/exiting for a synchronous function.

    If the call takes longer than FUTURE_WARN_SECONDS it will emit a warning.
    """
    if func is None:
        return lambda f: _make_sync_tracer(f, category)
    return _make_sync_tracer(func, category)


def _make_sync_tracer(func, category: str):
    mod = func.__module__
    qual = func.__qualname__

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        _t = time.monotonic()
        _log.warning(f"{category}.entering", function=f"{mod}.{qual}")
        try:
            result = func(*args, **kwargs)
            elapsed = time.monotonic() - _t
            if elapsed >= FUTURE_WARN_SECONDS:
                _log.error(f"{category}.blocked_event_loop", function=f"{mod}.{qual}",
                           duration_ms=round(elapsed * 1000))
            else:
                _log.info(f"{category}.exiting", function=f"{mod}.{qual}", duration_ms=round(elapsed * 1000))
            return result
        except Exception as e:
            elapsed = time.monotonic() - _t
            _log.error(f"{category}.threw", function=f"{mod}.{qual}", duration_ms=round(elapsed * 1000), error=str(e))
            raise

    return wrapper


@contextmanager
def trace_sync_block(name: str, category: str = "sync"):
    """Context manager that logs entering/exiting for a synchronous block."""
    _t = time.monotonic()
    _log.warning(f"{category}.entering", function=name)
    try:
        yield
    except Exception as e:
        elapsed = time.monotonic() - _t
        _log.error(f"{category}.threw", function=name, duration_ms=round(elapsed * 1000), error=str(e))
        raise
    else:
        elapsed = time.monotonic() - _t
        if elapsed >= FUTURE_WARN_SECONDS:
            _log.error(f"{category}.blocked_event_loop", function=name, duration_ms=round(elapsed * 1000))
        else:
            _log.info(f"{category}.exiting", function=name, duration_ms=round(elapsed * 1000))


# ---------------------------------------------------------------------------
#  Async-generator decorator
# ---------------------------------------------------------------------------

def trace_async_gen(func=None, *, category: str = "trace"):
    """Log entering / exiting for an async generator function.

    Logs *entering* before the first ``yield``, *exiting* after the final
    ``yield`` (or exception), and *duration_ms* on each terminal event.
    """
    if func is None:
        return lambda f: _make_async_gen_tracer(f, category)
    return _make_async_gen_tracer(func, category)


def _make_async_gen_tracer(func, category: str):
    mod = func.__module__
    qual = func.__qualname__

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        _t_start = time.monotonic()
        _first_yield_logged = False
        _log.info(f"{category}.entering", function=f"{mod}.{qual}")
        try:
            async for item in func(*args, **kwargs):
                if not _first_yield_logged:
                    _log.info(f"{category}.first_yield", function=f"{mod}.{qual}",
                              duration_ms=round((time.monotonic() - _t_start) * 1000))
                    _first_yield_logged = True
                yield item
            _log.info(f"{category}.exiting", function=f"{mod}.{qual}",
                      duration_ms=round((time.monotonic() - _t_start) * 1000))
        except Exception as e:
            elapsed = time.monotonic() - _t_start
            _log.error(f"{category}.threw", function=f"{mod}.{qual}",
                       duration_ms=round(elapsed * 1000), error=str(e))
            raise

    return wrapper


# ---------------------------------------------------------------------------
#  Timeout helpers
# ---------------------------------------------------------------------------

class AsyncTimeoutError(asyncio.TimeoutError):
    """Raised when an instrumented async call times out."""


async def call_with_timeout(coro, timeout: float = FUTURE_WARN_SECONDS, label: str = ""):
    """Wrap an awaitable with a timeout, logging entering/exiting.

    Raises ``AsyncTimeoutError`` (subclass of ``asyncio.TimeoutError``) on
    timeout.
    """
    _t = time.monotonic()
    _log.info("timeout.entering", function=label, timeout=timeout)
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        elapsed = time.monotonic() - _t
        _log.info("timeout.exiting", function=label, duration_ms=round(elapsed * 1000))
        return result
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - _t
        _log.error("timeout.triggered", function=label, timeout=timeout, duration_ms=round(elapsed * 1000))
        raise AsyncTimeoutError(f"{label} timed out after {timeout}s") from None
    except Exception as e:
        elapsed = time.monotonic() - _t
        _log.error("timeout.threw", function=label, duration_ms=round(elapsed * 1000), error=str(e))
        raise


@asynccontextmanager
async def async_timeout_block(name: str, timeout: float = FUTURE_WARN_SECONDS):
    """Context manager wrapping an async block with a timeout."""
    _t = time.monotonic()
    _log.info("timeout.entering", function=name, timeout=timeout)
    try:
        yield
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - _t
        _log.error("timeout.triggered", function=name, timeout=timeout, duration_ms=round(elapsed * 1000))
        raise AsyncTimeoutError(f"{name} timed out after {timeout}s") from None
    except Exception as e:
        elapsed = time.monotonic() - _t
        _log.error("timeout.threw", function=name, duration_ms=round(elapsed * 1000), error=str(e))
        raise
    else:
        elapsed = time.monotonic() - _t
        _log.info("timeout.exiting", function=name, duration_ms=round(elapsed * 1000))
