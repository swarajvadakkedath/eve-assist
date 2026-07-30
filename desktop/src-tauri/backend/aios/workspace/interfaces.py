"""Workspace Interfaces — abstract contracts."""

from abc import ABC, abstractmethod
from typing import Any

from aios.workspace.models import WorkspaceSnapshot, Application, Project, Repository, Editor, Terminal


class IWorkspaceSensor(ABC):
    @abstractmethod
    async def collect(self) -> dict:
        ...

    @abstractmethod
    async def start(self) -> None:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...


class IProjectDetector(ABC):
    @abstractmethod
    async def detect(self, path: str) -> Project | None:
        ...


class IWorkspaceManager(ABC):
    @abstractmethod
    async def get_current_snapshot(self) -> WorkspaceSnapshot:
        ...

    @abstractmethod
    async def refresh(self) -> WorkspaceSnapshot:
        ...


class IWorkspaceCache(ABC):
    @abstractmethod
    async def get_snapshot(self) -> WorkspaceSnapshot | None:
        ...

    @abstractmethod
    async def update_snapshot(self, snapshot: WorkspaceSnapshot) -> None:
        ...
