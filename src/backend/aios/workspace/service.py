"""Workspace Service — service layer wrapping WorkspaceManager."""

from typing import Any
from aios.workspace.manager import WorkspaceManager
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class WorkspaceService:
    def __init__(self, manager: WorkspaceManager | None = None):
        self._manager = manager or WorkspaceManager()

    @property
    def manager(self) -> WorkspaceManager:
        return self._manager

    async def start(self) -> None:
        await self._manager.start()

    async def stop(self) -> None:
        await self._manager.stop()

    async def get_current_context(self) -> dict:
        return await self._manager.get_context_for_conversation()
