"""Tests for Git Toolkit (repository, status, branches, commits, remote, tags)."""

import asyncio
import os
import subprocess
from pathlib import Path

import pytest

from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus
from aios.tools.git_tools import (
    register_git_tools,
    _find_repo,
    _current_repository,
    _repository_info,
    _git_status,
    _staged_files,
    _modified_files,
    _untracked_files,
    _git_diff,
    _list_branches,
    _create_branch,
    _checkout_branch,
    _delete_branch,
    _commit,
    _commit_log,
    _show_commit,
    _amend_last_commit,
    _list_tags,
    _create_tag,
    _checkout_tag,
    _discover_repositories,
)


def _git(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + cmd, cwd=cwd, capture_output=True, text=True, timeout=10)


@pytest.fixture
def git_repo(tmp_path: Path) -> str:
    repo = tmp_path / "test_repo"
    repo.mkdir()
    _git(["init"], str(repo))
    _git(["config", "user.email", "test@test.com"], str(repo))
    _git(["config", "user.name", "Test User"], str(repo))
    (repo / "README.md").write_text("# Test Repo")
    _git(["add", "README.md"], str(repo))
    _git(["commit", "-m", "Initial commit"], str(repo))
    (repo / "src").mkdir()
    (repo / "src" / "main.py").write_text("print('hello')")
    _git(["add", "src/main.py"], str(repo))
    _git(["commit", "-m", "Add main.py"], str(repo))
    (repo / "src" / "utils.py").write_text("def util():\n    pass\n")
    return str(repo)


@pytest.fixture
def non_git_dir(tmp_path: Path) -> str:
    d = tmp_path / "not_a_repo"
    d.mkdir()
    return str(d)


@pytest.fixture
def pm():
    return PermissionManager()


@pytest.fixture
def tm(pm):
    return ToolManager(pm)


@pytest.fixture
async def eb():
    bus = EventBus(max_retries=1, retry_delay=0.01)
    await bus.start()
    yield bus
    await bus.stop()


# ── Repository Tools ──

def test_find_repo(git_repo):
    assert _find_repo(git_repo) == git_repo


def test_find_repo_subdir(git_repo):
    src = os.path.join(git_repo, "src")
    assert _find_repo(src) == git_repo


def test_find_repo_not_found(non_git_dir):
    assert _find_repo(non_git_dir) is None


@pytest.mark.asyncio
async def test_current_repository_found(git_repo):
    result = await _current_repository({"path": git_repo})
    assert result.success
    assert result.data["found"]
    assert result.data["path"] == git_repo


@pytest.mark.asyncio
async def test_current_repository_not_found(non_git_dir):
    result = await _current_repository({"path": non_git_dir})
    assert result.success
    assert not result.data["found"]


@pytest.mark.asyncio
async def test_repository_info(git_repo):
    result = await _repository_info({"path": git_repo})
    assert result.success
    assert result.data["current_branch"] == "main" or result.data["current_branch"] == "master"
    assert result.data["name"] == "test_repo"
    assert "staged_count" in result.data
    assert "total_changes" in result.data


@pytest.mark.asyncio
async def test_repository_info_not_found(non_git_dir):
    result = await _repository_info({"path": non_git_dir})
    assert not result.success


# ── Status Tools ──

@pytest.mark.asyncio
async def test_git_status_clean(git_repo):
    result = await _git_status({"path": git_repo})
    assert result.success
    assert "clean" in result.data
    assert "staged" in result.data
    assert "modified" in result.data


@pytest.mark.asyncio
async def test_git_status_with_changes(git_repo):
    (Path(git_repo) / "new_file.txt").write_text("new content")
    result = await _git_status({"path": git_repo})
    assert result.success
    assert result.data["untracked"] >= 1


@pytest.mark.asyncio
async def test_git_status_not_in_repo(non_git_dir):
    result = await _git_status({"path": non_git_dir})
    assert not result.success


@pytest.mark.asyncio
async def test_staged_files(git_repo):
    repo = Path(git_repo)
    (repo / "new_staged.txt").write_text("staged content")
    _git(["add", "new_staged.txt"], git_repo)
    result = await _staged_files({"path": git_repo})
    assert result.success
    assert result.data["count"] >= 1
    staged_names = [f["file"] for f in result.data["files"]]
    assert "new_staged.txt" in staged_names


@pytest.mark.asyncio
async def test_modified_files(git_repo):
    repo = Path(git_repo)
    (repo / "README.md").write_text("# Modified content")
    result = await _modified_files({"path": git_repo})
    assert result.success
    assert result.data["count"] >= 1


@pytest.mark.asyncio
async def test_untracked_files(git_repo):
    repo = Path(git_repo)
    (repo / "untracked1.txt").write_text("untracked")
    (repo / "untracked2.py").write_text("x = 1")
    result = await _untracked_files({"path": git_repo})
    assert result.success
    assert result.data["count"] >= 2


@pytest.mark.asyncio
async def test_git_diff(git_repo):
    repo = Path(git_repo)
    (repo / "README.md").write_text("# Modified content for diff")
    result = await _git_diff({"path": git_repo})
    assert result.success
    assert result.data["has_changes"]


@pytest.mark.asyncio
async def test_git_diff_staged(git_repo):
    repo = Path(git_repo)
    (repo / "README.md").write_text("# Staged change for diff")
    _git(["add", "README.md"], git_repo)
    result = await _git_diff({"path": git_repo, "staged": True})
    assert result.success
    assert result.data["has_changes"]


# ── Branch Tools ──

@pytest.mark.asyncio
async def test_list_branches(git_repo):
    result = await _list_branches({"path": git_repo})
    assert result.success
    assert result.data["count"] >= 1
    assert any(b["current"] for b in result.data["branches"])


@pytest.mark.asyncio
async def test_create_branch(git_repo):
    result = await _create_branch({"path": git_repo, "name": "feature-test"})
    assert result.success
    assert result.data["created"]

    branches = await _list_branches({"path": git_repo})
    branch_names = [b["name"] for b in branches.data["branches"]]
    assert "feature-test" in branch_names


@pytest.mark.asyncio
async def test_create_branch_no_name(git_repo):
    result = await _create_branch({"path": git_repo, "name": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_checkout_branch(git_repo):
    _git(["branch", "other-branch"], git_repo)
    result = await _checkout_branch({"path": git_repo, "name": "other-branch"})
    assert result.success
    assert result.data["branch"] == "other-branch"


@pytest.mark.asyncio
async def test_checkout_branch_no_name(git_repo):
    result = await _checkout_branch({"path": git_repo, "name": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_delete_branch(git_repo):
    _git(["branch", "to-delete"], git_repo)
    result = await _delete_branch({"path": git_repo, "name": "to-delete"})
    assert result.success
    assert result.data["deleted"]


@pytest.mark.asyncio
async def test_delete_branch_no_name(git_repo):
    result = await _delete_branch({"path": git_repo, "name": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_delete_current_branch_fails(git_repo):
    result = await _delete_branch({"path": git_repo, "name": "main"})
    assert not result.success


# ── Commit Tools ──

@pytest.mark.asyncio
async def test_commit(git_repo):
    repo = Path(git_repo)
    (repo / "new_file.txt").write_text("to commit")
    _git(["add", "new_file.txt"], git_repo)
    result = await _commit({"path": git_repo, "message": "Test commit"})
    assert result.success
    assert result.data["hash"]


@pytest.mark.asyncio
async def test_commit_no_message(git_repo):
    result = await _commit({"path": git_repo, "message": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_commit_log(git_repo):
    result = await _commit_log({"path": git_repo})
    assert result.success
    assert result.data["count"] >= 2


@pytest.mark.asyncio
async def test_commit_log_with_format(git_repo):
    result = await _commit_log({"path": git_repo, "format": "full"})
    assert result.success
    assert len(result.data["commits"]) > 0
    assert "author" in result.data["commits"][0]


@pytest.mark.asyncio
async def test_show_commit(git_repo):
    result = await _show_commit({"path": git_repo, "commit": "HEAD"})
    assert result.success
    assert "details" in result.data
    assert result.data["details"]["hash"]


@pytest.mark.asyncio
async def test_show_commit_invalid_ref(git_repo):
    result = await _show_commit({"path": git_repo, "commit": "NONEXISTENT"})
    assert not result.success


@pytest.mark.asyncio
async def test_amend_last_commit(git_repo):
    result = await _amend_last_commit({"path": git_repo, "message": "Amended message"})
    assert result.success
    assert result.data["amended"]


# ── Tag Tools ──

@pytest.mark.asyncio
async def test_list_tags_empty(git_repo):
    result = await _list_tags({"path": git_repo})
    assert result.success
    assert result.data["count"] == 0


@pytest.mark.asyncio
async def test_create_and_list_tags(git_repo):
    result = await _create_tag({"path": git_repo, "name": "v1.0.0", "message": "Release 1.0"})
    assert result.success
    assert result.data["name"] == "v1.0.0"

    list_result = await _list_tags({"path": git_repo})
    assert list_result.data["count"] >= 1
    tag_names = [t["name"] for t in list_result.data["tags"]]
    assert "v1.0.0" in tag_names


@pytest.mark.asyncio
async def test_create_tag_no_name(git_repo):
    result = await _create_tag({"path": git_repo, "name": ""})
    assert not result.success


# ── Discovery ──

@pytest.mark.asyncio
async def test_discover_repositories(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    subprocess.run(["git", "init"], cwd=str(parent), capture_output=True, timeout=10)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=str(parent), capture_output=True, timeout=10)
    subprocess.run(["git", "config", "user.name", "T"], cwd=str(parent), capture_output=True, timeout=10)

    result = await _discover_repositories({"path": str(tmp_path), "depth": 5})
    assert result.success
    assert result.data["count"] >= 1


# ── Not in repo tests ──

@pytest.mark.asyncio
async def test_all_tools_fail_gracefully_outside_repo(non_git_dir):
    tools = [
        _git_status, _staged_files, _modified_files, _untracked_files,
        _list_branches, _create_branch, _commit_log, _show_commit,
        _list_tags, _create_tag,
    ]
    for tool in tools:
        result = await tool({"path": non_git_dir})
        assert not result.success, f"{tool.__name__} should fail outside repo"


# ── Registration ──

@pytest.mark.asyncio
async def test_register_git_tools(tm, eb):
    register_git_tools(tm, eb)
    await asyncio.sleep(0.05)

    for tid in ["git.status", "git.commit", "git.push", "git.list_tags"]:
        tool = await tm.get_tool(tid)
        assert tool is not None, f"Missing tool: {tid}"


@pytest.mark.asyncio
async def test_register_all_git_tools(tm, eb):
    register_git_tools(tm, eb)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    tool_ids = {t.id for t in all_tools}

    expected = {
        "git.discover_repositories", "git.current_repository", "git.repository_info",
        "git.status", "git.staged_files", "git.modified_files", "git.untracked_files", "git.diff",
        "git.list_branches", "git.create_branch", "git.checkout_branch", "git.delete_branch",
        "git.commit", "git.commit_log", "git.show_commit", "git.amend_last_commit",
        "git.fetch", "git.pull", "git.push",
        "git.list_tags", "git.create_tag", "git.checkout_tag",
        "git.cancel_operation",
    }
    missing = expected - tool_ids
    assert not missing, f"Missing tools: {missing}"


@pytest.mark.asyncio
async def test_git_tools_have_git_category(tm, eb):
    register_git_tools(tm, eb)
    await asyncio.sleep(0.05)
    git_tools = await tm.list_tools("git")
    assert len(git_tools) > 0
    for t in git_tools:
        assert t.category == "git"
