import pytest
from aios.workspace.models import (
    Workspace, Application, Project, Repository, Editor, Terminal,
    WorkspaceSnapshot, FrameworkType, AppCategory, GitStatus,
)


def test_workspace_defaults():
    ws = Workspace(name="test")
    assert ws.id
    assert ws.name == "test"
    assert ws.framework == FrameworkType.UNKNOWN
    assert ws.status == "active"
    assert ws.created_at is not None


def test_application_defaults():
    app = Application(process_name="code.exe", pid=1234)
    assert app.process_name == "code.exe"
    assert app.pid == 1234
    assert app.category == AppCategory.UNKNOWN
    assert app.launched_at is not None


def test_project_defaults():
    p = Project(root_path="/test", name="myproject")
    assert p.root_path == "/test"
    assert p.framework == FrameworkType.UNKNOWN
    assert p.build_command == ""
    assert p.test_command == ""


def test_repository_defaults():
    r = Repository(branch="main", remote="origin")
    assert r.branch == "main"
    assert r.status == GitStatus.NO_REPO
    assert r.modified_files == []
    assert r.ahead == 0


def test_editor_defaults():
    e = Editor(name="VS Code", active_file="main.py")
    assert e.name == "VS Code"
    assert e.active_file == "main.py"
    assert e.file_language == ""


def test_terminal_defaults():
    t = Terminal(cwd="/home", shell="bash")
    assert t.cwd == "/home"
    assert t.shell == "bash"


def test_workspace_snapshot():
    s = WorkspaceSnapshot(active_window="Test Window")
    assert s.active_window == "Test Window"
    assert s.timestamp is not None
    assert s.applications == []
    assert s.projects == []
    assert s.repositories == []


def test_framework_types():
    assert FrameworkType.NEXT_JS.value == "nextjs"
    assert FrameworkType.REACT.value == "react"
    assert FrameworkType.PYTHON.value == "python"
    assert FrameworkType.RUST.value == "rust"
    assert FrameworkType.GO.value == "go"


def test_app_categories():
    assert AppCategory.IDE.value == "ide"
    assert AppCategory.TERMINAL.value == "terminal"
    assert AppCategory.BROWSER.value == "browser"


def test_git_statuses():
    assert GitStatus.CLEAN.value == "clean"
    assert GitStatus.DIRTY.value == "dirty"
    assert GitStatus.NO_REPO.value == "no_repo"
