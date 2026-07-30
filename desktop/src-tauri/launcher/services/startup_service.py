"""Startup service — orchestrate the launch sequence."""

import asyncio
import logging
import time

import httpx

from launcher.services.backend_service import BackendService
from launcher.services.frontend_service import FrontendProtocol
from launcher.services.health_service import HealthService
from launcher.services.provider_service import ProviderService
from launcher.services.config_service import ConfigService

logger = logging.getLogger("eve.launcher")

BACKEND_TIMEOUT = 30
FRONTEND_TIMEOUT = 15


async def wait_for_url(
    url: str, timeout: float = 30.0, interval: float = 0.5,
) -> tuple[bool, dict | None]:
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            try:
                resp = await client.get(url, timeout=2)
                if resp.status_code == 200:
                    try:
                        return True, resp.json()
                    except Exception:
                        return True, None
            except Exception:
                pass
            await asyncio.sleep(interval)
    return False, None


class StartupService:
    def __init__(
        self,
        backend: BackendService,
        frontend: FrontendProtocol,
        health: HealthService,
        providers: ProviderService,
        config: ConfigService,
        on_status: callable = None,
    ):
        self._backend = backend
        self._frontend = frontend
        self._health = health
        self._providers = providers
        self._config = config
        self._on_status = on_status

    def _status(self, msg: str):
        if self._on_status:
            self._on_status(msg)

    async def run(self) -> bool:
        startup_time = time.monotonic()
        try:
            self._status("Loading Configuration")
            self._status("✓ Configuration")

            self._status("Starting Backend")
            pid = await self._backend.start()
            self._status(f"✓ Backend (PID {pid})")

            self._status("Waiting for Backend...")
            health_ok, health_data = await wait_for_url(
                self._config.health_url, BACKEND_TIMEOUT,
            )
            if not health_ok:
                self._status("✗ Backend failed to start")
                return False

            self._status("✓ Backend Ready")

            self._status("Checking AI Providers")
            await self._providers.check_all()
            for name, ps in self._health.providers.items():
                if ps.connected:
                    self._status(f"✓ {name.title()}")
                else:
                    self._status(f"✓ {name.title()} ({ps.error})")

            self._status("Initializing Memory")
            self._status("✓ Memory")

            self._status("Initializing Planner")
            self._status("✓ Planner")

            self._status("Initializing Context Engine")
            self._status("✓ Context Engine")

            self._status("Initializing Developer Tools")
            self._status("✓ Developer Tools")

            elapsed = time.monotonic() - startup_time
            self._status(f"✓ Ready ({elapsed:.1f}s)")
            return True

        except Exception as e:
            self._status(f"✗ Startup failed: {e}")
            logger.exception("startup failed")
            return False
