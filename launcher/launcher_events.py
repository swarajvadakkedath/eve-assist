"""Launcher lifecycle events."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
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
BACKEND_EXIT = "backend:exit"
BACKEND_RESTART_ATTEMPT = "backend:restart_attempt"
BACKEND_RESTART_EXHAUSTED = "backend:restart_exhausted"
HEARTBEAT_OK = "heartbeat:ok"
HEARTBEAT_MISSED = "heartbeat:missed"
HEARTBEAT_TRANSITION = "heartbeat:transition"
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


EXIT_LOG_PATH = Path.home() / ".eve" / "logs" / "backend_exit.log"


def record_exit(
    *,
    exit_code: int | None = None,
    termination_type: str = "unknown",
    uptime: float = 0.0,
    launcher_pid: int = 0,
    backend_pid: int = 0,
    server_pid: int = 0,
    restart_decision: str = "none",
    restart_count: int = 0,
    reason: str = "",
):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "termination_type": termination_type,
        "uptime": round(uptime, 1),
        "launcher_pid": launcher_pid,
        "backend_pid": backend_pid,
        "server_pid": server_pid,
        "restart_decision": restart_decision,
        "restart_count": restart_count,
        "reason": reason,
    }
    try:
        EXIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EXIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
    return entry
