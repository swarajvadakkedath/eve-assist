"""Shutdown service — graceful teardown of all services."""

import logging

from launcher.services.backend_service import BackendService
from launcher.services.frontend_service import FrontendProtocol
from launcher.services.health_service import HealthService

logger = logging.getLogger("eve.launcher")


class ShutdownService:
    def __init__(
        self,
        backend: BackendService,
        frontend: FrontendProtocol,
        health: HealthService,
    ):
        self._backend = backend
        self._frontend = frontend
        self._health = health

    async def shutdown(self, timeout: float = 10.0):
        logger.info("shutdown sequence started")
        await self._health.stop_monitoring()
        logger.info("health monitoring stopped")
        await self._frontend.stop(timeout=timeout)
        logger.info("frontend stopped")
        await self._backend.stop(timeout=timeout)
        logger.info("backend stopped")
        logger.info("shutdown sequence complete")
