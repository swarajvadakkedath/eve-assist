"""Context models — Context dataclass, ActivityType, ProjectInfo."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ActivityType(str, Enum):
    CODING = "coding"
    BROWSING = "browsing"
    WRITING = "writing"
    OFFICE = "office"
    IDLE = "idle"
    UNKNOWN = "unknown"


@dataclass
class ProjectInfo:
    path: str
    type: str
    markers: list[str] = field(default_factory=list)


@dataclass
class Context:
    active_app: str | None = None
    active_window: str | None = None
    active_file: str | None = None
    project: ProjectInfo | None = None
    recent_files: list[str] = field(default_factory=list)
    open_applications: list[str] = field(default_factory=list)
    activity: ActivityType = ActivityType.IDLE
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).timestamp()

    def to_dict(self) -> dict:
        return {
            "active_app": self.active_app,
            "active_window": self.active_window,
            "active_file": self.active_file,
            "project_path": self.project.path if self.project else None,
            "project_type": self.project.type if self.project else None,
            "project_markers": self.project.markers if self.project else [],
            "recent_files": self.recent_files,
            "open_applications": self.open_applications,
            "activity": self.activity.value,
            "timestamp": self.timestamp,
        }

    def changed_since(self, other: "Context | None") -> list[str]:
        if other is None:
            return ["active_app", "active_window", "active_file", "project", "activity"]
        changes: list[str] = []
        if self.active_app != other.active_app:
            changes.append("active_app")
        if self.active_window != other.active_window:
            changes.append("active_window")
        if self.active_file != other.active_file:
            changes.append("active_file")
        if self.project != other.project:
            changes.append("project")
        if self.activity != other.activity:
            changes.append("activity")
        return changes
