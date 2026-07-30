"""LauncherService — reusable orchestration engine.

This is the main API for all launcher operations.
It does NOT own the UI — no browser opening, no window management.
Future Tauri integration calls these methods directly.
"""

import asyncio
import logging
import time
from uuid import UUID, uuid4

from launcher import LAUNCHER_VERSION
from launcher.launcher_events import (
    LauncherEvent,
    LAUNCHER_STARTING,
    LAUNCHER_READY,
    LAUNCHER_STOPPING,
    LAUNCHER_STOPPED,
    LAUNCHER_ERROR,
    RESTART_REQUESTED,
    RESTART_COMPLETED,
    SHUTDOWN_REQUESTED,
    SHUTDOWN_COMPLETED,
    BACKEND_STARTED,
    EventHandler,
)
from launcher.launcher_api import LauncherStatus
from launcher.services.config_service import ConfigService
from launcher.services.logger_service import LoggerService
from launcher.services.process_service import ProcessService
from launcher.services.backend_service import BackendService
from launcher.services.frontend_service import BrowserFrontendService, FrontendProtocol
from launcher.services.health_service import HealthService
from launcher.services.provider_service import ProviderService
from launcher.services.tray_service import TrayService, TrayProtocol
from launcher.services.startup_service import StartupService
from launcher.services.shutdown_service import ShutdownService

logger = logging.getLogger("eve.launcher")


class LauncherService:
    def __init__(
        self,
        config_service: ConfigService | None = None,
        logger_service: LoggerService | None = None,
        process_service: ProcessService | None = None,
        backend_service: BackendService | None = None,
        frontend_service: FrontendProtocol | None = None,
        health_service: HealthService | None = None,
        provider_service: ProviderService | None = None,
        tray_service: TrayProtocol | None = None,
    ):
        self._config = config_service or ConfigService()
        self._logs = logger_service or LoggerService()
        self._ps = process_service or ProcessService()
        self._backend = backend_service or BackendService(self._ps)
        self._frontend = frontend_service or BrowserFrontendService(self._ps)
        self._health: HealthService | None = health_service
        self._providers: ProviderService | None = provider_service
        self._tray = tray_service or TrayService()
        self._startup: StartupService | None = None
        self._shutdown: ShutdownService | None = None
        self._subscribers: dict[UUID, EventHandler] = {}
        self._state = "stopped"
        self._started_at: float = 0.0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._api = None

    def _emit(self, event: LauncherEvent):
        logger.debug("event: %s", event.type)
        for handler in self._subscribers.values():
            try:
                handler(event)
            except Exception:
                logger.exception("event handler error for %s", event.type)

    def on_event(self, handler: EventHandler) -> UUID:
        sub_id = uuid4()
        self._subscribers[sub_id] = handler
        return sub_id

    def off_event(self, sub_id: UUID):
        self._subscribers.pop(sub_id, None)

    async def initialize(self) -> bool:
        self._state = "initializing"
        self._loop = asyncio.get_running_loop()
        self._logs.setup()
        logger.info("Eve OS Launcher v%s initializing", LAUNCHER_VERSION)
        self._config.save()
        self._emit(LauncherEvent(type=LAUNCHER_STARTING, data={"version": LAUNCHER_VERSION}))
        if self._config.is_first_run:
            logger.info("first-run pending — call run_first_run_wizard()")
        self._health = HealthService(
            backend_url=self._config.backend_url,
            health_url=self._config.health_url,
            on_change=self._on_health_change,
            on_event=self._on_health_event,
        )
        self._providers = ProviderService(self._health, self._config)
        self._startup = StartupService(
            backend=self._backend,
            frontend=self._frontend,
            health=self._health,
            providers=self._providers,
            config=self._config,
        )
        self._shutdown = ShutdownService(
            backend=self._backend,
            frontend=self._frontend,
            health=self._health,
        )
        self._state = "initialized"
        return True

    def _on_health_change(self, statuses: dict):
        for name, status in statuses.items():
            if status == "down":
                logger.warning("service down: %s", name)
                asyncio.run_coroutine_threadsafe(
                    self._attempt_restart(name), self._loop,
                )

    def _on_health_event(self, event: LauncherEvent):
        self._emit(event)

    async def _attempt_restart(self, name: str):
        max_retries = 3
        if name == "backend":
            sh = self._health.services.get("backend")
            if sh and sh.restart_count >= max_retries:
                logger.error("max restarts reached for backend")
                return
            logger.info("restarting backend...")
            await self._backend.restart()
            if sh:
                sh.restart_count += 1
            self._emit(LauncherEvent(type=BACKEND_STARTED, data={"restart": True}))

    async def start(self) -> bool:
        if self._state not in ("initialized", "stopped"):
            logger.warning("cannot start in state: %s", self._state)
            return False
        if self._startup is None:
            logger.warning("cannot start — not initialized")
            return False
        self._state = "starting"
        self._started_at = time.time()

        ok = await self._startup.run()
        if ok:
            self._state = "running"
            self._started_at = time.time()
            self._health.start_monitoring()
            self._emit(LauncherEvent(type=LAUNCHER_READY, data={
                "backend_url": self._config.backend_url,
                "version": LAUNCHER_VERSION,
            }))
        else:
            self._state = "error"
            self._emit(LauncherEvent(type=LAUNCHER_ERROR, data={"message": "startup failed"}))
        return ok

    async def stop(self):
        if self._state == "stopped":
            return
        self._state = "stopping"
        self._emit(LauncherEvent(type=LAUNCHER_STOPPING))
        if self._shutdown:
            await self._shutdown.shutdown()
        self._state = "stopped"
        self._emit(LauncherEvent(type=LAUNCHER_STOPPED))

    async def restart(self) -> bool:
        self._emit(LauncherEvent(type=RESTART_REQUESTED))
        await self.stop()
        ok = await self.start()
        if ok:
            self._emit(LauncherEvent(type=RESTART_COMPLETED))
        return ok

    async def shutdown(self):
        self._emit(LauncherEvent(type=SHUTDOWN_REQUESTED))
        self._tray.stop()
        await self.stop()
        self._emit(LauncherEvent(type=SHUTDOWN_COMPLETED))

    def status(self) -> LauncherStatus:
        uptime = time.time() - self._started_at if self._started_at > 0 else 0.0
        services = {}
        if self._health:
            services = {n: s.status for n, s in self._health.services.items()}
        providers = {}
        if self._health:
            providers = {
                n: {"connected": p.connected, "error": p.error}
                for n, p in self._health.providers.items()
            }
        return LauncherStatus(
            state=self._state,
            version=LAUNCHER_VERSION,
            started_at=self._started_at,
            backend_url=self._config.backend_url,
            frontend_url=self._config.frontend_url,
            frontend_type=self._config.frontend_type,
            services=services,
            providers=providers,
            uptime=uptime,
        )

    async def health(self) -> dict:
        if self._health:
            return await self._health.check_all()
        return {}

    def launch_frontend(self):
        if self._state != "running":
            logger.warning("cannot launch frontend when not running")
            return
        import webbrowser
        webbrowser.open(self._config.frontend_url)

    def open_devtools(self):
        import webbrowser
        webbrowser.open(f"{self._config.backend_url}/docs")

    def open_health_dashboard(self):
        import webbrowser
        webbrowser.open(f"{self._config.backend_url}/api/v1/system/health")

    def open_settings(self):
        import webbrowser
        webbrowser.open(f"{self._config.frontend_url}/settings")

    @property
    def config(self) -> ConfigService:
        return self._config

    @property
    def logs(self) -> LoggerService:
        return self._logs

    @property
    def backend(self) -> BackendService:
        return self._backend

    @property
    def frontend(self) -> FrontendProtocol:
        return self._frontend

    @property
    def health_service(self) -> HealthService | None:
        return self._health

    @property
    def tray(self) -> TrayProtocol:
        return self._tray

    @property
    def running(self) -> bool:
        return self._state == "running"

    @property
    def state(self) -> str:
        return self._state
