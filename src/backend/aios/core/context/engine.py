"""Context Engine — event-driven observer for workspace, app, and file context."""

import asyncio
from datetime import datetime, timezone

from aios.core.di_container import DIContainer
from aios.core.event_bus import EventBus
from aios.core.windows.adapter import WindowsAdapter
from aios.core.context.models import Context, ProjectInfo, ActivityType
from aios.core.context.project_detector import (
    detect_project_from_file,
    infer_project_type_from_file,
)
from aios.core.context.activity_detector import detect_activity, extract_active_file
from aios.models.memory import NodeInput


CONTEXT_ENGINE_SOURCE = "context_engine"
MEMORY_NODE_TYPE = "observation"
_KNOWN_IDE_APPS = frozenset({
    "code", "vscode", "visual studio code",
    "idea", "intellij", "intellij idea",
    "pycharm", "pycharm64",
    "webstorm", "webstorm64",
    "goland", "goland64",
    "rider", "rider64",
    "clion", "clion64",
    "phpstorm", "phpstorm64",
    "rubymine", "rubymine64",
    "datagrip", "datagrip64",
    "android studio",
    "sublime text", "sublime_text",
    "atom", "notepad++", "notepad++(64-bit)",
    "vim", "nvim", "neovim",
    "emacs",
    "eclipse",
    "xcode",
    "zed",
    "cursor",
    "windsurf",
})


class ContextEngine:
    def __init__(
        self,
        windows_adapter: WindowsAdapter | None = None,
        event_bus: EventBus | None = None,
        poll_interval: float = 2.0,
        memory_store: any = None,
    ):
        self._windows = windows_adapter
        self._event_bus = event_bus
        self._poll_interval = poll_interval
        self._memory_store = memory_store
        self._current: Context | None = None
        self._history: list[Context] = []
        self._max_history: int = 1000
        self._running = False
        self._poll_task: asyncio.Task | None = None
        self._idle_threshold: float = 60.0
        self._last_activity_time: float = 0.0
        self._last_external_project: ProjectInfo | None = None
        self._last_external_app: str = ""
        self._cache_timestamp: float = 0.0
        self._CACHE_MAX_AGE: float = 300.0  # 5 minutes

    # ------------------------------------------------------------------
    # DI Registration
    # ------------------------------------------------------------------

    @staticmethod
    def register_in_container(
        container: DIContainer,
        windows_adapter: WindowsAdapter | None = None,
        event_bus: EventBus | None = None,
        poll_interval: float = 2.0,
        memory_store: any = None,
    ) -> DIContainer:
        def factory() -> ContextEngine:
            return ContextEngine(
                windows_adapter=windows_adapter,
                event_bus=event_bus,
                poll_interval=poll_interval,
                memory_store=memory_store,
            )
        container.register(ContextEngine, factory=factory)
        return container

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_current_context(self) -> Context | None:
        return self._current

    async def get_active_app(self) -> str:
        if self._current and self._current.active_app:
            return self._current.active_app
        return ""

    async def get_active_file(self) -> str | None:
        if self._current:
            return self._current.active_file
        return None

    async def detect_project(self) -> ProjectInfo | None:
        if self._current and self._current.project:
            return self._current.project
        if self._last_external_project:
            import time
            age = time.monotonic() - self._cache_timestamp
            if age > self._CACHE_MAX_AGE:
                self._last_external_project = None
                self._last_external_app = ""
                return None
            if self._last_external_project.path:
                from pathlib import Path
                if not Path(self._last_external_project.path).exists():
                    self._last_external_project = None
                    self._last_external_app = ""
                    return None
            return self._last_external_project
        return None

    async def get_recent_activity(self, minutes: int = 5) -> list[Context]:
        cutoff = datetime.now(timezone.utc).timestamp() - (minutes * 60)
        return [c for c in self._history if c.timestamp > cutoff]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self):
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        if self._event_bus:
            await self._event_bus.publish(
                "context:engine_started",
                {"poll_interval": self._poll_interval},
                source=CONTEXT_ENGINE_SOURCE,
            )

    async def stop(self):
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        self._last_external_project = None
        self._last_external_app = ""
        self._cache_timestamp = 0.0
        if self._event_bus:
            await self._event_bus.publish(
                "context:engine_stopped",
                {},
                source=CONTEXT_ENGINE_SOURCE,
            )

    async def poll_now(self) -> Context:
        ctx = await self._poll()
        if ctx:
            await self._handle_update(ctx)
        return ctx or Context()

    # ------------------------------------------------------------------
    # Polling Loop
    # ------------------------------------------------------------------

    async def _poll_loop(self):
        while self._running:
            try:
                ctx = await self._poll()
                if ctx:
                    await self._handle_update(ctx)
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                if self._event_bus:
                    await self._event_bus.publish(
                        "context:poll_error",
                        {},
                        source=CONTEXT_ENGINE_SOURCE,
                    )
                await asyncio.sleep(self._poll_interval)

    async def _poll(self) -> Context | None:
        if self._windows is None:
            return None
        window = await self._windows.get_active_window()
        app = window.app if window else ""
        window_title = window.title if window else ""
        active_file = extract_active_file(app, window_title)
        project = detect_project_from_file(active_file)
        if project is None and active_file:
            inferred_type = infer_project_type_from_file(active_file)
            if inferred_type:
                project = ProjectInfo(path="", type=inferred_type, markers=[])
        is_eve_active = app.lower() in ("eve", "eve ai", "") or not app
        is_ide_active = app.lower().replace(" ", "") in _KNOWN_IDE_APPS or any(
            ide in app.lower() for ide in _KNOWN_IDE_APPS
        )
        if project and not is_eve_active:
            self._last_external_project = project
            self._last_external_app = app
            import time
            self._cache_timestamp = time.monotonic()
        elif is_eve_active and self._last_external_project:
            project = self._last_external_project
        elif not is_eve_active and not is_ide_active and not project:
            self._last_external_project = None
            self._last_external_app = ""
        activity = detect_activity(app, window_title)
        now = datetime.now(timezone.utc).timestamp()
        if activity == ActivityType.IDLE:
            if self._current and self._current.activity != ActivityType.IDLE:
                idle_duration = now - self._last_activity_time
                if idle_duration < self._idle_threshold:
                    activity = self._current.activity
        else:
            self._last_activity_time = now
        return Context(
            active_app=app,
            active_window=window_title,
            active_file=active_file,
            project=project,
            activity=activity,
            timestamp=now,
        )

    async def _handle_update(self, ctx: Context):
        changes = ctx.changed_since(self._current)
        if not changes:
            return
        prev = self._current
        self._current = ctx
        self._history.append(ctx)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        await self._publish_events(ctx, prev, changes)

    async def _publish_events(self, ctx: Context, prev: Context | None, changes: list[str]):
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            "context:changed",
            ctx.to_dict(),
            source=CONTEXT_ENGINE_SOURCE,
        )
        if "project" in changes and ctx.project:
            await self._event_bus.publish(
                "context:project_changed",
                {"path": ctx.project.path, "type": ctx.project.type, "markers": ctx.project.markers},
                source=CONTEXT_ENGINE_SOURCE,
            )
        if "active_file" in changes and ctx.active_file:
            await self._event_bus.publish(
                "context:file_changed",
                {"path": ctx.active_file, "app": ctx.active_app or ""},
                source=CONTEXT_ENGINE_SOURCE,
            )
        if "activity" in changes:
            await self._event_bus.publish(
                "context:activity_changed",
                {"activity": ctx.activity.value, "previous": (prev.activity.value if prev else "unknown")},
                source=CONTEXT_ENGINE_SOURCE,
            )
        if "active_app" in changes:
            await self._event_bus.publish(
                "context:application_changed",
                {"app": ctx.active_app or "", "window": ctx.active_window or ""},
                source=CONTEXT_ENGINE_SOURCE,
            )
        if self._memory_store and ctx.activity != ActivityType.IDLE:
            await self._store_context_observation(ctx, changes)

    async def _store_context_observation(self, ctx: Context, changes: list[str]):
        try:
            node_input = NodeInput(
                type=MEMORY_NODE_TYPE,
                subtype="context",
                title=f"Context: {ctx.active_app or 'unknown'} — {ctx.activity.value}",
                summary=f"App: {ctx.active_app} | Window: {ctx.active_window} | File: {ctx.active_file} | Activity: {ctx.activity.value} | Project: {ctx.project.path if ctx.project else 'none'}",
                source=CONTEXT_ENGINE_SOURCE,
                importance=0.3,
                tags=[ctx.activity.value, *(ctx.active_app.lower().replace(" ", "_").split(",") if ctx.active_app else [])],
                metadata={
                    "changes": changes,
                    "active_app": ctx.active_app,
                    "active_window": ctx.active_window,
                    "active_file": ctx.active_file,
                    "activity": ctx.activity.value,
                    "project_path": ctx.project.path if ctx.project else None,
                    "project_type": ctx.project.type if ctx.project else None,
                },
            )
            await self._memory_store.create_node(node_input)
        except Exception:
            pass
