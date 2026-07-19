"""Context Engine — application/file/project tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable


@dataclass
class Context:
    active_app: str | None = None
    active_window: str | None = None
    active_file: str | None = None
    project_path: str | None = None
    project_type: str | None = None
    recent_files: list[str] = field(default_factory=list)
    open_applications: list[str] = field(default_factory=list)
    activity: str = "idle"
    timestamp: datetime = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow()


class ContextEngine:
    def __init__(self, poll_interval: float = 2.0):
        self._poll_interval = poll_interval
        self._current: Context = Context()
        self._history: list[Context] = []
        self._handlers: list[Callable] = []

    async def get_current_context(self) -> Context:
        return self._current

    async def get_active_app(self) -> str:
        return self._current.active_app or ""

    async def get_active_file(self) -> str | None:
        return self._current.active_file

    async def detect_project(self) -> dict | None:
        if self._current.project_path:
            return {"path": self._current.project_path, "type": self._current.project_type}
        return None

    async def get_recent_activity(self, minutes: int = 5) -> list[Context]:
        cutoff = datetime.utcnow().timestamp() - (minutes * 60)
        return [c for c in self._history if c.timestamp.timestamp() > cutoff]

    async def subscribe_context_changes(self, handler: Callable) -> None:
        self._handlers.append(handler)
