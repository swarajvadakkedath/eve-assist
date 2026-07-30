"""Workspace Repository — persist workspace state."""

from typing import Any
from aios.workspace.models import Workspace, Project
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class WorkspaceRepository:
    def __init__(self, db: Any | None = None):
        self._db = db
        self._workspaces: dict[str, Workspace] = {}

    async def save_workspace(self, workspace: Workspace) -> None:
        self._workspaces[workspace.id] = workspace

    async def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self._workspaces.get(workspace_id)

    async def list_workspaces(self) -> list[Workspace]:
        return list(self._workspaces.values())

    async def save_project(self, project: Project) -> None:
        pass

    async def get_projects(self) -> list[Project]:
        return []

    async def delete_workspace(self, workspace_id: str) -> None:
        self._workspaces.pop(workspace_id, None)
