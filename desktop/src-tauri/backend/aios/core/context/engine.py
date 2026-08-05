"""Context Engine — the kernel of the AI Operating System.

Owns:
  - Provider registration and lifecycle
  - Context aggregation from all providers
  - Context validation
  - Incremental updates (only changed sections refresh)
  - Context versioning (every snapshot has version + changed_providers)
  - Intelligent caching (invalidate only changed sections)
  - Subscriptions (consumers get notified of context changes)
  - Serialization (to_dict, compute_hash)
  - Event integration (subscribes to all provider-relevant events)

Does NOT depend on Hermes. Does NOT directly access Windows/OS services.
All OS access is delegated to Context Providers.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from aios.core.context.models import (
    ExecutionContext,
    ContextProvider,
    ContextScope,
    ProjectInfo,
    ActivityType,
    WindowContext,
    WorkspaceContext,
    GitContext,
    BrowserContext,
    DesktopContext,
    VoiceContext,
    MemoryContext,
    ProviderHealthContext,
    ClipboardContext,
    CalendarContext,
    SelectionContext,
    ApplicationContext,
    ToolContext,
    NotificationContext,
)
from aios.core.context.project_detector import (
    detect_project_from_file,
    infer_project_type_from_file,
)
from aios.core.context.activity_detector import detect_activity, extract_active_file
from aios.utils.logger import get_logger

logger = get_logger(__name__)

CONTEXT_ENGINE_SOURCE = "context_engine"


class ContextEngine:
    """The unified context kernel.

    Every EVE subsystem and Hermes receives context through this engine.
    The engine never directly accesses OS services — all access is
    delegated to registered ContextProviders.
    """

    def __init__(
        self,
        windows_adapter=None,
        event_bus=None,
        poll_interval: float = 2.0,
        memory_store=None,
    ):
        # Core dependencies (backward-compatible with old ContextEngine)
        self._windows = windows_adapter
        self._event_bus = event_bus
        self._poll_interval = poll_interval
        self._memory_store = memory_store

        # Provider registry
        self._providers: dict[str, ContextProvider] = {}
        self._provider_order: list[str] = []

        # Context state
        self._current: ExecutionContext | None = None
        self._version: int = 0
        self._history: list[ExecutionContext] = []
        self._max_history: int = 100

        # Lifecycle
        self._running = False
        self._poll_task: asyncio.Task | None = None

        # Cache
        self._section_cache: dict[str, dict] = {}
        self._section_cache_time: dict[str, float] = {}
        self._cache_ttl: float = 30.0

        # Subscriptions
        self._subscribers: list[Callable] = []
        self._event_subscriptions: list[str] = []

        # Backward-compatible: legacy Context fields
        self._legacy_context = None
        self._idle_threshold: float = 60.0
        self._last_activity_time: float = 0.0
        self._last_external_project: ProjectInfo | None = None
        self._last_external_app: str = ""
        self._cache_timestamp: float = 0.0
        self._CACHE_MAX_AGE: float = 300.0

    # ------------------------------------------------------------------
    # DI Registration
    # ------------------------------------------------------------------

    @staticmethod
    def register_in_container(
        container,
        windows_adapter=None,
        event_bus=None,
        poll_interval: float = 2.0,
        memory_store=None,
    ):
        from aios.core.di_container import DIContainer

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
    # Provider Management
    # ------------------------------------------------------------------

    def register_provider(self, provider: ContextProvider) -> None:
        """Register a context provider."""
        pid = provider.provider_id
        self._providers[pid] = provider
        if pid not in self._provider_order:
            self._provider_order.append(pid)
        logger.info("context.provider_registered", provider=pid)

    def unregister_provider(self, provider_id: str) -> None:
        self._providers.pop(provider_id, None)
        self._provider_order = [p for p in self._provider_order if p != provider_id]

    def get_provider(self, provider_id: str) -> ContextProvider | None:
        return self._providers.get(provider_id)

    def list_providers(self) -> list[dict]:
        return [
            {
                "id": p.provider_id,
                "name": p.display_name,
                "scope": p.scope.value,
                "status": "active",
            }
            for p in self._providers.values()
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        # Start all providers
        for provider in self._providers.values():
            try:
                await provider.start()
            except Exception as exc:
                logger.warning("context.provider_start_failed", provider=provider.provider_id, error=str(exc))

        # Subscribe to relevant events
        await self._subscribe_events()

        # Start poll loop
        self._poll_task = asyncio.create_task(self._poll_loop())

        if self._event_bus:
            await self._event_bus.publish(
                "context:engine_started",
                {"providers": len(self._providers), "poll_interval": self._poll_interval},
                source=CONTEXT_ENGINE_SOURCE,
            )
        logger.info("context.engine_started", providers=len(self._providers))

    async def stop(self) -> None:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        # Stop all providers
        for provider in self._providers.values():
            try:
                await provider.stop()
            except Exception:
                pass

        # Unsubscribe events
        for sub_id in self._event_subscriptions:
            if self._event_bus:
                try:
                    self._event_bus.unsubscribe(sub_id)
                except Exception:
                    pass
        self._event_subscriptions.clear()

        if self._event_bus:
            await self._event_bus.publish(
                "context:engine_stopped",
                {},
                source=CONTEXT_ENGINE_SOURCE,
            )

    # ------------------------------------------------------------------
    # Context Collection
    # ------------------------------------------------------------------

    async def collect(self) -> ExecutionContext:
        """Collect context from all providers and build ExecutionContext."""
        start = time.monotonic()
        sections: dict[str, Any] = {}

        # Collect from all providers concurrently
        tasks = {}
        for pid, provider in self._providers.items():
            tasks[pid] = asyncio.create_task(self._safe_collect(provider))

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for pid, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.warning("context.collect_failed", provider=pid, error=str(result))
                continue
            if isinstance(result, dict):
                sections.update(result)

        # Build ExecutionContext from collected sections
        ctx = ExecutionContext(
            context_id=uuid4().hex,
            version=self._version + 1,
            session_id=self._current.session_id if self._current else "",
            timestamp=datetime.now(timezone.utc).timestamp(),
            window=self._build_window(sections),
            clipboard=self._build_clipboard(sections),
            workspace=self._build_workspace(sections),
            git=self._build_git(sections),
            browser=self._build_browser(sections),
            desktop=self._build_desktop(sections),
            voice=self._build_voice(sections),
            memory=self._build_memory(sections),
            provider_health=self._build_provider_health(sections),
            calendar=self._build_calendar(sections),
            selection=self._build_selection(sections),
            application=self._build_application(sections),
            tools=self._build_tools(sections),
            notifications=self._build_notifications(sections),
            changed_providers=list(tasks.keys()),
        )

        # Detect changes
        changes = ctx.diff(self._current)
        ctx.changed_providers = changes

        # Update state
        self._version = ctx.version
        prev = self._current
        self._current = ctx

        # Cache sections
        for section in changes:
            section_data = sections.get(section)
            if section_data is not None:
                self._section_cache[section] = section_data
                self._section_cache_time[section] = time.monotonic()

        # Record history
        self._history.append(ctx)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        latency = (time.monotonic() - start) * 1000

        # Publish events
        if changes:
            await self._publish_change_events(ctx, prev, changes)

        # Notify subscribers
        await self._notify_subscribers(ctx, changes)

        # Store observation in memory
        if self._memory_store and ctx.window.activity != ActivityType.IDLE:
            await self._store_observation(ctx, changes)

        return ctx

    async def _safe_collect(self, provider: ContextProvider) -> dict:
        try:
            return await provider.collect()
        except Exception as exc:
            logger.warning("context.provider_collect_error", provider=provider.provider_id, error=str(exc))
            return {}

    # ------------------------------------------------------------------
    # Context Access (backward-compatible)
    # ------------------------------------------------------------------

    async def get_current_context(self) -> ExecutionContext | None:
        return self._current

    async def snapshot(self) -> ExecutionContext:
        """Return current context or collect fresh if none exists."""
        if self._current:
            return self._current
        return await self.collect()

    async def diff(self, other: ExecutionContext | None = None) -> list[str]:
        """Return changed sections between current and another context."""
        if self._current is None:
            return []
        return self._current.diff(other)

    def get_version(self) -> int:
        return self._version

    # Backward-compatible API
    async def get_active_app(self) -> str:
        if self._current and self._current.window.active_app:
            return self._current.window.active_app
        return ""

    async def get_active_file(self) -> str | None:
        if self._current:
            return self._current.window.active_file
        return None

    async def detect_project(self) -> ProjectInfo | None:
        if self._current and self._current.workspace.current_project:
            return self._current.workspace.current_project
        if self._last_external_project:
            age = time.monotonic() - self._cache_timestamp
            if age > self._CACHE_MAX_AGE:
                self._last_external_project = None
                return None
            return self._last_external_project
        return None

    async def get_recent_activity(self, minutes: int = 5) -> list[ExecutionContext]:
        cutoff = datetime.now(timezone.utc).timestamp() - (minutes * 60)
        return [c for c in self._history if c.timestamp > cutoff]

    # ------------------------------------------------------------------
    # Incremental Updates
    # ------------------------------------------------------------------

    async def refresh_section(self, section: str) -> None:
        """Refresh a specific context section from its provider."""
        for pid, provider in self._providers.items():
            try:
                data = await provider.collect()
                if section in data:
                    self._section_cache[section] = data[section]
                    self._section_cache_time[section] = time.monotonic()
                    # Trigger a full re-collect to update ExecutionContext
                    await self.collect()
                    return
            except Exception:
                continue

    def get_section_cache(self, section: str) -> dict | None:
        """Get cached section data if still valid."""
        cached = self._section_cache.get(section)
        if cached is None:
            return None
        age = time.monotonic() - self._section_cache_time.get(section, 0)
        if age > self._cache_ttl:
            return None
        return cached

    def invalidate_cache(self, section: str | None = None) -> None:
        """Invalidate cache for a section or all sections."""
        if section:
            self._section_cache.pop(section, None)
            self._section_cache_time.pop(section, None)
        else:
            self._section_cache.clear()
            self._section_cache_time.clear()

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable) -> str:
        """Subscribe to context changes. Returns subscription id."""
        sub_id = uuid4().hex
        self._subscribers.append(callback)
        return sub_id

    def unsubscribe(self, callback: Callable) -> None:
        self._subscribers = [s for s in self._subscribers if s is not callback]

    async def _notify_subscribers(self, ctx: ExecutionContext, changes: list[str]) -> None:
        for callback in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(ctx, changes)
                else:
                    callback(ctx, changes)
            except Exception as exc:
                logger.warning("context.subscriber_error", error=str(exc))

    # ------------------------------------------------------------------
    # Event Integration
    # ------------------------------------------------------------------

    async def _subscribe_events(self) -> None:
        """Subscribe to relevant EventBus events."""
        if self._event_bus is None:
            return
        event_types = [
            "voice:*",
            "desktop:*",
            "memory:*",
            "tool:*",
            "provider:*",
            "workspace:*",
        ]
        for event_type in event_types:
            try:
                sub_id = self._event_bus.subscribe(event_type, self._on_event)
                self._event_subscriptions.append(sub_id)
            except Exception:
                pass

    async def _on_event(self, event) -> None:
        """Handle incoming events and propagate to relevant providers."""
        event_type = event.type if hasattr(event, "type") else ""
        payload = event.payload if hasattr(event, "payload") else {}
        for provider in self._providers.values():
            try:
                await provider.on_event(event_type, payload)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Context Building Helpers
    # ------------------------------------------------------------------

    def _build_window(self, sections: dict) -> WindowContext:
        data = sections.get("window", {})
        if isinstance(data, WindowContext):
            return data
        if isinstance(data, dict):
            return WindowContext(
                active_app=data.get("active_app", ""),
                active_window=data.get("active_window", ""),
                active_file=data.get("active_file"),
                open_applications=data.get("open_applications", []),
                activity=ActivityType(data.get("activity", "idle")),
            )
        return WindowContext()

    def _build_clipboard(self, sections: dict) -> ClipboardContext:
        data = sections.get("clipboard", {})
        if isinstance(data, dict):
            return ClipboardContext(
                text=data.get("text", ""),
                has_content=data.get("has_content", False),
                content_type=data.get("content_type", "text"),
                timestamp=data.get("timestamp", 0),
            )
        return ClipboardContext()

    def _build_workspace(self, sections: dict) -> WorkspaceContext:
        data = sections.get("workspace", {})
        if isinstance(data, dict):
            project = None
            if data.get("current_project"):
                p = data["current_project"]
                project = ProjectInfo(
                    path=p.get("path", ""),
                    type=p.get("type", ""),
                    markers=p.get("markers", []),
                )
            return WorkspaceContext(
                current_project=project,
                recent_files=data.get("recent_files", []),
                open_files=data.get("open_files", []),
                workspace_path=data.get("workspace_path", ""),
            )
        return WorkspaceContext()

    def _build_git(self, sections: dict) -> GitContext:
        data = sections.get("git", {})
        if isinstance(data, dict):
            return GitContext(
                repository_path=data.get("repository_path", ""),
                current_branch=data.get("current_branch", ""),
                is_dirty=data.get("is_dirty", False),
                staged_files=data.get("staged_files", []),
                recent_commits=data.get("recent_commits", []),
                remote_url=data.get("remote_url", ""),
            )
        return GitContext()

    def _build_browser(self, sections: dict) -> BrowserContext:
        data = sections.get("browser", {})
        if isinstance(data, dict):
            return BrowserContext(
                active_tab_title=data.get("active_tab_title", ""),
                active_tab_url=data.get("active_tab_url", ""),
                open_tabs=data.get("open_tabs", []),
                browser_name=data.get("browser_name", ""),
            )
        return BrowserContext()

    def _build_desktop(self, sections: dict) -> DesktopContext:
        data = sections.get("desktop", {})
        if isinstance(data, dict):
            return DesktopContext(
                status=data.get("status", "ready"),
                hotkeys_active=data.get("hotkeys_active", False),
                notifications_pending=data.get("notifications_pending", 0),
            )
        return DesktopContext()

    def _build_voice(self, sections: dict) -> VoiceContext:
        data = sections.get("voice", {})
        if isinstance(data, dict):
            return VoiceContext(
                is_active=data.get("is_active", False),
                state=data.get("state", "idle"),
                conversation_id=data.get("conversation_id", ""),
                is_listening=data.get("is_listening", False),
                is_speaking=data.get("is_speaking", False),
                last_transcript=data.get("last_transcript", ""),
                session_id=data.get("session_id", ""),
            )
        return VoiceContext()

    def _build_memory(self, sections: dict) -> MemoryContext:
        data = sections.get("memory", {})
        if isinstance(data, dict):
            return MemoryContext(
                total_memories=data.get("total_memories", 0),
            )
        return MemoryContext()

    def _build_provider_health(self, sections: dict) -> ProviderHealthContext:
        data = sections.get("provider_health", {})
        if isinstance(data, dict):
            return ProviderHealthContext(
                providers=data.get("providers", {}),
                overall_health=data.get("overall_health", "unknown"),
                active_providers=data.get("active_providers", 0),
                degraded_providers=data.get("degraded_providers", 0),
                failed_providers=data.get("failed_providers", 0),
            )
        return ProviderHealthContext()

    def _build_calendar(self, sections: dict) -> CalendarContext:
        data = sections.get("calendar", {})
        if isinstance(data, dict):
            return CalendarContext(
                events_today=data.get("events_today", []),
                next_event=data.get("next_event"),
                has_upcoming_meeting=data.get("has_upcoming_meeting", False),
            )
        return CalendarContext()

    def _build_selection(self, sections: dict) -> SelectionContext:
        data = sections.get("selection", {})
        if isinstance(data, dict):
            return SelectionContext(
                selected_text=data.get("selected_text", ""),
                source_app=data.get("source_app", ""),
                source_file=data.get("source_file", ""),
                timestamp=data.get("timestamp", 0),
            )
        return SelectionContext()

    def _build_application(self, sections: dict) -> ApplicationContext:
        data = sections.get("application", {})
        if isinstance(data, dict):
            return ApplicationContext(
                running_processes=data.get("running_processes", []),
                foreground_app=data.get("foreground_app", ""),
                background_apps=data.get("background_apps", []),
            )
        return ApplicationContext()

    def _build_tools(self, sections: dict) -> ToolContext:
        data = sections.get("tools", {})
        if isinstance(data, dict):
            return ToolContext(
                available_tools=data.get("available_tools", []),
                recent_tool_calls=data.get("recent_tool_calls", []),
                permissions=data.get("permissions", {}),
            )
        return ToolContext()

    def _build_notifications(self, sections: dict) -> NotificationContext:
        data = sections.get("notifications", {})
        if isinstance(data, dict):
            return NotificationContext(
                pending=data.get("pending", []),
                recent=data.get("recent", []),
                unread_count=data.get("unread_count", 0),
            )
        return NotificationContext()

    # ------------------------------------------------------------------
    # Event Publishing
    # ------------------------------------------------------------------

    async def _publish_change_events(self, ctx: ExecutionContext, prev: ExecutionContext | None, changes: list[str]) -> None:
        if self._event_bus is None:
            return
        await self._event_bus.publish(
            "context:changed",
            {"version": ctx.version, "changes": changes, "context_id": ctx.context_id},
            source=CONTEXT_ENGINE_SOURCE,
        )
        event_map = {
            "window": "context:window_changed",
            "clipboard": "context:clipboard_changed",
            "workspace": "context:workspace_changed",
            "git": "context:git_changed",
            "browser": "context:browser_changed",
            "voice": "context:voice_changed",
            "memory": "context:memory_changed",
            "provider_health": "context:provider_health_changed",
        }
        for section in changes:
            event_type = event_map.get(section)
            if event_type:
                section_data = ctx.to_dict().get(section, {})
                await self._event_bus.publish(event_type, section_data, source=CONTEXT_ENGINE_SOURCE)

    # ------------------------------------------------------------------
    # Memory Storage
    # ------------------------------------------------------------------

    async def _store_observation(self, ctx: ExecutionContext, changes: list[str]) -> None:
        if not self._memory_store:
            return
        try:
            from aios.models.memory import NodeInput
            node_input = NodeInput(
                type="observation",
                subtype="context",
                title=f"Context: {ctx.window.active_app or 'unknown'} — {ctx.window.activity.value}",
                summary=f"App: {ctx.window.active_app} | Activity: {ctx.window.activity.value}",
                source=CONTEXT_ENGINE_SOURCE,
                importance=0.3,
                tags=[ctx.window.activity.value],
                metadata={"changes": changes, "version": ctx.version},
            )
            await self._memory_store.create_node(node_input)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Polling Loop
    # ------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self.collect()
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("context.poll_error", error=str(exc))
                if self._event_bus:
                    await self._event_bus.publish(
                        "context:poll_error",
                        {"error": str(exc)},
                        source=CONTEXT_ENGINE_SOURCE,
                    )
                await asyncio.sleep(self._poll_interval)

    async def poll_now(self) -> ExecutionContext:
        """Force an immediate poll and return the result."""
        return await self.collect()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def diagnostics(self) -> dict:
        """Return engine diagnostics for AI Operations Center."""
        return {
            "version": self._version,
            "context_id": self._current.context_id if self._current else None,
            "providers": self.list_providers(),
            "provider_count": len(self._providers),
            "running": self._running,
            "history_size": len(self._history),
            "cache_sections": list(self._section_cache.keys()),
            "subscriber_count": len(self._subscribers),
            "poll_interval": self._poll_interval,
            "current_hash": self._current.compute_hash() if self._current else None,
        }
