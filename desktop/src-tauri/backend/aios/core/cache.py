"""Model cache with TTL, background refresh, and offline support."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CacheEntry:
    data: Any
    fetched_at: float
    ttl: float
    etag: str = ""
    stale_at: float = 0.0

    @property
    def is_fresh(self) -> bool:
        return (time.monotonic() - self.fetched_at) < self.ttl

    @property
    def is_stale(self) -> bool:
        return (time.monotonic() - self.fetched_at) >= self.ttl


class ModelCache:
    """Thread-safe, TTL-based model list cache with background refresh.

    - Returns cached data instantly for UI.
    - Triggers background refresh when stale.
    - Supports ETag-based conditional requests to save bandwidth.
    - Gracefully serves stale data when offline.
    """

    def __init__(
        self,
        default_ttl: float = 300.0,
        stale_ttl: float = 86400.0,
        refresh_interval: float = 600.0,
    ):
        self._default_ttl = default_ttl
        self._stale_ttl = stale_ttl
        self._refresh_interval = refresh_interval
        self._entries: dict[str, CacheEntry] = {}
        self._background_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    # -- Public API ---------------------------------------------------------

    async def get(
        self,
        key: str,
        fetcher: Callable[[], Any] | None = None,
        ttl: float | None = None,
        etag: str | None = None,
    ) -> Any:
        """Get cached data. If missing or stale, call fetcher.

        If fetcher raises, returns stale data if available.
        """
        async with self._lock:
            entry = self._entries.get(key)

            if entry and entry.is_fresh:
                return entry.data

            if entry and entry.is_stale and fetcher is None:
                return entry.data

        if fetcher is None:
            return entry.data if entry else None

        try:
            result = await fetcher()
            async with self._lock:
                self._entries[key] = CacheEntry(
                    data=result,
                    fetched_at=time.monotonic(),
                    ttl=ttl or self._default_ttl,
                    etag=etag or "",
                )
            return result
        except Exception as e:
            logger.warning("cache.fetch_failed", key=key, error=str(e))
            if entry and entry.is_stale and (time.monotonic() - entry.fetched_at) < self._stale_ttl:
                logger.info("cache.serving_stale", key=key)
                return entry.data
            raise

    async def set(self, key: str, data: Any, ttl: float | None = None):
        async with self._lock:
            self._entries[key] = CacheEntry(
                data=data,
                fetched_at=time.monotonic(),
                ttl=ttl or self._default_ttl,
            )

    async def invalidate(self, key: str):
        async with self._lock:
            self._entries.pop(key, None)

    async def get_etag(self, key: str) -> str:
        async with self._lock:
            entry = self._entries.get(key)
            return entry.etag if entry else ""

    async def clear(self):
        async with self._lock:
            self._entries.clear()

    # -- Background refresh -------------------------------------------------

    def start_background_refresh(
        self,
        key: str,
        fetcher: Callable[[], Any],
        interval: float | None = None,
    ):
        """Start periodic background refresh for a key.

        The task runs forever; cancel it via cancel_background_refresh.
        """
        if key in self._background_tasks:
            return

        async def _refresh_loop():
            while True:
                try:
                    await asyncio.sleep(interval or self._refresh_interval)
                    async with self._lock:
                        entry = self._entries.get(key)
                        etag = entry.etag if entry else ""

                    result = await fetcher()
                    async with self._lock:
                        self._entries[key] = CacheEntry(
                            data=result,
                            fetched_at=time.monotonic(),
                            ttl=self._default_ttl,
                            etag=etag,
                        )
                    logger.debug("cache.background_refreshed", key=key)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning("cache.background_refresh_failed", key=key, error=str(e))

        task = asyncio.create_task(_refresh_loop())
        self._background_tasks[key] = task

    def cancel_background_refresh(self, key: str):
        task = self._background_tasks.pop(key, None)
        if task:
            task.cancel()

    def cancel_all(self):
        for key in list(self._background_tasks.keys()):
            self.cancel_background_refresh(key)
