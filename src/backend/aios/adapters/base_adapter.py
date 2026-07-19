"""Abstract base for OS adapters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class FileInfo:
    path: str
    name: str
    size: int
    is_dir: bool
    modified: str


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float


@dataclass
class SystemInfo:
    os: str
    os_version: str
    cpu: str
    cpu_percent: float
    ram_total_gb: float
    ram_used_gb: float
    ram_percent: float


@dataclass
class WindowInfo:
    title: str
    app: str
    x: int
    y: int
    width: int
    height: int


class BaseAdapter(ABC):
    @abstractmethod
    async def search_files(self, pattern: str, path: str | None = None) -> list[FileInfo]:
        ...

    @abstractmethod
    async def read_file(self, path: str) -> str:
        ...

    @abstractmethod
    async def write_file(self, path: str, content: str) -> None:
        ...

    @abstractmethod
    async def delete_file(self, path: str) -> None:
        ...

    @abstractmethod
    async def create_directory(self, path: str) -> None:
        ...

    @abstractmethod
    async def list_processes(self) -> list[ProcessInfo]:
        ...

    @abstractmethod
    async def start_process(self, command: str) -> int:
        ...

    @abstractmethod
    async def kill_process(self, pid: int) -> None:
        ...

    @abstractmethod
    async def get_system_info(self) -> SystemInfo:
        ...

    @abstractmethod
    async def get_active_window(self) -> WindowInfo:
        ...

    @abstractmethod
    async def get_screenshot(self) -> bytes:
        ...
