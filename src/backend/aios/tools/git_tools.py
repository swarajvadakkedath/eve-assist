"""Git Toolkit — Repository, Status, Branches, Commits, Remote, Tags for AIOS Phase 5.3."""

import asyncio
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios.core.tool_manager import ToolResult
from aios.core.event_bus import EventBus

_running_operations: dict[str, dict[str, Any]] = {}
_op_counter = 0


def _next_op_id() -> str:
    global _op_counter
    _op_counter += 1
    return f"git_{_op_counter}_{datetime.utcnow().timestamp()}"


def _find_repo(path: str | None = None) -> str | None:
    start = Path(path or os.getcwd()).resolve()
    for parent in [start] + list(start.parents):
        git_dir = parent / ".git"
        if git_dir.exists() and git_dir.is_dir():
            return str(parent)
    return None


def _parse_git_status_line(line: str) -> dict:
    if len(line) < 3:
        return {}
    index_status = line[0]
    working_status = line[1]
    file_path = line[3:].strip()
    return {
        "index_status": index_status,
        "working_status": working_status,
        "file": file_path,
        "staged": index_status != " ",
        "modified": working_status != " ",
    }


async def _run_git(args: list[str], cwd: str | None = None, timeout: int = 30) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {"success": False, "error": f"Git command timed out after {timeout}s", "exit_code": -1}
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    return {
        "success": proc.returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": proc.returncode,
    }


async def _run_git_streaming(
    args: list[str], cwd: str | None = None,
    event_bus: EventBus | None = None, op_id: str | None = None,
    timeout: int = 300,
) -> dict:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    if op_id:
        _running_operations[op_id] = {"proc": proc, "args": args, "started_at": datetime.utcnow(), "status": "running"}

    async def _read_stream(stream, stream_name: str):
        chunks = []
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            chunks.append(text)
            if event_bus and op_id:
                await event_bus.publish(
                    "git:stream:output",
                    {"op_id": op_id, "stream": stream_name, "data": text},
                    source="git_tools",
                )
        return "".join(chunks)

    stdout_task = asyncio.create_task(_read_stream(proc.stdout, "stdout"))
    stderr_task = asyncio.create_task(_read_stream(proc.stderr, "stderr"))

    try:
        exit_code = await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        await stdout_task
        await stderr_task
        if op_id:
            _running_operations[op_id]["status"] = "timeout"
        return {"success": False, "error": f"Git operation timed out after {timeout}s", "exit_code": -1}
    except asyncio.CancelledError:
        proc.kill()
        await proc.wait()
        await stdout_task
        await stderr_task
        if op_id:
            _running_operations[op_id]["status"] = "cancelled"
        return {"success": False, "error": "Git operation cancelled", "exit_code": -1}

    stdout_text = await stdout_task
    stderr_text = await stderr_task

    if op_id:
        _running_operations[op_id]["status"] = "completed" if exit_code == 0 else "failed"
        _running_operations[op_id]["exit_code"] = exit_code

    return {"success": exit_code == 0, "stdout": stdout_text, "stderr": stderr_text, "exit_code": exit_code}


def _ensure_repo(path: str | None) -> str | None:
    repo = _find_repo(path)
    if not repo:
        return None
    return repo


# ── Repository Tools ──


async def _discover_repositories(params: dict) -> ToolResult:
    try:
        root = params.get("path", os.getcwd())
        depth = params.get("depth", 3)
        repos = []
        base = Path(root).resolve()
        if not base.exists():
            return ToolResult(success=False, error=f"Path not found: {root}")

        for i, entry in enumerate(base.rglob(".git")):
            if i >= depth:
                break
            repo_path = str(entry.parent)
            result = await _run_git(["rev-parse", "--git-dir"], cwd=repo_path)
            if result["success"]:
                remotes_result = await _run_git(["remote", "-v"], cwd=repo_path)
                remote_info = {}
                for line in remotes_result["stdout"].splitlines():
                    parts = line.split()
                    if len(parts) >= 3:
                        remote_info[parts[0]] = parts[1]
                repos.append({
                    "path": repo_path,
                    "remotes": remote_info,
                    "has_remote": len(remote_info) > 0,
                })
        return ToolResult(success=True, data={
            "repositories": repos, "count": len(repos), "root": str(base),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _current_repository(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=True, data={"found": False, "message": "Not in a Git repository"})

        return ToolResult(success=True, data={
            "found": True,
            "path": repo,
            "name": Path(repo).name,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _repository_info(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        branch_result = await _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
        hash_result = await _run_git(["rev-parse", "HEAD"], cwd=repo)
        remotes_result = await _run_git(["remote", "-v"], cwd=repo)
        tags_result = await _run_git(["tag", "--list"], cwd=repo)
        log_result = await _run_git(["log", "--oneline", "-5"], cwd=repo)
        status_result = await _run_git(["status", "--porcelain"], cwd=repo)

        remotes = {}
        for line in remotes_result["stdout"].splitlines():
            parts = line.split()
            if len(parts) >= 3:
                remotes[parts[0]] = {"url": parts[1], "type": parts[2].strip("()")}

        branch = branch_result["stdout"].strip() if branch_result["success"] else "HEAD"
        commits = [line.strip() for line in log_result["stdout"].splitlines() if line.strip()] if log_result["success"] else []
        status_lines = [line.strip() for line in status_result["stdout"].splitlines() if line.strip()]

        staged = sum(1 for l in status_lines if len(l) > 2 and l[0] != " ")
        modified = sum(1 for l in status_lines if len(l) > 2 and l[1] != " ")

        return ToolResult(success=True, data={
            "path": repo,
            "name": Path(repo).name,
            "current_branch": branch,
            "head_hash": hash_result["stdout"].strip() if hash_result["success"] else None,
            "remotes": remotes,
            "has_remote": len(remotes) > 0,
            "tags": [t.strip() for t in tags_result["stdout"].splitlines() if t.strip()] if tags_result["success"] else [],
            "recent_commits": commits,
            "staged_count": staged,
            "modified_count": modified,
            "total_changes": len(status_lines),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Status Tools ──


async def _git_status(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        result = await _run_git(["status", "--porcelain"], cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        lines = [line for line in result["stdout"].splitlines() if line.strip()]
        entries = [_parse_git_status_line(line) for line in lines]

        branch_result = await _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
        branch = branch_result["stdout"].strip() if branch_result["success"] else "HEAD"

        ahead_result = await _run_git(["rev-list", "--count", "@{upstream}..HEAD"], cwd=repo)
        behind_result = await _run_git(["rev-list", "--count", "HEAD..@{upstream}"], cwd=repo)
        ahead = int(ahead_result["stdout"].strip()) if ahead_result["success"] else 0
        behind = int(behind_result["stdout"].strip()) if behind_result["success"] else 0

        return ToolResult(success=True, data={
            "branch": branch,
            "entries": entries,
            "staged": sum(1 for e in entries if e.get("staged")),
            "modified": sum(1 for e in entries if e.get("modified")),
            "untracked": sum(1 for e in entries if e.get("index_status") == "?"),
            "total": len(entries),
            "ahead": ahead,
            "behind": behind,
            "clean": len(entries) == 0,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _staged_files(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        result = await _run_git(["diff", "--cached", "--name-status"], cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        files = []
        for line in result["stdout"].splitlines():
            if line.strip():
                parts = line.split("\t", 1)
                files.append({
                    "status": parts[0] if len(parts) > 0 else "",
                    "file": parts[1] if len(parts) > 1 else "",
                })

        return ToolResult(success=True, data={
            "files": files, "count": len(files),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _modified_files(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        result = await _run_git(["diff", "--name-status"], cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        files = []
        for line in result["stdout"].splitlines():
            if line.strip():
                parts = line.split("\t", 1)
                files.append({
                    "status": parts[0] if len(parts) > 0 else "",
                    "file": parts[1] if len(parts) > 1 else "",
                })

        return ToolResult(success=True, data={
            "files": files, "count": len(files),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _untracked_files(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        result = await _run_git(["ls-files", "--others", "--exclude-standard"], cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        files = [f.strip() for f in result["stdout"].splitlines() if f.strip()]
        return ToolResult(success=True, data={
            "files": files, "count": len(files),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _git_diff(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        staged = params.get("staged", False)
        file_path = params.get("file")
        context_lines = params.get("context_lines", 3)

        args = ["diff", f"-U{context_lines}"]
        if staged:
            args.append("--cached")
        if file_path:
            args.append(file_path)

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(success=True, data={
            "diff": result["stdout"],
            "staged": staged,
            "file": file_path,
            "has_changes": bool(result["stdout"].strip()),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Branch Tools ──


async def _list_branches(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        all_branches = params.get("all", False)
        args = ["branch"]
        if all_branches:
            args.append("-a")
        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        branches = []
        for line in result["stdout"].splitlines():
            if line.strip():
                is_current = line.startswith("*")
                name = line[2:].strip() if is_current else line.strip()
                branches.append({
                    "name": name,
                    "current": is_current,
                    "remote": "/" in name,
                })

        return ToolResult(success=True, data={
            "branches": branches, "count": len(branches),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _create_branch(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        branch_name = params.get("name", "")
        base = params.get("base", "")
        if not branch_name:
            return ToolResult(success=False, error="No branch name provided")

        args = ["branch", branch_name]
        if base:
            args.append(base)

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(success=True, data={
            "name": branch_name, "base": base or "HEAD", "created": True,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _checkout_branch(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        branch_name = params.get("name", "")
        create_new = params.get("create_new", False)

        if not branch_name:
            return ToolResult(success=False, error="No branch name provided")

        args = ["checkout"]
        if create_new:
            args.extend(["-b"])
        args.append(branch_name)

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        if event_bus:
            await event_bus.publish(
                "git:checkout",
                {"branch": branch_name, "created_new": create_new, "repo": repo},
                source="git_tools",
            )

        return ToolResult(success=True, data={
            "branch": branch_name, "created_new": create_new,
            "message": result["stdout"].strip(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _delete_branch(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        branch_name = params.get("name", "")
        force = params.get("force", False)

        if not branch_name:
            return ToolResult(success=False, error="No branch name provided")

        current_result = await _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
        current_branch = current_result["stdout"].strip()
        if branch_name == current_branch:
            return ToolResult(success=False, error=f"Cannot delete current branch: {branch_name}")

        args = ["branch", "-D" if force else "-d", branch_name]
        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        if event_bus:
            await event_bus.publish(
                "git:delete_branch",
                {"branch": branch_name, "force": force, "repo": repo},
                source="git_tools",
            )

        return ToolResult(success=True, data={
            "branch": branch_name, "deleted": True, "force": force,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Commit Tools ──


async def _commit(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        message = params.get("message", "")
        all_files = params.get("all", False)
        amend = params.get("amend", False)

        if not message and not amend:
            return ToolResult(success=False, error="No commit message provided")

        args = ["commit"]
        if all_files:
            args.append("-a")
        if amend:
            args.append("--amend")
        args.extend(["-m", message])

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        hash_result = await _run_git(["rev-parse", "HEAD"], cwd=repo)
        commit_hash = hash_result["stdout"].strip() if hash_result["success"] else ""

        if event_bus:
            await event_bus.publish(
                "git:commit",
                {"hash": commit_hash, "message": message, "amend": amend, "repo": repo},
                source="git_tools",
            )

        return ToolResult(success=True, data={
            "hash": commit_hash,
            "message": message,
            "amend": amend,
            "output": result["stdout"].strip(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _commit_log(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        max_count = params.get("max_count", 20)
        branch = params.get("branch", "")
        format_str = params.get("format", "hash")

        formats = {
            "hash": "%H",
            "short": "%h",
            "full": "%H|%an|%ae|%ad|%s",
            "reference": "%h|%an|%s",
        }
        fmt = formats.get(format_str, formats["reference"])

        args = ["log", f"--max-count={max_count}", f"--format={fmt}", "--date=iso-strict"]
        if branch:
            args.append(branch)

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        commits = []
        for line in result["stdout"].splitlines():
            if line.strip():
                if format_str in ("hash", "short"):
                    commits.append({"hash": line.strip()})
                else:
                    parts = line.split("|", 4)
                    entry = {"hash": parts[0] if len(parts) > 0 else ""}
                    if len(parts) > 1:
                        entry["author"] = parts[1]
                    if len(parts) > 2:
                        entry["email"] = parts[2]
                    if len(parts) > 3:
                        entry["date"] = parts[3]
                    if len(parts) > 4:
                        entry["message"] = parts[4]
                    commits.append(entry)

        return ToolResult(success=True, data={
            "commits": commits, "count": len(commits),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _show_commit(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        commit_ref = params.get("commit", "HEAD")
        stat = params.get("stat", True)

        args = ["show", commit_ref]
        if stat:
            args.append("--stat")

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        log_result = await _run_git(["log", "-1", f"--format=%H|%an|%ae|%ad|%s|%P", "--date=iso-strict", commit_ref], cwd=repo)
        details = {}
        if log_result["success"]:
            parts = log_result["stdout"].strip().split("|", 5)
            details = {
                "hash": parts[0] if len(parts) > 0 else "",
                "author": parts[1] if len(parts) > 1 else "",
                "email": parts[2] if len(parts) > 2 else "",
                "date": parts[3] if len(parts) > 3 else "",
                "message": parts[4] if len(parts) > 4 else "",
                "parents": parts[5].split() if len(parts) > 5 and parts[5] else [],
            }

        return ToolResult(success=True, data={
            "commit": commit_ref,
            "details": details,
            "output": result["stdout"],
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _amend_last_commit(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        message = params.get("message", "")
        no_edit = params.get("no_edit", False)

        args = ["commit", "--amend"]
        if no_edit:
            args.append("--no-edit")
        elif message:
            args.extend(["-m", message])
        else:
            return ToolResult(success=False, error="Provide message or use no_edit")

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        hash_result = await _run_git(["rev-parse", "HEAD"], cwd=repo)
        commit_hash = hash_result["stdout"].strip() if hash_result["success"] else ""

        if event_bus:
            await event_bus.publish(
                "git:amend",
                {"hash": commit_hash, "no_edit": no_edit, "repo": repo},
                source="git_tools",
            )

        return ToolResult(success=True, data={
            "hash": commit_hash, "amended": True, "no_edit": no_edit,
            "output": result["stdout"].strip(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Remote Tools ──


async def _fetch(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        remote = params.get("remote", "origin")
        prune = params.get("prune", False)

        args = ["fetch", remote]
        if prune:
            args.append("--prune")

        op_id = _next_op_id()
        if event_bus:
            await event_bus.publish(
                "git:fetch:started",
                {"op_id": op_id, "remote": remote, "repo": repo},
                source="git_tools",
            )

        result = await _run_git_streaming(args, cwd=repo, event_bus=event_bus, op_id=op_id, timeout=300)

        if event_bus:
            await event_bus.publish(
                "git:fetch:completed" if result["success"] else "git:fetch:failed",
                {"op_id": op_id, "remote": remote},
                source="git_tools",
            )

        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(success=True, data={
            "remote": remote, "output": result["stdout"].strip(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _pull(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        remote = params.get("remote", "")
        branch = params.get("branch", "")
        rebase = params.get("rebase", False)

        args = ["pull"]
        if rebase:
            args.append("--rebase")
        if remote:
            args.append(remote)
        if branch:
            args.append(branch)

        op_id = _next_op_id()
        if event_bus:
            await event_bus.publish(
                "git:pull:started",
                {"op_id": op_id, "remote": remote or "default", "branch": branch or "current", "repo": repo},
                source="git_tools",
            )

        result = await _run_git_streaming(args, cwd=repo, event_bus=event_bus, op_id=op_id, timeout=300)

        if event_bus:
            await event_bus.publish(
                "git:pull:completed" if result["success"] else "git:pull:failed",
                {"op_id": op_id, "remote": remote or "default", "branch": branch or "current"},
                source="git_tools",
            )

        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(success=True, data={
            "remote": remote or "origin", "branch": branch or "current",
            "output": result["stdout"].strip(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _push(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        remote = params.get("remote", "origin")
        branch = params.get("branch", "")
        force = params.get("force", False)
        set_upstream = params.get("set_upstream", False)

        args = ["push"]
        if force:
            args.append("--force")
        if set_upstream:
            args.append("-u")
        args.append(remote)
        if branch:
            args.append(branch)

        op_id = _next_op_id()
        if event_bus:
            await event_bus.publish(
                "git:push:started",
                {"op_id": op_id, "remote": remote, "branch": branch or "current", "force": force, "repo": repo},
                source="git_tools",
            )

        result = await _run_git_streaming(args, cwd=repo, event_bus=event_bus, op_id=op_id, timeout=300)

        if event_bus:
            await event_bus.publish(
                "git:push:completed" if result["success"] else "git:push:failed",
                {"op_id": op_id, "remote": remote, "branch": branch or "current"},
                source="git_tools",
            )

        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(success=True, data={
            "remote": remote, "branch": branch or "current",
            "output": result["stdout"].strip(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Tag Tools ──


async def _list_tags(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        result = await _run_git(["tag", "--list", "--sort=-creatordate"], cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        tags = []
        for tag_name in result["stdout"].splitlines():
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            annot_result = await _run_git(["tag", "-l", f"--format=%(objecttype)|%(subject)", tag_name], cwd=repo)
            tag_type = "annotated" if "tag|" in annot_result.get("stdout", "") else "lightweight"
            tags.append({"name": tag_name, "type": tag_type})

        return ToolResult(success=True, data={
            "tags": tags, "count": len(tags),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _create_tag(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        tag_name = params.get("name", "")
        message = params.get("message", "")
        target = params.get("target", "HEAD")

        if not tag_name:
            return ToolResult(success=False, error="No tag name provided")

        args = ["tag"]
        if message:
            args.extend(["-a", tag_name, "-m", message])
        else:
            args.append(tag_name)
        if target != "HEAD":
            args.append(target)

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(success=True, data={
            "name": tag_name, "annotated": bool(message),
            "target": target,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _checkout_tag(params: dict) -> ToolResult:
    try:
        path = params.get("path")
        repo = _ensure_repo(path)
        if not repo:
            return ToolResult(success=False, error="Not in a Git repository")

        tag_name = params.get("name", "")
        if not tag_name:
            return ToolResult(success=False, error="No tag name provided")

        create_branch = params.get("create_branch", "")
        args = ["checkout", "tags/" + tag_name]
        if create_branch:
            args = ["checkout", "-b", create_branch, "tags/" + tag_name]

        result = await _run_git(args, cwd=repo)
        if not result["success"]:
            return ToolResult(success=False, error=result["stderr"])

        return ToolResult(success=True, data={
            "tag": tag_name,
            "branch": create_branch or "detached HEAD",
            "message": result["stdout"].strip(),
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Operation Management ──


async def _cancel_git_operation(params: dict) -> ToolResult:
    try:
        op_id = params.get("op_id", "")
        if not op_id:
            # Cancel all running
            cancelled = []
            for oid, entry in list(_running_operations.items()):
                proc = entry.get("proc")
                if proc and proc.returncode is None:
                    proc.kill()
                    entry["status"] = "cancelled"
                    cancelled.append(oid)
            return ToolResult(success=True, data={"cancelled": cancelled, "count": len(cancelled)})

        entry = _running_operations.get(op_id)
        if not entry:
            return ToolResult(success=False, error=f"Operation not found: {op_id}")

        proc = entry.get("proc")
        if not proc or proc.returncode is not None:
            entry["status"] = "already_completed"
            return ToolResult(success=True, data={"op_id": op_id, "status": "already_completed"})

        proc.kill()
        entry["status"] = "cancelled"
        return ToolResult(success=True, data={"op_id": op_id, "status": "cancelled"})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Registration ──

def register_git_tools(tm, event_bus=None):
    import asyncio
    from aios.core.tool_manager import ToolContract
    from aios.core.permission_manager import PermissionLevel

    repo_tools = [
        ToolContract(
            id="git.discover_repositories", name="Discover Repositories",
            description="Find Git repositories in a directory tree",
            parameters={
                "path": {"type": "string", "description": "Root path to search", "default": "."},
                "depth": {"type": "integer", "description": "Max repositories to find", "default": 3},
            },
            returns={"repositories": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.discover_repositories"], tags=["git", "discover", "repository"],
        ),
        ToolContract(
            id="git.current_repository", name="Current Repository",
            description="Detect the current Git repository from working directory",
            parameters={
                "path": {"type": "string", "description": "Directory to check", "required": False},
            },
            returns={"found": {"type": "boolean"}, "path": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.current_repository"], tags=["git", "current", "repository"],
        ),
        ToolContract(
            id="git.repository_info", name="Repository Info",
            description="Get detailed info about the current repository",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
            },
            returns={"name": {"type": "string"}, "current_branch": {"type": "string"}, "remotes": {"type": "object"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.repository_info"], tags=["git", "info", "repository"],
        ),
    ]

    status_tools = [
        ToolContract(
            id="git.status", name="Git Status",
            description="Show the working tree status with staged/modified/untracked counts",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
            },
            returns={"branch": {"type": "string"}, "staged": {"type": "integer"}, "modified": {"type": "integer"}, "clean": {"type": "boolean"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.status"], tags=["git", "status"],
        ),
        ToolContract(
            id="git.staged_files", name="Staged Files",
            description="List staged files with their status",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
            },
            returns={"files": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.staged_files"], tags=["git", "staged"],
        ),
        ToolContract(
            id="git.modified_files", name="Modified Files",
            description="List modified (unstaged) files",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
            },
            returns={"files": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.modified_files"], tags=["git", "modified"],
        ),
        ToolContract(
            id="git.untracked_files", name="Untracked Files",
            description="List untracked files",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
            },
            returns={"files": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.untracked_files"], tags=["git", "untracked"],
        ),
        ToolContract(
            id="git.diff", name="Git Diff",
            description="Show diff for staged or unstaged changes",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "staged": {"type": "boolean", "description": "Show staged diff", "default": False},
                "file": {"type": "string", "description": "Specific file to diff", "required": False},
                "context_lines": {"type": "integer", "description": "Number of context lines", "default": 3},
            },
            returns={"diff": {"type": "string"}, "has_changes": {"type": "boolean"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.diff"], tags=["git", "diff"],
        ),
    ]

    branch_tools = [
        ToolContract(
            id="git.list_branches", name="List Branches",
            description="List local (or all) branches",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "all": {"type": "boolean", "description": "Include remote branches", "default": False},
            },
            returns={"branches": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.list_branches"], tags=["git", "branches"],
        ),
        ToolContract(
            id="git.create_branch", name="Create Branch",
            description="Create a new branch",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "name": {"type": "string", "description": "Branch name"},
                "base": {"type": "string", "description": "Base branch or commit", "required": False},
            },
            returns={"name": {"type": "string"}, "created": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE, category="git",
            capabilities=["git.create_branch"], tags=["git", "branch", "create"],
        ),
        ToolContract(
            id="git.checkout_branch", name="Checkout Branch",
            description="Switch to a branch (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "name": {"type": "string", "description": "Branch name to checkout"},
                "create_new": {"type": "boolean", "description": "Create and checkout new branch", "default": False},
            },
            returns={"branch": {"type": "string"}, "message": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="git",
            requires_confirmation=True,
            capabilities=["git.checkout_branch"], tags=["git", "checkout"],
        ),
        ToolContract(
            id="git.delete_branch", name="Delete Branch",
            description="Delete a branch (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "name": {"type": "string", "description": "Branch name to delete"},
                "force": {"type": "boolean", "description": "Force delete", "default": False},
            },
            returns={"branch": {"type": "string"}, "deleted": {"type": "boolean"}},
            permission_level=PermissionLevel.SENSITIVE, category="git",
            requires_confirmation=True,
            capabilities=["git.delete_branch"], tags=["git", "branch", "delete"],
        ),
    ]

    commit_tools = [
        ToolContract(
            id="git.commit", name="Commit",
            description="Create a commit with a message",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "message": {"type": "string", "description": "Commit message"},
                "all": {"type": "boolean", "description": "Stage all changes first", "default": False},
                "amend": {"type": "boolean", "description": "Amend last commit", "default": False},
            },
            returns={"hash": {"type": "string"}, "message": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="git",
            capabilities=["git.commit"], tags=["git", "commit"],
        ),
        ToolContract(
            id="git.commit_log", name="Commit Log",
            description="Show commit history",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "max_count": {"type": "integer", "description": "Max commits to show", "default": 20},
                "branch": {"type": "string", "description": "Branch to show", "required": False},
                "format": {"type": "string", "description": "Format: hash, short, reference, full", "default": "reference"},
            },
            returns={"commits": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.commit_log"], tags=["git", "log", "history"],
        ),
        ToolContract(
            id="git.show_commit", name="Show Commit",
            description="Show details of a specific commit",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "commit": {"type": "string", "description": "Commit reference", "default": "HEAD"},
                "stat": {"type": "boolean", "description": "Show file statistics", "default": True},
            },
            returns={"commit": {"type": "string"}, "details": {"type": "object"}, "output": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.show_commit"], tags=["git", "show", "commit"],
        ),
        ToolContract(
            id="git.amend_last_commit", name="Amend Last Commit",
            description="Amend the last commit (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "message": {"type": "string", "description": "New commit message", "required": False},
                "no_edit": {"type": "boolean", "description": "Keep existing message", "default": False},
            },
            returns={"hash": {"type": "string"}, "amended": {"type": "boolean"}},
            permission_level=PermissionLevel.SENSITIVE, category="git",
            requires_confirmation=True,
            capabilities=["git.amend_last_commit"], tags=["git", "amend"],
        ),
    ]

    remote_tools = [
        ToolContract(
            id="git.fetch", name="Fetch",
            description="Fetch from remote (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "remote": {"type": "string", "description": "Remote name", "default": "origin"},
                "prune": {"type": "boolean", "description": "Prune deleted remotes", "default": False},
            },
            returns={"remote": {"type": "string"}, "output": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="git",
            requires_confirmation=True,
            capabilities=["git.fetch"], tags=["git", "fetch"],
        ),
        ToolContract(
            id="git.pull", name="Pull",
            description="Pull from remote (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "remote": {"type": "string", "description": "Remote name", "required": False},
                "branch": {"type": "string", "description": "Branch to pull", "required": False},
                "rebase": {"type": "boolean", "description": "Use rebase instead of merge", "default": False},
            },
            returns={"remote": {"type": "string"}, "output": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="git",
            requires_confirmation=True,
            capabilities=["git.pull"], tags=["git", "pull"],
        ),
        ToolContract(
            id="git.push", name="Push",
            description="Push to remote (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "remote": {"type": "string", "description": "Remote name", "default": "origin"},
                "branch": {"type": "string", "description": "Branch to push", "required": False},
                "force": {"type": "boolean", "description": "Force push", "default": False},
                "set_upstream": {"type": "boolean", "description": "Set upstream tracking", "default": False},
            },
            returns={"remote": {"type": "string"}, "output": {"type": "string"}},
            permission_level=PermissionLevel.SENSITIVE, category="git",
            requires_confirmation=True,
            capabilities=["git.push"], tags=["git", "push"],
        ),
    ]

    tag_tools = [
        ToolContract(
            id="git.list_tags", name="List Tags",
            description="List tags in the repository",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
            },
            returns={"tags": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="git",
            capabilities=["git.list_tags"], tags=["git", "tags"],
        ),
        ToolContract(
            id="git.create_tag", name="Create Tag",
            description="Create a tag (annotated or lightweight)",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "name": {"type": "string", "description": "Tag name"},
                "message": {"type": "string", "description": "Annotation message", "required": False},
                "target": {"type": "string", "description": "Commit to tag", "default": "HEAD"},
            },
            returns={"name": {"type": "string"}, "annotated": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE, category="git",
            capabilities=["git.create_tag"], tags=["git", "tag", "create"],
        ),
        ToolContract(
            id="git.checkout_tag", name="Checkout Tag",
            description="Checkout a tag (detached HEAD)",
            parameters={
                "path": {"type": "string", "description": "Repository path", "required": False},
                "name": {"type": "string", "description": "Tag name"},
                "create_branch": {"type": "string", "description": "Create branch from tag", "required": False},
            },
            returns={"tag": {"type": "string"}, "branch": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="git",
            requires_confirmation=True,
            capabilities=["git.checkout_tag"], tags=["git", "tag", "checkout"],
        ),
    ]

    mgmt_tools = [
        ToolContract(
            id="git.cancel_operation", name="Cancel Git Operation",
            description="Cancel a running git operation by op_id (or all if omitted)",
            parameters={
                "op_id": {"type": "string", "description": "Operation ID to cancel", "required": False},
            },
            returns={"cancelled": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="git",
            capabilities=["git.cancel_operation"], tags=["git", "cancel"],
        ),
    ]

    all_tools = repo_tools + status_tools + branch_tools + commit_tools + remote_tools + tag_tools + mgmt_tools

    repo_handlers = [
        _discover_repositories, _current_repository, _repository_info,
    ]
    status_handlers = [
        _git_status, _staged_files, _modified_files, _untracked_files, _git_diff,
    ]
    branch_handlers = [
        _list_branches, _create_branch,
        lambda p, eb=event_bus: _checkout_branch(p, eb),
        lambda p, eb=event_bus: _delete_branch(p, eb),
    ]
    commit_handlers = [
        lambda p, eb=event_bus: _commit(p, eb),
        _commit_log, _show_commit,
        lambda p, eb=event_bus: _amend_last_commit(p, eb),
    ]
    remote_handlers = [
        lambda p, eb=event_bus: _fetch(p, eb),
        lambda p, eb=event_bus: _pull(p, eb),
        lambda p, eb=event_bus: _push(p, eb),
    ]
    tag_handlers = [
        _list_tags, _create_tag, _checkout_tag,
    ]
    mgmt_handlers = [_cancel_git_operation]

    all_handlers = repo_handlers + status_handlers + branch_handlers + commit_handlers + remote_handlers + tag_handlers + mgmt_handlers

    for contract, handler in zip(all_tools, all_handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
