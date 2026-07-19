"""Desktop Notifications — native Windows notifications.

Sprint 12.5 — Desktop Notifications.
"""

import enum
import time
from datetime import datetime
from typing import Callable, Any
from uuid import uuid4

from aios.desktop.settings_store import SettingsStore
from aios.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from plyer import notification as plyer_notification
    _HAS_PLYER = True
except ImportError:
    _HAS_PLYER = False


class NotificationType(str, enum.Enum):
    PERMISSION_REQUEST = "permission_request"
    TASK_COMPLETED = "task_completed"
    AI_FINISHED = "ai_finished"
    PLUGIN_INSTALLED = "plugin_installed"
    UPDATE_AVAILABLE = "update_available"
    WARNING = "warning"
    ERROR = "error"


NOTIFICATION_PREFERENCES_KEY: dict[NotificationType, str] = {
    NotificationType.PERMISSION_REQUEST: "notifications.permission_requests",
    NotificationType.TASK_COMPLETED: "notifications.task_completed",
    NotificationType.AI_FINISHED: "notifications.ai_finished",
    NotificationType.PLUGIN_INSTALLED: "notifications.plugin_installed",
    NotificationType.UPDATE_AVAILABLE: "notifications.update_available",
    NotificationType.WARNING: "notifications.warnings",
    NotificationType.ERROR: "notifications.errors",
}


class NotificationService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._settings_store = None
        self._history: list[dict] = []
        self._max_history = 100
        self._initialized = True

    async def initialize(self, settings_store) -> None:
        self._settings_store = settings_store

    async def show(
        self,
        title: str,
        message: str,
        notification_type: str = "info",
        timeout: int = 5,
        actions: list[dict] | None = None,
    ) -> None:
        if self._settings_store:
            pref_key = f"notifications.{notification_type}"
            enabled = await self._settings_store.get(pref_key, True)
            if not enabled:
                return
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                timeout=timeout,
            )
        except Exception as e:
            logger.error("notification.failed", title=title, error=str(e))
        self._history.append({
            "title": title,
            "message": message,
            "type": notification_type,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "actions": actions or [],
        })
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(self, limit: int = 50) -> list[dict]:
        return self._history[-limit:]

    def clear_history(self) -> None:
        self._history.clear()