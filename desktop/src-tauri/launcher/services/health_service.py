"""Health service — monitor backend, frontend, and internal services."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

import httpx

from launcher.launcher_events import (
    LauncherEvent,
    BACKEND_FAILED,
    BACKEND_DEGRADED,
    SERVICE_HEALTH_CHANGED,
)


@dataclass
class ServiceHealth:
    name: str
    status: str = "unknown"
    details: dict = field(default_factory=dict)
    last_seen: float = 0.0
    restart_count: int = 0


@dataclass
class ProviderStatus:
    name: str
    connected: bool = False
    error: str = ""


class HealthService:
    def __init__(
        self,
        backend_url: str,
        health_url: str,
        on_change: Callable | None = None,
        on_event: Callable | None = None,
        interval: float = 5.0,
    ):
        self._backend_url = backend_url
        self._health_url = health_url
        self._on_change = on_change
        self._on_event = on_event
        self._interval = interval
        self._running = False
        self._task: asyncio.Task | None = None
        self.services: dict[str, ServiceHealth] = {}
        self.providers: dict[str, ProviderStatus] = {}
        self._init_services()

    def _init_services(self):
        for name in [
            "backend", "frontend", "memory", "planner",
            "windows_adapter", "context_engine", "voice", "vision",
            "plugin_system", "developer_tools",
        ]:
            self.services[name] = ServiceHealth(name=name)
        for name in ["gemini", "groq", "openrouter", "ollama", "github_models", "z_ai"]:
            self.providers[name] = ProviderStatus(name=name)

    def _emit(self, event_type: str, data: dict):
        if self._on_event:
            self._on_event(LauncherEvent(type=event_type, data=data))

    async def check_backend(self) -> ServiceHealth:
        sh = self.services["backend"]
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self._health_url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                modules = data.get("modules", {})
                previous = sh.status
                sh.status = "healthy"
                sh.details = modules
                sh.last_seen = time.time()
                if previous in ("down", "degraded", "unknown"):
                    self._emit(SERVICE_HEALTH_CHANGED, {"service": "backend", "status": "healthy", "modules": modules})
            else:
                sh.status = "degraded"
                self._emit(BACKEND_DEGRADED, {"status_code": resp.status_code})
        except Exception as e:
            sh.status = "down"
            self._emit(BACKEND_FAILED, {"error": str(e)})
        return sh

    async def check_frontend(self) -> ServiceHealth:
        sh = self.services["frontend"]
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self._backend_url.replace(str(self._backend_url.split(":")[-1]), "5173"),
                    timeout=3, follow_redirects=True,
                )
            sh.status = "healthy" if resp.status_code < 500 else "degraded"
            sh.last_seen = time.time() if sh.status == "healthy" else sh.last_seen
        except Exception:
            sh.status = "down"
        return sh

    async def check_ai_provider(self, name: str, key: str = "", url: str = "") -> ProviderStatus:
        ps = self.providers[name]
        checks = {
            "gemini": ("https://generativelanguage.googleapis.com/v1beta/models" if key else None),
            "groq": ("https://api.groq.com/openai/v1/models" if key else None),
            "openrouter": ("https://openrouter.ai/api/v1/models" if key else None),
            "ollama": (f"{url or 'http://127.0.0.1:11434'}/api/tags"),
            "github_models": ("https://models.inference.ai.azure.com" if key else None),
            "z_ai": (f"https://{name}.ai" if key else None),
        }
        endpoint = checks.get(name)
        if endpoint is None:
            previous = ps.connected
            ps.connected = False
            ps.error = "Missing API Key" if key == "" else "Unavailable"
            if previous:
                self._emit("provider:disconnected", {"provider": name, "error": ps.error})
            return ps
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(endpoint, timeout=5, headers={
                    "Authorization": f"Bearer {key}",
                } if key else {})
            previous = ps.connected
            ps.connected = resp.status_code < 500
            ps.error = "" if ps.connected else f"HTTP {resp.status_code}"
            if ps.connected and not previous:
                self._emit("provider:connected", {"provider": name})
            elif not ps.connected and previous:
                self._emit("provider:disconnected", {"provider": name, "error": ps.error})
        except httpx.ConnectError:
            ps.connected = False
            ps.error = "Offline"
        except Exception as e:
            ps.connected = False
            ps.error = str(e)
        return ps

    async def check_all_ai_providers(self, api_keys: dict, ollama_url: str = ""):
        for name in self.providers:
            cfg = api_keys.get(name, {})
            key = cfg.get("key", "") if isinstance(cfg, dict) else ""
            url = cfg.get("url", ollama_url) if isinstance(cfg, dict) else ollama_url
            await self.check_ai_provider(name, key, url)

    async def check_all(self) -> dict:
        await self.check_backend()
        await self.check_frontend()
        return {name: s.status for name, s in self.services.items()}

    def get_backend_modules(self) -> dict:
        return self.services.get("backend", ServiceHealth("backend")).details

    def needs_restart(self, name: str) -> bool:
        sh = self.services.get(name)
        return sh is not None and sh.status == "down"

    async def _loop(self):
        while self._running:
            before = {n: s.status for n, s in self.services.items()}
            await self.check_all()
            after = {n: s.status for n, s in self.services.items()}
            if before != after and self._on_change:
                self._on_change(after)
            await asyncio.sleep(self._interval)

    def start_monitoring(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())

    _check_backend = check_backend
    _check_frontend = check_frontend
    _check_ai_provider = check_ai_provider

    async def stop_monitoring(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
