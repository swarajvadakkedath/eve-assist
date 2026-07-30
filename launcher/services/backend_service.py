"""Backend service — backend process lifecycle."""

import logging
import sys

from launcher.services.process_service import ProcessService, BACKEND_DIR

logger = logging.getLogger("eve.launcher")


class BackendService:
    def __init__(self, process_service: ProcessService):
        self._ps = process_service

    async def start(self) -> int:
        mp = await self._ps.start(
            "backend", sys.executable, "-m", "aios.main",
            cwd=str(BACKEND_DIR),
        )
        logger.info("backend started (PID %s)", mp.pid)
        return mp.pid

    async def stop(self, timeout: float = 10.0):
        await self._ps.stop("backend", timeout=timeout)
        logger.info("backend stopped")

    async def restart(self, timeout: float = 10.0):
        await self.stop(timeout=timeout)
        return await self.start()

    async def is_alive(self) -> bool:
        return await self._ps.is_alive("backend")

    def get_pid(self) -> int | None:
        mp = self._ps.get("backend")
        return mp.pid if mp else None
