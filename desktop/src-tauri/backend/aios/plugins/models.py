"""Plugin data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from aios.plugins.manifest import PluginManifest


class PluginStatus(str, Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    VERIFIED = "verified"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    STOPPED = "stopped"
    DISABLED = "disabled"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNLOADED = "unloaded"
    REMOVED = "removed"


class PluginScope(str, Enum):
    BUILTIN = "builtin"
    USER = "user"
    SYSTEM = "system"
    MARKETPLACE = "marketplace"


class PluginHealthStatus(str, Enum):
    ALIVE = "alive"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    FAILED = "failed"
    STOPPED = "stopped"


class IsolationStrategy(str, Enum):
    IN_PROCESS = "in_process"
    SUBPROCESS = "subprocess"
    VIRTUAL_ENV = "virtual_env"
    DOCKER = "docker"
    REMOTE = "remote"


@dataclass
class PluginMetadata:
    id: str = ""
    name: str = ""
    version: str = ""
    author: str = ""
    description: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    platforms: list[str] = field(default_factory=lambda: ["windows"])
    tags: list[str] = field(default_factory=list)
    category: str = "general"
    icon: str = ""
    documentation: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class PluginCapability:
    id: str
    name: str
    description: str = ""
    permission_level: int = 1
    timeout: int = 30
    parameters: dict = field(default_factory=dict)
    returns: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class PluginPermission:
    permission: str
    level: int = 1
    reason: str = ""
    granted: bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class PluginDependency:
    plugin_id: str
    version_spec: str = ""
    optional: bool = False
    resolved: bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class PluginHealth:
    status: PluginHealthStatus = PluginHealthStatus.STARTING
    startup_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    error_count: int = 0
    restart_count: int = 0
    last_error: str = ""
    last_heartbeat: datetime | None = None
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "startup_time_ms": self.startup_time_ms,
            "memory_usage_mb": self.memory_usage_mb,
            "error_count": self.error_count,
            "restart_count": self.restart_count,
            "last_error": self.last_error,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "uptime_seconds": self.uptime_seconds,
        }


@dataclass
class PluginContext:
    plugin_id: str
    manifest: PluginManifest | None = None
    config: dict = field(default_factory=dict)
    logger: Any = None
    event_bus: Any = None
    permission_manager: Any = None


@dataclass
class PluginConfiguration:
    plugin_id: str
    settings: dict = field(default_factory=dict)
    enabled: bool = True
    auto_start: bool = True
    isolation: IsolationStrategy = IsolationStrategy.IN_PROCESS

    def to_dict(self) -> dict:
        return {
            "plugin_id": self.plugin_id,
            "settings": self.settings,
            "enabled": self.enabled,
            "auto_start": self.auto_start,
            "isolation": self.isolation.value,
        }


@dataclass
class PluginState:
    status: PluginStatus = PluginStatus.DISCOVERED
    health: PluginHealth = field(default_factory=PluginHealth)
    configuration: PluginConfiguration | None = None
    error: str | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "health": self.health.to_dict(),
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
        }


@dataclass
class PluginResult:
    success: bool
    data: Any = None
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class PluginVersion:
    plugin_id: str
    version: str
    sdk_version: str
    installed_at: datetime | None = None
    checksum: str = ""
    release_notes: str = ""


@dataclass
class Plugin:
    id: str = ""
    manifest: PluginManifest | None = None
    state: PluginState = field(default_factory=PluginState)
    scope: PluginScope = PluginScope.USER
    source: str = ""
    instance: Any = None
    capabilities: list[PluginCapability] = field(default_factory=list)
    dependencies: list[PluginDependency] = field(default_factory=list)
    metadata: PluginMetadata = field(default_factory=PluginMetadata)

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex

    @property
    def status(self) -> PluginStatus:
        return self.state.status

    @property
    def health(self) -> PluginHealth:
        return self.state.health

    @property
    def is_active(self) -> bool:
        return self.state.status == PluginStatus.ACTIVE

    @property
    def is_failed(self) -> bool:
        return self.state.status == PluginStatus.FAILED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scope": self.scope.value,
            "source": self.source,
            "state": self.state.to_dict(),
            "metadata": self.metadata.to_dict() if self.metadata else {},
            "capabilities": [c.to_dict() for c in self.capabilities],
            "dependencies": [d.to_dict() for d in self.dependencies],
        }
