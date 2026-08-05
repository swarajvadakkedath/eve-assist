"""Context Providers — each owns one context source.

Providers are modular, testable, and know nothing about Hermes.
They collect structured data from a single source and return it
as a dict that the Context Engine merges into ExecutionContext.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from aios.core.context.models import (
    ClipboardContext,
    WindowContext,
    WorkspaceContext,
    GitContext,
    BrowserContext,
    DesktopContext,
    VoiceContext,
    MemoryContext,
    ProviderHealthContext,
    CalendarContext,
    SelectionContext,
    ApplicationContext,
    ToolContext,
    NotificationContext,
    ContextScope,
    ActivityType,
    ProjectInfo,
)


# ---------------------------------------------------------------------------
# ClipboardProvider
# ---------------------------------------------------------------------------

class ClipboardProvider:
    """Provides clipboard context. Reads current clipboard content."""

    @property
    def provider_id(self) -> str:
        return "clipboard"

    @property
    def display_name(self) -> str:
        return "Clipboard"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PRIVATE

    def __init__(self):
        self._last_content = ""
        self._last_check = 0.0
        self._cache_ttl = 2.0  # seconds

    async def collect(self) -> dict[str, Any]:
        now = time.monotonic()
        if now - self._last_check < self._cache_ttl:
            return {}
        self._last_check = now
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000 if __import__("sys").platform == "win32" else 0,
            )
            text = result.stdout.strip() if result.returncode == 0 else ""
            changed = text != self._last_content
            self._last_content = text
            return {
                "clipboard": ClipboardContext(
                    text=text[:10000] if text else "",
                    has_content=bool(text),
                    content_type="text",
                    timestamp=now,
                    scope=ContextScope.PRIVATE,
                ).to_dict() if changed or not text else {},
            }
        except Exception:
            return {}

    def invalidate_cache(self) -> None:
        self._last_check = 0.0


# ---------------------------------------------------------------------------
# WindowProvider
# ---------------------------------------------------------------------------

class WindowProvider:
    """Provides active window and application context via WindowsAdapter."""

    @property
    def provider_id(self) -> str:
        return "window"

    @property
    def display_name(self) -> str:
        return "Window"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    def __init__(self, windows_adapter=None):
        self._windows = windows_adapter

    async def collect(self) -> dict[str, Any]:
        if self._windows is None:
            return {}
        try:
            window = await self._windows.get_active_window()
            app = window.app if window else ""
            title = window.title if window else ""
            from aios.core.context.activity_detector import detect_activity, extract_active_file
            activity = detect_activity(app, title)
            active_file = extract_active_file(app, title)
            return {
                "window": WindowContext(
                    active_app=app,
                    active_window=title,
                    active_file=active_file,
                    activity=activity,
                ).to_dict(),
            }
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# WorkspaceProvider
# ---------------------------------------------------------------------------

class WorkspaceProvider:
    """Provides workspace and project context."""

    @property
    def provider_id(self) -> str:
        return "workspace"

    @property
    def display_name(self) -> str:
        return "Workspace"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    def __init__(self):
        self._recent_files: list[str] = []
        self._workspace_path = ""

    async def collect(self) -> dict[str, Any]:
        return {
            "workspace": WorkspaceContext(
                recent_files=self._recent_files[:20],
                workspace_path=self._workspace_path,
            ).to_dict(),
        }

    def set_workspace(self, path: str) -> None:
        self._workspace_path = path

    def add_recent_file(self, path: str) -> None:
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:50]

    async def on_event(self, event_type: str, payload: dict) -> None:
        if event_type == "context:file_changed":
            path = payload.get("path", "")
            if path:
                self.add_recent_file(path)
        elif event_type in ("workspace:opened", "workspace:changed"):
            self._workspace_path = payload.get("path", self._workspace_path)


# ---------------------------------------------------------------------------
# GitProvider
# ---------------------------------------------------------------------------

class GitProvider:
    """Provides git repository context."""

    @property
    def provider_id(self) -> str:
        return "git"

    @property
    def display_name(self) -> str:
        return "Git"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    def __init__(self):
        self._repo_path = ""
        self._branch = ""
        self._is_dirty = False
        self._remote_url = ""
        self._last_check = 0.0
        self._cache_ttl = 10.0

    async def collect(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._repo_path and now - self._last_check < self._cache_ttl:
            return {
                "git": GitContext(
                    repository_path=self._repo_path,
                    current_branch=self._branch,
                    is_dirty=self._is_dirty,
                    remote_url=self._remote_url,
                ).to_dict(),
            }
        if not self._repo_path:
            return {"git": GitContext().to_dict()}
        try:
            import subprocess
            def _git(args: list[str]) -> str:
                r = subprocess.run(
                    ["git"] + args,
                    cwd=self._repo_path,
                    capture_output=True, text=True, timeout=5,
                    creationflags=0x08000000 if __import__("sys").platform == "win32" else 0,
                )
                return r.stdout.strip() if r.returncode == 0 else ""

            branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
            is_dirty = bool(_git(["status", "--porcelain"]))
            remote = _git(["remote", "get-url", "origin"])
            self._branch = branch
            self._is_dirty = is_dirty
            self._remote_url = remote
            self._last_check = now
            return {
                "git": GitContext(
                    repository_path=self._repo_path,
                    current_branch=branch,
                    is_dirty=is_dirty,
                    remote_url=remote,
                ).to_dict(),
            }
        except Exception:
            return {}

    def set_repository(self, path: str) -> None:
        self._repo_path = path
        self._last_check = 0.0

    def invalidate_cache(self) -> None:
        self._last_check = 0.0


# ---------------------------------------------------------------------------
# BrowserProvider
# ---------------------------------------------------------------------------

class BrowserProvider:
    """Provides browser tab context. Stub — requires browser extension or API."""

    @property
    def provider_id(self) -> str:
        return "browser"

    @property
    def display_name(self) -> str:
        return "Browser"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PRIVATE

    def __init__(self):
        self._active_title = ""
        self._active_url = ""
        self._tabs: list[dict] = []

    async def collect(self) -> dict[str, Any]:
        return {
            "browser": BrowserContext(
                active_tab_title=self._active_title,
                active_tab_url=self._active_url,
                open_tabs=self._tabs,
            ).to_dict(),
        }

    def update(self, title: str = "", url: str = "", tabs: list[dict] | None = None) -> None:
        self._active_title = title
        self._active_url = url
        if tabs is not None:
            self._tabs = tabs


# ---------------------------------------------------------------------------
# DesktopProvider
# ---------------------------------------------------------------------------

class DesktopProvider:
    """Provides desktop state context — tray, notifications, hotkeys."""

    @property
    def provider_id(self) -> str:
        return "desktop"

    @property
    def display_name(self) -> str:
        return "Desktop"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    def __init__(self, status_service=None, hotkey_manager=None):
        self._status_service = status_service
        self._hotkey_manager = hotkey_manager
        self._notifications_pending = 0

    async def collect(self) -> dict[str, Any]:
        status = "ready"
        if self._status_service:
            try:
                status = self._status_service.get_status().value
            except Exception:
                pass
        hotkeys_active = False
        if self._hotkey_manager:
            try:
                hotkeys_active = True
            except Exception:
                pass
        return {
            "desktop": DesktopContext(
                status=status,
                hotkeys_active=hotkeys_active,
                notifications_pending=self._notifications_pending,
            ).to_dict(),
        }

    def set_notification_count(self, count: int) -> None:
        self._notifications_pending = count


# ---------------------------------------------------------------------------
# VoiceProvider
# ---------------------------------------------------------------------------

class VoiceProvider:
    """Provides voice session context."""

    @property
    def provider_id(self) -> str:
        return "voice"

    @property
    def display_name(self) -> str:
        return "Voice"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PRIVATE

    def __init__(self):
        self._state = VoiceContext()

    async def collect(self) -> dict[str, Any]:
        return {"voice": self._state.to_dict()}

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)

    async def on_event(self, event_type: str, payload: dict) -> None:
        if event_type == "voice:state:change":
            self._state.state = payload.get("state", self._state.state)
            self._state.is_active = payload.get("state", "") != "idle"
        elif event_type == "voice:listening:start":
            self._state.is_listening = True
        elif event_type == "voice:listening:stop":
            self._state.is_listening = False
        elif event_type == "voice:speaking:start":
            self._state.is_speaking = True
        elif event_type == "voice:speaking:stop":
            self._state.is_speaking = False
        elif event_type == "voice:transcript:final":
            self._state.last_transcript = payload.get("text", "")


# ---------------------------------------------------------------------------
# MemoryProvider
# ---------------------------------------------------------------------------

class MemoryProvider:
    """Provides memory context — relevant, recent, and project memories."""

    @property
    def provider_id(self) -> str:
        return "memory"

    @property
    def display_name(self) -> str:
        return "Memory"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PRIVATE

    def __init__(self, memory_system=None):
        self._memory = memory_system
        self._last_query = ""
        self._cached_result: dict | None = None
        self._cache_time = 0.0
        self._cache_ttl = 30.0

    async def collect(self) -> dict[str, Any]:
        if self._memory is None:
            return {"memory": MemoryContext().to_dict()}
        try:
            stats = await self._memory.stats() if hasattr(self._memory, "stats") else {}
            total = stats.get("total_nodes", 0) if isinstance(stats, dict) else 0
            return {
                "memory": MemoryContext(total_memories=total).to_dict(),
            }
        except Exception:
            return {"memory": MemoryContext().to_dict()}

    async def query_relevant(self, query: str, conversation_id: str = "") -> list[dict]:
        """Query relevant memories for a specific conversation."""
        if self._memory is None:
            return []
        now = time.monotonic()
        cache_key = f"{query}:{conversation_id}"
        if self._cached_result and self._last_query == cache_key and now - self._cache_time < self._cache_ttl:
            return self._cached_result.get("memories", [])
        try:
            results = await self._memory.search(query, limit=10)
            memories = []
            for m in results:
                memories.append({
                    "content": getattr(m, "content", str(m)),
                    "type": getattr(m, "type", "unknown"),
                    "importance": getattr(m, "importance", 0.5),
                })
            self._last_query = cache_key
            self._cached_result = {"memories": memories}
            self._cache_time = now
            return memories
        except Exception:
            return []

    def invalidate_cache(self) -> None:
        self._cached_result = None
        self._cache_time = 0.0


# ---------------------------------------------------------------------------
# ProviderHealthProvider
# ---------------------------------------------------------------------------

class ProviderHealthProvider:
    """Provides AI provider health context."""

    @property
    def provider_id(self) -> str:
        return "provider_health"

    @property
    def display_name(self) -> str:
        return "Provider Health"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    def __init__(self, health_monitor=None):
        self._health_monitor = health_monitor

    async def collect(self) -> dict[str, Any]:
        if self._health_monitor is None:
            return {"provider_health": ProviderHealthContext().to_dict()}
        try:
            all_health = self._health_monitor.get_all_health()
            providers = {}
            active = 0
            degraded = 0
            failed = 0
            for pid, h in all_health.items():
                state = h.state.value if hasattr(h.state, "value") else str(h.state)
                providers[pid] = {
                    "state": state,
                    "health_score": getattr(h, "health_score", 0),
                    "success_rate": getattr(h, "success_rate", 0),
                    "latency_ms": getattr(h, "latency_ms", 0),
                }
                if state == "healthy":
                    active += 1
                elif state == "degraded":
                    degraded += 1
                elif state in ("unreachable", "invalid_key", "quota_exceeded"):
                    failed += 1
            overall = "healthy" if failed == 0 and degraded == 0 else "degraded" if failed == 0 else "failing"
            return {
                "provider_health": ProviderHealthContext(
                    providers=providers,
                    overall_health=overall,
                    active_providers=active,
                    degraded_providers=degraded,
                    failed_providers=failed,
                ).to_dict(),
            }
        except Exception:
            return {"provider_health": ProviderHealthContext().to_dict()}


# ---------------------------------------------------------------------------
# CalendarProvider
# ---------------------------------------------------------------------------

class CalendarProvider:
    """Provides calendar context. Stub — requires calendar API integration."""

    @property
    def provider_id(self) -> str:
        return "calendar"

    @property
    def display_name(self) -> str:
        return "Calendar"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PRIVATE

    def __init__(self):
        self._events: list[dict] = []
        self._next_event: dict | None = None

    async def collect(self) -> dict[str, Any]:
        return {
            "calendar": CalendarContext(
                events_today=self._events,
                next_event=self._next_event,
                has_upcoming_meeting=self._next_event is not None,
            ).to_dict(),
        }

    def update_events(self, events: list[dict], next_event: dict | None = None) -> None:
        self._events = events
        self._next_event = next_event


# ---------------------------------------------------------------------------
# SelectionProvider
# ---------------------------------------------------------------------------

class SelectionProvider:
    """Provides selected text context."""

    @property
    def provider_id(self) -> str:
        return "selection"

    @property
    def display_name(self) -> str:
        return "Selection"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PRIVATE

    def __init__(self):
        self._selected_text = ""
        self._source_app = ""
        self._source_file = ""
        self._timestamp = 0.0

    async def collect(self) -> dict[str, Any]:
        return {
            "selection": SelectionContext(
                selected_text=self._selected_text[:5000],
                source_app=self._source_app,
                source_file=self._source_file,
                timestamp=self._timestamp,
            ).to_dict(),
        }

    def update(self, text: str = "", source_app: str = "", source_file: str = "") -> None:
        self._selected_text = text
        self._source_app = source_app
        self._source_file = source_file
        self._timestamp = time.time()

    def clear(self) -> None:
        self._selected_text = ""
        self._source_app = ""
        self._source_file = ""
        self._timestamp = 0.0


# ---------------------------------------------------------------------------
# ApplicationProvider
# ---------------------------------------------------------------------------

class ApplicationProvider:
    """Provides running application context."""

    @property
    def provider_id(self) -> str:
        return "application"

    @property
    def display_name(self) -> str:
        return "Applications"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    def __init__(self):
        self._processes: list[str] = []
        self._foreground = ""
        self._background: list[str] = []

    async def collect(self) -> dict[str, Any]:
        return {
            "application": ApplicationContext(
                running_processes=self._processes,
                foreground_app=self._foreground,
                background_apps=self._background,
            ).to_dict(),
        }

    def update(self, foreground: str = "", processes: list[str] | None = None) -> None:
        self._foreground = foreground
        if processes is not None:
            self._processes = processes


# ---------------------------------------------------------------------------
# ToolProvider
# ---------------------------------------------------------------------------

class ToolProvider:
    """Provides tool availability and permission context."""

    @property
    def provider_id(self) -> str:
        return "tools"

    @property
    def display_name(self) -> str:
        return "Tools"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    def __init__(self, tool_manager=None):
        self._tool_manager = tool_manager
        self._recent_calls: list[dict] = []

    async def collect(self) -> dict[str, Any]:
        tools = []
        if self._tool_manager:
            try:
                tool_list = await self._tool_manager.list_tools()
                tools = [
                    {"id": getattr(t, "id", ""), "name": getattr(t, "name", ""), "category": getattr(t, "category", "")}
                    for t in tool_list
                ]
            except Exception:
                pass
        return {
            "tools": ToolContext(
                available_tools=tools,
                recent_tool_calls=self._recent_calls[-10:],
            ).to_dict(),
        }

    def record_tool_call(self, tool_id: str, success: bool, duration_ms: float) -> None:
        self._recent_calls.append({
            "tool_id": tool_id,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": time.time(),
        })
        if len(self._recent_calls) > 50:
            self._recent_calls = self._recent_calls[-50:]


# ---------------------------------------------------------------------------
# NotificationProvider
# ---------------------------------------------------------------------------

class NotificationProvider:
    """Provides notification context."""

    @property
    def provider_id(self) -> str:
        return "notifications"

    @property
    def display_name(self) -> str:
        return "Notifications"

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    def __init__(self):
        self._pending: list[dict] = []
        self._recent: list[dict] = []
        self._unread_count = 0

    async def collect(self) -> dict[str, Any]:
        return {
            "notifications": NotificationContext(
                pending=self._pending[:20],
                recent=self._recent[:20],
                unread_count=self._unread_count,
            ).to_dict(),
        }

    def add_notification(self, notification: dict) -> None:
        self._pending.append(notification)
        self._unread_count += 1

    def mark_read(self) -> None:
        self._unread_count = 0
        self._recent.extend(self._pending)
        self._pending = []
        if len(self._recent) > 100:
            self._recent = self._recent[-100:]
