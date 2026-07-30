"""Launcher lifecycle events."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


LAUNCHER_STARTING = "launcher:starting"
LAUNCHER_READY = "launcher:ready"
LAUNCHER_STOPPING = "launcher:stopping"
LAUNCHER_STOPPED = "launcher:stopped"
LAUNCHER_ERROR = "launcher:error"
BACKEND_STARTED = "backend:started"
BACKEND_STOPPED = "backend:stopped"
BACKEND_FAILED = "backend:failed"
BACKEND_DEGRADED = "backend:degraded"
FRONTEND_STARTED = "frontend:started"
FRONTEND_STOPPED = "frontend:stopped"
FRONTEND_FAILED = "frontend:failed"
PROVIDER_CONNECTED = "provider:connected"
PROVIDER_DISCONNECTED = "provider:disconnected"
SERVICE_HEALTH_CHANGED = "service:health_changed"
SHUTDOWN_REQUESTED = "shutdown:requested"
SHUTDOWN_COMPLETED = "shutdown:completed"
RESTART_REQUESTED = "restart:requested"
RESTART_COMPLETED = "restart:completed"


@dataclass
class LauncherEvent:
    type: str
    data: dict = field(default_factory=dict)
    id: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


EventHandler = callable  # type: ignore
