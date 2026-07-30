"""Workspace Event Publisher — publishes workspace events to the Event Bus."""

from typing import Any
from aios.utils.logger import get_logger

logger = get_logger(__name__)


WORKSPACE_EVENT_TYPES = {
    "updated": "workspace.updated",
    "project_detected": "workspace.project.detected",
    "project_changed": "workspace.project.changed",
    "application_focused": "workspace.application.focused",
    "application_closed": "workspace.application.closed",
    "git_updated": "workspace.git.updated",
    "editor_changed": "workspace.editor.changed",
    "terminal_changed": "workspace.terminal.changed",
    "snapshot_created": "workspace.snapshot.created",
}


class WorkspaceEventPublisher:
    def __init__(self, event_bus: Any | None = None):
        self._event_bus = event_bus

    async def publish(self, event_type: str, payload: dict, correlation_id: str = "") -> None:
        if not self._event_bus:
            return
        try:
            await self._event_bus.publish(
                event_type=event_type,
                payload=payload,
                source="workspace",
                correlation_id=correlation_id,
            )
        except Exception as e:
            logger.error("workspace_event.publish_failed", event_type=event_type, error=str(e))

    async def workspace_updated(self, snapshot: Any) -> None:
        await self.publish("workspace.updated", {
            "timestamp": snapshot.timestamp.isoformat() if hasattr(snapshot, "timestamp") else "",
            "active_window": snapshot.active_window or "",
            "project_count": len(snapshot.projects) if hasattr(snapshot, "projects") else 0,
        })

    async def project_detected(self, project: Any) -> None:
        await self.publish("workspace.project.detected", {
            "path": project.root_path if hasattr(project, "root_path") else "",
            "name": project.name if hasattr(project, "name") else "",
            "framework": project.framework.value if hasattr(project, "framework") else "",
        })

    async def application_focused(self, app_name: str) -> None:
        await self.publish("workspace.application.focused", {
            "application": app_name,
        })

    async def git_updated(self, repo: Any) -> None:
        await self.publish("workspace.git.updated", {
            "branch": repo.branch if hasattr(repo, "branch") else "",
            "dirty": repo.dirty if hasattr(repo, "dirty") else False,
            "modified_count": len(repo.modified_files) if hasattr(repo, "modified_files") else 0,
        })

    async def editor_changed(self, editor: Any) -> None:
        await self.publish("workspace.editor.changed", {
            "name": editor.name if hasattr(editor, "name") else "",
            "active_file": editor.active_file if hasattr(editor, "active_file") else "",
        })

    async def snapshot_created(self, snapshot: Any) -> None:
        await self.publish("workspace.snapshot.created", {
            "timestamp": snapshot.timestamp.isoformat() if hasattr(snapshot, "timestamp") else "",
        })
