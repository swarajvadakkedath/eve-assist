import pytest
import tempfile
import os
from aios.workspace.git import GitCollector


@pytest.fixture
def collector():
    return GitCollector()


def test_find_git_root(collector):
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = os.path.join(tmpdir, ".git")
        os.makedirs(git_dir)
        subdir = os.path.join(tmpdir, "sub", "dir")
        os.makedirs(subdir)
        root = collector._find_git_root(subdir)
        assert root == tmpdir


def test_find_git_root_none(collector):
    with tempfile.TemporaryDirectory() as tmpdir:
        root = collector._find_git_root(tmpdir)
        assert root is None


def test_detect_provider(collector):
    assert collector._detect_provider("git@github.com:user/repo.git") == "github"
    assert collector._detect_provider("https://gitlab.com/user/repo.git") == "gitlab"
    assert collector._detect_provider("") == "local"
    assert collector._detect_provider("https://dev.azure.com/project") == "azure-devops"
    assert collector._detect_provider("git@other.com:repo.git") == "other"


@pytest.mark.asyncio
async def test_run_git(collector):
    result = await collector._run_git(os.getcwd(), "version")
    assert "git version" in result


@pytest.mark.asyncio
async def test_collect_no_git(collector):
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = await collector.collect(tmpdir)
        assert repo is None


def test_git_status_parsing():
    pass
