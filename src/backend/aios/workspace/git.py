"""Git Intelligence — read-only Git repository awareness."""

import os
from typing import Any
from aios.workspace.models import Repository, GitStatus
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class GitCollector:
    async def collect(self, path: str) -> Repository | None:
        git_dir = self._find_git_root(path)
        if not git_dir:
            return None
        repo = Repository()
        try:
            repo = await self._collect_basic(git_dir)
            repo = await self._collect_branch(git_dir, repo)
            repo = await self._collect_status(git_dir, repo)
            repo = await self._collect_remote(git_dir, repo)
            repo = await self._collect_commits(git_dir, repo)
        except Exception as e:
            logger.error("git.collect.failed", path=path, error=str(e))
        return repo

    def _find_git_root(self, path: str) -> str | None:
        path = os.path.abspath(path)
        while True:
            if os.path.exists(os.path.join(path, ".git")):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                return None
            path = parent

    async def _collect_basic(self, git_root: str) -> Repository:
        repo = Repository()
        try:
            remote = await self._run_git(git_root, "remote get-url origin")
            repo.remote = remote.strip() if remote else ""
            repo.provider = self._detect_provider(repo.remote)
        except Exception:
            pass
        return repo

    async def _collect_branch(self, git_root: str, repo: Repository) -> Repository:
        try:
            branch = await self._run_git(git_root, "rev-parse --abbrev-ref HEAD")
            repo.branch = branch.strip() if branch else "unknown"
        except Exception:
            repo.branch = "unknown"
        return repo

    async def _collect_status(self, git_root: str, repo: Repository) -> Repository:
        try:
            status = await self._run_git(git_root, "status --porcelain")
            if status:
                lines = status.strip().split("\n")
                modified = []
                staged = []
                untracked = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("??"):
                        untracked.append(line[2:].strip())
                    elif line.startswith(" "):
                        modified.append(line[1:].strip())
                    elif line.startswith("M"):
                        staged.append(line[1:].strip())
                    elif line.startswith("A"):
                        staged.append(line[1:].strip())
                    elif line.startswith("D"):
                        pass
                    else:
                        modified.append(line[1:].strip())
                repo.modified_files = modified
                repo.staged_files = staged
                repo.untracked_files = untracked
                repo.dirty = bool(status.strip())
                repo.status = GitStatus.DIRTY if repo.dirty else GitStatus.CLEAN
        except Exception:
            pass
        return repo

    async def _collect_remote(self, git_root: str, repo: Repository) -> Repository:
        try:
            ahead_behind = await self._run_git(git_root, "rev-list --count --left-right HEAD...@{u}")
            if ahead_behind:
                parts = ahead_behind.strip().split()
                if len(parts) == 2:
                    repo.ahead = int(parts[0])
                    repo.behind = int(parts[1])
                    if repo.ahead > 0 and repo.behind > 0:
                        repo.status = GitStatus.AHEAD_BEHIND
                    elif repo.ahead > 0:
                        repo.status = GitStatus.AHEAD
                    elif repo.behind > 0:
                        repo.status = GitStatus.BEHIND
        except Exception:
            pass
        return repo

    async def _collect_commits(self, git_root: str, repo: Repository) -> Repository:
        try:
            log = await self._run_git(git_root, "log -1 --format=%H%n%s")
            if log:
                lines = log.strip().split("\n", 1)
                repo.last_commit = lines[0].strip()
                repo.last_commit_message = lines[1].strip() if len(lines) > 1 else ""
        except Exception:
            pass
        return repo

    def _detect_provider(self, remote: str) -> str:
        if not remote:
            return "local"
        if "github.com" in remote:
            return "github"
        if "gitlab.com" in remote:
            return "gitlab"
        if "bitbucket.org" in remote:
            return "bitbucket"
        if "dev.azure.com" in remote or "visualstudio.com" in remote:
            return "azure-devops"
        return "other"

    async def _run_git(self, cwd: str, args: str) -> str:
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            "git", *args.split(),
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return ""
        return stdout.decode("utf-8", errors="replace")
