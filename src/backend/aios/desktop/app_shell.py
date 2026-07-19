"""Application Shell — startup, shutdown, single-instance, crash recovery.

Sprint 12.1 — Application Shell.
"""

import asyncio
import os
import signal
import sys
import tempfile
from datetime import datetime
from typing import Callable, Any

from aios.desktop.status_service import StatusService, AppStatus
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class AppShell:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._status_service = StatusService()
        self._startup_hooks: list[Callable] = []
        self._shutdown_hooks: list[Callable] = []
        self._crash_hooks: list[Callable] = []
        self._is_running = False
        self._is_shutting_down = False
        self._lock_file = None
        self._lock_path = None
        self._initialized = True

    async def initialize(self, lock_path: str | None = None) -> None:
        if lock_path:
            self._lock_path = lock_path
        else:
            self._lock_path = os.path.join(
                tempfile.gettempdir(), "aios_instance.lock"
            )

    async def start(self) -> None:
        if self._is_running:
            return
        if not self._acquire_lock():
            raise RuntimeError("Another AIOS instance is already running")
        self._is_running = True
        await self._status.set_status(AppStatus.STARTING)
        for hook in self._startup_hooks:
            try:
                await hook()
            except Exception as e:
                logger.error("startup_hook_failed", error=str(e))
        await self._status.set_status(AppStatus.READY)

    async def shutdown(self) -> None:
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        self._is_running = False
        for hook in reversed(self._shutdown_hooks):
            try:
                await hook()
            except Exception as e:
                logger.error("shutdown_hook_failed", error=str(e))
        self._release_lock()

    def add_startup_hook(self, hook: callable) -> None:
        self._startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: callable) -> None:
        self._shutdown_hooks.append(hook)

    def add_crash_hook(self, hook: callable) -> None:
        self._crash_hooks.append(hook)

    def _acquire_lock(self) -> bool:
        if not self._lock_path:
            return True
        try:
            self._lock_file = open(self._lock_path, "w")
            import msvcrt
            try:
                msvcrt.lockf(self._lock_file.fileno(), msvcrt.LOCK_EX | msvcrt.LOCK_NB, 1)
                self._lock_file.write(str(os.getpid()))
                self._lock_file.flush()
                return True
            except OSError:
                return False
        except Exception as e:
            logger.error("lock.acquire_failed", error=str(e))
            return False

    def _release_lock(self) -> None:
        if self._lock_file:
            try:
                import msvcrt
                msvcrt.lockf(self._lock_file.fileno(), msvcrt.LOCK_UN, 1)
                self._lock_file.close()
            except Exception:
                pass
            self._lock_file = None
