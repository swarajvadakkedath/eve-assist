"""Backend service — backend process lifecycle with exit diagnostics."""

import logging
import os
import sys
import time

from launcher.launcher_events import (
    BACKEND_EXIT,
    BACKEND_RESTART_ATTEMPT,
    BACKEND_RESTART_EXHAUSTED,
    LauncherEvent,
    record_exit,
)
from launcher.services.process_service import ProcessService, BACKEND_DIR

logger = logging.getLogger("eve.launcher")

DEFAULT_MAX_RESTARTS = 3
BACKOFF_BASE_S = 2.0


class BackendService:
    def __init__(self, process_service: ProcessService, max_restarts: int = DEFAULT_MAX_RESTARTS):
        self._ps = process_service
        self._max_restarts = max_restarts
        self._restart_count = 0
        self._started_at: float = 0.0
        self._backend_pid: int = 0
        self._launcher_pid: int = os.getpid()
        self._on_event = None
        self._restart_history: list[dict] = []

    def set_event_handler(self, handler):
        self._on_event = handler

    def _emit(self, event: LauncherEvent):
        if self._on_event:
            self._on_event(event)

    @property
    def uptime(self) -> float:
        if self._started_at <= 0:
            return 0.0
        return time.time() - self._started_at

    @property
    def restart_count(self) -> int:
        return self._restart_count

    def _backoff_delay(self) -> float:
        return min(BACKOFF_BASE_S * (2 ** self._restart_count), 30.0)

    async def start(self) -> int:
        self._started_at = time.time()
        mp = await self._ps.start(
            "backend", sys.executable, "-m", "aios.main",
            cwd=str(BACKEND_DIR),
        )
        self._backend_pid = mp.pid
        logger.info(
            "launcher started backend (PID=%s, launcher=%s, cwd=%s)",
            mp.pid, self._launcher_pid, BACKEND_DIR,
        )
        return mp.pid

    async def stop(self, timeout: float = 10.0):
        exit_code = None
        if self._backend_pid:
            mp = self._ps.get("backend")
            if mp:
                exit_code = mp.returncode
        await self._ps.stop("backend", timeout=timeout)
        uptime = self.uptime
        record_exit(
            exit_code=exit_code,
            termination_type="graceful_stop",
            uptime=uptime,
            launcher_pid=self._launcher_pid,
            backend_pid=self._backend_pid,
            reason="shutdown_requested",
        )
        logger.info(
            "backend stopped (PID=%s, uptime=%.1fs)",
            self._backend_pid, uptime,
        )
        self._backend_pid = 0
        self._started_at = 0.0

    async def _handle_exit(self, mp):
        exit_code = mp.returncode
        uptime = self.uptime
        termination = "unknown"
        if exit_code is None:
            termination = "unknown_exit"
        elif exit_code == 0:
            termination = "clean_exit"
        elif exit_code < 0:
            termination = "signal"
        else:
            termination = f"exit_code_{exit_code}"

        logger.warning(
            "backend exited (PID=%s, code=%s, type=%s, uptime=%.1fs, restarts=%d/%d)",
            mp.pid, exit_code, termination, uptime,
            self._restart_count, self._max_restarts,
        )

        decision = "restart"
        if self._restart_count >= self._max_restarts:
            decision = "exhausted"
        elif exit_code == 0:
            decision = "no_restart"

        record_exit(
            exit_code=exit_code,
            termination_type=termination,
            uptime=uptime,
            launcher_pid=self._launcher_pid,
            backend_pid=mp.pid,
            restart_decision=decision,
            restart_count=self._restart_count,
            reason=f"process_exited(code={exit_code})",
        )

        self._emit(LauncherEvent(
            type=BACKEND_EXIT,
            data={
                "exit_code": exit_code,
                "termination_type": termination,
                "uptime": round(uptime, 1),
                "backend_pid": mp.pid,
                "restart_decision": decision,
                "restart_count": self._restart_count,
                "max_restarts": self._max_restarts,
            },
        ))

        return decision

    async def restart(self, timeout: float = 10.0) -> bool:
        self._restart_count += 1
        delay = self._backoff_delay()

        self._emit(LauncherEvent(
            type=BACKEND_RESTART_ATTEMPT,
            data={
                "attempt": self._restart_count,
                "max": self._max_restarts,
                "backoff_s": round(delay, 1),
            },
        ))

        if self._restart_count > self._max_restarts:
            logger.error(
                "backend restart exhausted (%d/%d attempts)",
                self._restart_count, self._max_restarts,
            )
            self._emit(LauncherEvent(
                type=BACKEND_RESTART_EXHAUSTED,
                data={
                    "attempts": self._restart_count,
                    "max": self._max_restarts,
                },
            ))
            return False

        logger.info(
            "backend restarting (attempt %d/%d, backoff %.1fs)",
            self._restart_count, self._max_restarts, delay,
        )

        import asyncio
        await asyncio.sleep(delay)

        await self.stop(timeout=timeout)
        self._started_at = 0.0
        try:
            await self.start()
            logger.info("backend restart succeeded (attempt %d/%d)", self._restart_count, self._max_restarts)
            return True
        except Exception as e:
            logger.error("backend restart failed (attempt %d/%d): %s", self._restart_count, self._max_restarts, e)
            return False

    def reset_restart_count(self):
        self._restart_count = 0

    async def is_alive(self) -> bool:
        return await self._ps.is_alive("backend")

    def get_pid(self) -> int | None:
        mp = self._ps.get("backend")
        return mp.pid if mp else None
