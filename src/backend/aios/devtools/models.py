from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_int(cls, level: int) -> "LogLevel":
        if level >= 50:
            return cls.CRITICAL
        if level >= 40:
            return cls.ERROR
        if level >= 30:
            return cls.WARNING
        if level >= 20:
            return cls.INFO
        return cls.DEBUG


@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    message: str
    source: str = ""
    category: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class HealthStatus:
    component: str
    healthy: bool
    status: str = ""
    metrics: dict = field(default_factory=dict)
    last_checked: datetime = field(default_factory=datetime.utcnow)
    error: str = ""


@dataclass
class ModuleInfo:
    name: str
    file: str
    size: int = 0
    exports: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    is_package: bool = False
    docstring: str = ""
    source_lines: int = 0


@dataclass
class MetricPoint:
    timestamp: datetime
    name: str
    value: float
    labels: dict = field(default_factory=dict)


@dataclass
class DiagnosticCheck:
    name: str
    status: str = "pending"
    passed: bool = False
    detail: str = ""
    duration_ms: float = 0.0
    error: str = ""


@dataclass
class DiagnosticResult:
    id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    checks: list[DiagnosticCheck] = field(default_factory=list)
    summary: str = ""
    all_passed: bool = False


@dataclass
class DebugResult:
    output: str = ""
    error: str = ""
    result: Any = None
    duration_ms: float = 0.0
    variables: dict = field(default_factory=dict)


@dataclass
class WatchedModule:
    name: str
    file_path: str
    last_mtime: float = 0.0
    auto_reload: bool = True
