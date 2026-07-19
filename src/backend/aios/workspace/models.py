"""Workspace Models — strongly typed workspace, project, and environment models."""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


class FrameworkType(str, enum.Enum):
    NEXT_JS = "nextjs"
    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    NODE_JS = "nodejs"
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    PYTHON = "python"
    FLUTTER = "flutter"
    REACT_NATIVE = "react-native"
    DOTNET = "dotnet"
    JAVA = "java"
    RUST = "rust"
    GO = "go"
    UNKNOWN = "unknown"


class AppCategory(str, enum.Enum):
    IDE = "ide"
    TERMINAL = "terminal"
    EDITOR = "editor"
    DB_CLIENT = "db_client"
    API_CLIENT = "api_client"
    BROWSER = "browser"
    COMM_TOOL = "communication"
    DEV_TOOL = "dev_tool"
    UNKNOWN = "unknown"


class GitStatus(str, enum.Enum):
    CLEAN = "clean"
    DIRTY = "dirty"
    AHEAD = "ahead"
    BEHIND = "behind"
    AHEAD_BEHIND = "ahead_behind"
    NO_REPO = "no_repo"


@dataclass
class Application:
    process_name: str = ""
    window_title: str = ""
    executable: str = ""
    pid: int = 0
    category: AppCategory = AppCategory.UNKNOWN
    up: bool = True
    launched_at: datetime = None

    def __post_init__(self):
        if not self.launched_at:
            self.launched_at = datetime.utcnow()


@dataclass
class Project:
    root_path: str = ""
    name: str = ""
    framework: FrameworkType = FrameworkType.UNKNOWN
    language: str = ""
    package_manager: str = ""
    build_command: str = ""
    test_command: str = ""
    run_command: str = ""
    version: str = ""


@dataclass
class Repository:
    provider: str = ""
    branch: str = ""
    remote: str = ""
    modified_files: list = field(default_factory=list)
    staged_files: list = field(default_factory=list)
    untracked_files: list = field(default_factory=list)
    ahead: int = 0
    behind: int = 0
    dirty: bool = False
    last_commit: str = ""
    last_commit_message: str = ""
    status: GitStatus = GitStatus.NO_REPO


@dataclass
class Editor:
    name: str = ""
    workspace: str = ""
    active_file: str = ""
    file_language: str = ""
    pid: int = 0
    process_name: str = ""


@dataclass
class Terminal:
    cwd: str = ""
    shell: str = ""
    pid: int = 0
    process_name: str = ""


@dataclass
class Workspace:
    id: str = ""
    name: str = ""
    path: str = ""
    type: str = ""
    framework: FrameworkType = FrameworkType.UNKNOWN
    language: str = ""
    status: str = "active"
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()


@dataclass
class WorkspaceSnapshot:
    timestamp: datetime = None
    active_window: str = ""
    active_application: Application | None = None
    applications: list = field(default_factory=list)
    projects: list = field(default_factory=list)
    repositories: list = field(default_factory=list)
    editors: list = field(default_factory=list)
    terminals: list = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow()
