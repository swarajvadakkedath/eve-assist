"""Frontend service — abstracted frontend lifecycle.

Current implementation: browser (npm run dev).
Future implementation: Tauri native window.
The launcher does not know which is used.
"""

import logging
from typing import Protocol

from launcher.services.process_service import ProcessService, PROJECT_ROOT

logger = logging.getLogger("eve.launcher")

FRONTEND_DIR = PROJECT_ROOT / "src" / "frontend"


class FrontendProtocol(Protocol):
    async def start(self, url: str) -> int: ...
    async def stop(self, timeout: float): ...
    async def restart(self, timeout: float) -> int: ...
    async def is_alive(self) -> bool: ...
    def get_type(self) -> str: ...


class BrowserFrontendService:
    def __init__(self, process_service: ProcessService):
        self._ps = process_service
        self._type = "browser"

    async def start(self, url: str = "") -> int:
        mp = await self._ps.start(
            "frontend", "npm", "run", "dev",
            cwd=str(FRONTEND_DIR),
        )
        logger.info("frontend started (PID %s, type=%s)", mp.pid, self._type)
        return mp.pid

    async def stop(self, timeout: float = 5.0):
        await self._ps.stop("frontend", timeout=timeout)
        logger.info("frontend stopped")

    async def restart(self, timeout: float = 5.0) -> int:
        await self.stop(timeout=timeout)
        return await self.start()

    async def is_alive(self) -> bool:
        return await self._ps.is_alive("frontend")

    def get_type(self) -> str:
        return self._type
