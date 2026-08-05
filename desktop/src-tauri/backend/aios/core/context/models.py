"""Context models — ExecutionContext, ContextProvider protocol, versioning, diffing.

ExecutionContext is the universal context object passed to Hermes and every
EVE subsystem.  It is the ONLY way subsystems access contextual state.

Hermes never inspects Windows, clipboard, browser, or any OS service directly.
Everything flows through ExecutionContext.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActivityType(str, Enum):
    CODING = "coding"
    BROWSING = "browsing"
    WRITING = "writing"
    OFFICE = "office"
    MEETING = "meeting"
    MEDIA = "media"
    IDLE = "idle"
    UNKNOWN = "unknown"


class ContextScope(str, Enum):
    """Privacy scope for context sections."""
    PUBLIC = "public"
    PRIVATE = "private"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


# ---------------------------------------------------------------------------
# Sub-context dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ProjectInfo:
    path: str = ""
    type: str = ""
    markers: list[str] = field(default_factory=list)
    name: str = ""
    git_remote: str = ""

    def to_dict(self) -> dict:
        return {"path": self.path, "type": self.type, "markers": self.markers, "name": self.name, "git_remote": self.git_remote}


@dataclass
class ClipboardContext:
    text: str = ""
    has_content: bool = False
    content_type: str = "text"  # text, image, file
    timestamp: float = 0.0
    scope: ContextScope = ContextScope.PRIVATE

    def to_dict(self) -> dict:
        return {"has_content": self.has_content, "content_type": self.content_type, "timestamp": self.timestamp, "text_length": len(self.text)}


@dataclass
class WindowContext:
    active_app: str = ""
    active_window: str = ""
    active_file: str | None = None
    open_applications: list[str] = field(default_factory=list)
    activity: ActivityType = ActivityType.IDLE
    scope: ContextScope = ContextScope.PUBLIC

    def to_dict(self) -> dict:
        return {
            "active_app": self.active_app,
            "active_window": self.active_window,
            "active_file": self.active_file,
            "open_applications": self.open_applications,
            "activity": self.activity.value,
        }


@dataclass
class WorkspaceContext:
    current_project: ProjectInfo | None = None
    recent_files: list[str] = field(default_factory=list)
    open_files: list[str] = field(default_factory=list)
    workspace_path: str = ""
    scope: ContextScope = ContextScope.PUBLIC

    def to_dict(self) -> dict:
        return {
            "current_project": self.current_project.to_dict() if self.current_project else None,
            "recent_files": self.recent_files[:10],
            "open_files": self.open_files[:10],
            "workspace_path": self.workspace_path,
        }


@dataclass
class GitContext:
    repository_path: str = ""
    current_branch: str = ""
    is_dirty: bool = False
    staged_files: list[str] = field(default_factory=list)
    recent_commits: list[dict] = field(default_factory=list)
    remote_url: str = ""
    scope: ContextScope = ContextScope.PUBLIC

    def to_dict(self) -> dict:
        return {
            "repository_path": self.repository_path,
            "current_branch": self.current_branch,
            "is_dirty": self.is_dirty,
            "staged_count": len(self.staged_files),
            "recent_commits": self.recent_commits[:5],
            "remote_url": self.remote_url,
        }


@dataclass
class BrowserContext:
    active_tab_title: str = ""
    active_tab_url: str = ""
    open_tabs: list[dict] = field(default_factory=list)
    browser_name: str = ""
    scope: ContextScope = ContextScope.PRIVATE

    def to_dict(self) -> dict:
        return {
            "active_tab_title": self.active_tab_title,
            "active_tab_url": self.active_tab_url,
            "tab_count": len(self.open_tabs),
            "browser_name": self.browser_name,
        }


@dataclass
class DesktopContext:
    system_tray_active: bool = False
    notifications_pending: int = 0
    status: str = "ready"
    hotkeys_active: bool = False
    scope: ContextScope = ContextScope.PUBLIC

    def to_dict(self) -> dict:
        return {
            "system_tray_active": self.system_tray_active,
            "notifications_pending": self.notifications_pending,
            "status": self.status,
            "hotkeys_active": self.hotkeys_active,
        }


@dataclass
class VoiceContext:
    is_active: bool = False
    state: str = "idle"
    conversation_id: str = ""
    is_listening: bool = False
    is_speaking: bool = False
    last_transcript: str = ""
    session_id: str = ""
    scope: ContextScope = ContextScope.PRIVATE

    def to_dict(self) -> dict:
        return {
            "is_active": self.is_active,
            "state": self.state,
            "conversation_id": self.conversation_id,
            "is_listening": self.is_listening,
            "is_speaking": self.is_speaking,
            "session_id": self.session_id,
        }


@dataclass
class MemoryContext:
    relevant_memories: list[dict] = field(default_factory=list)
    recent_memories: list[dict] = field(default_factory=list)
    project_memories: list[dict] = field(default_factory=list)
    total_memories: int = 0
    scope: ContextScope = ContextScope.PRIVATE

    def to_dict(self) -> dict:
        return {
            "relevant_count": len(self.relevant_memories),
            "recent_count": len(self.recent_memories),
            "project_count": len(self.project_memories),
            "total_memories": self.total_memories,
        }


@dataclass
class ProviderHealthContext:
    providers: dict[str, dict] = field(default_factory=dict)
    overall_health: str = "unknown"
    active_providers: int = 0
    degraded_providers: int = 0
    failed_providers: int = 0
    scope: ContextScope = ContextScope.PUBLIC

    def to_dict(self) -> dict:
        return {
            "overall_health": self.overall_health,
            "active_providers": self.active_providers,
            "degraded_providers": self.degraded_providers,
            "failed_providers": self.failed_providers,
            "provider_count": len(self.providers),
        }


@dataclass
class CalendarContext:
    events_today: list[dict] = field(default_factory=list)
    next_event: dict | None = None
    has_upcoming_meeting: bool = False
    scope: ContextScope = ContextScope.PRIVATE

    def to_dict(self) -> dict:
        return {
            "events_today": len(self.events_today),
            "next_event": self.next_event,
            "has_upcoming_meeting": self.has_upcoming_meeting,
        }


@dataclass
class SelectionContext:
    selected_text: str = ""
    source_app: str = ""
    source_file: str = ""
    timestamp: float = 0.0
    scope: ContextScope = ContextScope.PRIVATE

    def to_dict(self) -> dict:
        return {
            "has_selection": bool(self.selected_text),
            "text_length": len(self.selected_text),
            "source_app": self.source_app,
            "source_file": self.source_file,
        }


@dataclass
class ApplicationContext:
    running_processes: list[str] = field(default_factory=list)
    foreground_app: str = ""
    background_apps: list[str] = field(default_factory=list)
    scope: ContextScope = ContextScope.PUBLIC

    def to_dict(self) -> dict:
        return {
            "foreground_app": self.foreground_app,
            "running_count": len(self.running_processes),
            "background_count": len(self.background_apps),
        }


@dataclass
class ToolContext:
    available_tools: list[dict] = field(default_factory=list)
    recent_tool_calls: list[dict] = field(default_factory=list)
    permissions: dict[str, str] = field(default_factory=dict)
    scope: ContextScope = ContextScope.PUBLIC

    def to_dict(self) -> dict:
        return {
            "available_count": len(self.available_tools),
            "recent_calls": len(self.recent_tool_calls),
            "permissions": self.permissions,
        }


@dataclass
class NotificationContext:
    pending: list[dict] = field(default_factory=list)
    recent: list[dict] = field(default_factory=list)
    unread_count: int = 0
    scope: ContextScope = ContextScope.PUBLIC

    def to_dict(self) -> dict:
        return {
            "pending_count": len(self.pending),
            "unread_count": self.unread_count,
            "recent_count": len(self.recent),
        }


# ---------------------------------------------------------------------------
# ExecutionContext — the universal context object
# ---------------------------------------------------------------------------

@dataclass
class ExecutionContext:
    """The universal context object.

    Every EVE subsystem and Hermes receives this object.
    Hermes NEVER accesses OS services directly — only this object.
    """
    # Identity
    context_id: str = field(default_factory=lambda: uuid4().hex)
    version: int = 0
    session_id: str = ""
    execution_id: str = ""
    timestamp: float = 0.0

    # Sub-contexts
    window: WindowContext = field(default_factory=WindowContext)
    clipboard: ClipboardContext = field(default_factory=ClipboardContext)
    workspace: WorkspaceContext = field(default_factory=WorkspaceContext)
    git: GitContext = field(default_factory=GitContext)
    browser: BrowserContext = field(default_factory=BrowserContext)
    desktop: DesktopContext = field(default_factory=DesktopContext)
    voice: VoiceContext = field(default_factory=VoiceContext)
    memory: MemoryContext = field(default_factory=MemoryContext)
    provider_health: ProviderHealthContext = field(default_factory=ProviderHealthContext)
    calendar: CalendarContext = field(default_factory=CalendarContext)
    selection: SelectionContext = field(default_factory=SelectionContext)
    application: ApplicationContext = field(default_factory=ApplicationContext)
    tools: ToolContext = field(default_factory=ToolContext)
    notifications: NotificationContext = field(default_factory=NotificationContext)

    # Metadata
    changed_providers: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).timestamp()

    def to_dict(self) -> dict:
        return {
            "context_id": self.context_id,
            "version": self.version,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "window": self.window.to_dict(),
            "clipboard": self.clipboard.to_dict(),
            "workspace": self.workspace.to_dict(),
            "git": self.git.to_dict(),
            "browser": self.browser.to_dict(),
            "desktop": self.desktop.to_dict(),
            "voice": self.voice.to_dict(),
            "memory": self.memory.to_dict(),
            "provider_health": self.provider_health.to_dict(),
            "calendar": self.calendar.to_dict(),
            "selection": self.selection.to_dict(),
            "application": self.application.to_dict(),
            "tools": self.tools.to_dict(),
            "notifications": self.notifications.to_dict(),
            "changed_providers": self.changed_providers,
        }

    def compute_hash(self) -> str:
        """Compute a hash of the context for cache invalidation."""
        data = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def diff(self, other: "ExecutionContext | None") -> list[str]:
        """Return list of changed section names compared to another context."""
        if other is None:
            return [
                "window", "clipboard", "workspace", "git", "browser",
                "desktop", "voice", "memory", "provider_health",
                "calendar", "selection", "application", "tools", "notifications",
            ]
        changes: list[str] = []
        sections = [
            ("window", self.window, other.window),
            ("clipboard", self.clipboard, other.clipboard),
            ("workspace", self.workspace, other.workspace),
            ("git", self.git, other.git),
            ("browser", self.browser, other.browser),
            ("desktop", self.desktop, other.desktop),
            ("voice", self.voice, other.voice),
            ("memory", self.memory, other.memory),
            ("provider_health", self.provider_health, other.provider_health),
            ("calendar", self.calendar, other.calendar),
            ("selection", self.selection, other.selection),
            ("application", self.application, other.application),
            ("tools", self.tools, other.tools),
            ("notifications", self.notifications, other.notifications),
        ]
        for name, current, previous in sections:
            if current.to_dict() != previous.to_dict():
                changes.append(name)
        return changes

    # Convenience accessors (backward-compatible with old Context API)

    @property
    def active_app(self) -> str:
        return self.window.active_app

    @property
    def active_window(self) -> str:
        return self.window.active_window

    @property
    def active_file(self) -> str | None:
        return self.window.active_file

    @property
    def project(self) -> ProjectInfo | None:
        return self.workspace.current_project

    @property
    def activity(self) -> ActivityType:
        return self.window.activity


# ---------------------------------------------------------------------------
# Context Provider protocol
# ---------------------------------------------------------------------------

class ContextProvider:
    """Base class for all context providers.

    Each provider owns one responsibility:
    - Collects data from one source
    - Publishes change events
    - Never knows about Hermes or any agent

    Providers must implement collect() and provider_id.
    """

    @property
    def provider_id(self) -> str:
        raise NotImplementedError

    @property
    def display_name(self) -> str:
        return self.provider_id

    @property
    def scope(self) -> ContextScope:
        return ContextScope.PUBLIC

    async def start(self) -> None:
        """Start the provider (optional lifecycle hook)."""
        pass

    async def stop(self) -> None:
        """Stop the provider (optional lifecycle hook)."""
        pass

    async def collect(self) -> dict[str, Any]:
        """Collect current context data from this source.

        Returns a dict that will be merged into ExecutionContext.
        Must be async and non-blocking where possible.
        """
        return {}

    async def on_event(self, event_type: str, payload: dict) -> None:
        """Handle an EventBus event that may affect this provider's context.

        Providers subscribe to relevant events and update their internal state.
        """
        pass

    def invalidate_cache(self) -> None:
        """Force cache invalidation for this provider."""
        pass
