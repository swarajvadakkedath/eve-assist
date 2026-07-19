"""Workspace Watcher — background polling and change detection."""

import asyncio
from typing import Any, Callable
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class WorkspaceWatcher:
    def __init__(self, poll_interval: float = 2.0):
        self._poll_interval = poll_interval
        self._callbacks: list[Callable] = []
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self, collect_fn: Callable) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(collect_fn))
        logger.info("watcher.started", poll_interval=self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("watcher.stopped")

    async def _poll_loop(self, collect_fn: Callable) -> None:
        while self._running:
            try:
                result = await collect_fn()
                for callback in self._callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.error("watcher.callback_failed", error=str(e))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("watcher.poll_failed", error=str(e))
            await asyncio.sleep(self._poll_interval)

    def subscribe(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)
