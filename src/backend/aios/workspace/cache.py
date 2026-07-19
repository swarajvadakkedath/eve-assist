"""Workspace Cache — incremental updates with automatic expiration."""

from datetime import datetime, timedelta
from typing import Any
from aios.workspace.models import WorkspaceSnapshot


class WorkspaceCache:
    def __init__(self, ttl_seconds: int = 10):
        self._snapshot: WorkspaceSnapshot | None = None
        self._updated_at: datetime | None = None
        self._ttl = timedelta(seconds=ttl_seconds)
        self._snapshots: list[WorkspaceSnapshot] = []
        self._max_snapshots = 50

    async def get_snapshot(self) -> WorkspaceSnapshot | None:
        if self._snapshot and self._updated_at:
            if datetime.utcnow() - self._updated_at < self._ttl:
                return self._snapshot
        return None

    async def update_snapshot(self, snapshot: WorkspaceSnapshot) -> None:
        self._snapshot = snapshot
        self._updated_at = datetime.utcnow()
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]

    async def get_history(self, limit: int = 10) -> list[WorkspaceSnapshot]:
        return self._snapshots[-limit:]

    async def invalidate(self) -> None:
        self._snapshot = None
        self._updated_at = None

    async def get_cached_snapshot_count(self) -> int:
        return len(self._snapshots)

    async def get_cache_age_seconds(self) -> float:
        if self._updated_at:
            return (datetime.utcnow() - self._updated_at).total_seconds()
        return -1
