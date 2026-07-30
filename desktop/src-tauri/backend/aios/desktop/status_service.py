"""Application Status Service — centralized status management for AIOS.

Sprint 12.9 — Application Status Service.
"""

import enum
import inspect
import time
from datetime import datetime, timezone
from typing import Callable, Any
from uuid import uuid4

from aios.utils.logger import get_logger

logger = get_logger(__name__)


class AppStatus(str, enum.Enum):
    STARTING = "starting"
    READY = "ready"
    LISTENING = "listening"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING = "waiting"
    UPDATING = "updating"
    OFFLINE = "offline"
    ERROR = "error"


StatusObserver = Callable[[AppStatus, dict], None]


class StatusService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._status: AppStatus = AppStatus.STARTING
        self._observers: list[StatusObserver] = []
        self._history: list[dict] = []
        self._max_history = 100
        self._metadata: dict = {}
        self._initialized = True

    @property
    def status(self) -> AppStatus:
        return self._status

    async def set_status(self, new_status: AppStatus, metadata: dict | None = None) -> None:
        old_status = self._status
        self._status = new_status
        if metadata:
            self._metadata = metadata
        entry = {
            "old_status": old_status.value,
            "new_status": new_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        for observer in self._observers:
            try:
                result = observer(new_status, metadata or {})
                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                __import__("logging").getLogger(__name__).error("status_observer_failed: %s", str(e))

    def get_status(self) -> AppStatus:
        return self._status

    def get_history(self, limit: int = 50) -> list[dict]:
        return self._history[-limit:]

    def get_metadata(self) -> dict:
        return dict(self._metadata)

    def subscribe(self, observer: StatusObserver) -> None:
        self._observers.append(observer)

    def unsubscribe(self, observer: StatusObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)
