"""Built-in tool implementations."""

from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionLevel


async def _read_file(params: dict) -> ToolResult:
    try:
        from pathlib import Path
        path = Path(params["path"])
        if not path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        content = path.read_text(encoding="utf-8")
        return ToolResult(success=True, data={"content": content, "path": str(path)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _write_file(params: dict) -> ToolResult:
    try:
        from pathlib import Path
        path = Path(params["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(params["content"], encoding="utf-8")
        return ToolResult(success=True, data={"path": str(path), "size": len(params["content"])})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_directory(params: dict) -> ToolResult:
    try:
        from pathlib import Path
        path = Path(params["path"])
        if not path.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")
        entries = []
        for entry in path.iterdir():
            entries.append({"name": entry.name, "is_dir": entry.is_dir()})
        return ToolResult(success=True, data={"path": str(path), "entries": entries})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _execute_command(params: dict) -> ToolResult:
    import asyncio
    import shlex
    import subprocess
    try:
        args = shlex.split(params["command"])
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=params.get("timeout", 30))
        return ToolResult(
            success=proc.returncode == 0,
            data={"stdout": stdout.decode(), "stderr": stderr.decode(), "returncode": proc.returncode},
        )
    except asyncio.TimeoutError:
        return ToolResult(success=False, error="Command timed out")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_files(params: dict) -> ToolResult:
    from pathlib import Path
    try:
        root = Path(params["path"])
        pattern = params.get("pattern", "*")
        results = [str(p) for p in root.rglob(pattern)]
        return ToolResult(success=True, data={"files": results, "count": len(results)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _get_system_info(params: dict) -> ToolResult:
    import platform
    return ToolResult(success=True, data={
        "os": platform.system(),
        "os_version": platform.version(),
        "hostname": platform.node(),
        "python_version": platform.python_version(),
    })


def register_builtin_tools(tm: ToolManager):
    import asyncio
    from aios.core.permission_manager import PermissionLevel

    tools = [
        ToolContract(
            id="file.read",
            name="Read File",
            description="Read the contents of a file",
            parameters={"path": {"type": "string", "description": "Path to the file"}},
            returns={"content": {"type": "string"}, "path": {"type": "string"}},
            permission_level=PermissionLevel.READ,
            category="filesystem",
            capabilities=["file.read"],
        ),
        ToolContract(
            id="file.write",
            name="Write File",
            description="Write content to a file",
            parameters={"path": {"type": "string"}, "content": {"type": "string"}},
            returns={"path": {"type": "string"}, "size": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE,
            category="filesystem",
            capabilities=["file.write"],
        ),
        ToolContract(
            id="file.list",
            name="List Directory",
            description="List files and directories in a path",
            parameters={"path": {"type": "string"}},
            returns={"path": {"type": "string"}, "entries": {"type": "array"}},
            permission_level=PermissionLevel.READ,
            category="filesystem",
            capabilities=["file.list"],
        ),
        ToolContract(
            id="file.search",
            name="Search Files",
            description="Search for files matching a pattern",
            parameters={"path": {"type": "string"}, "pattern": {"type": "string"}},
            returns={"files": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ,
            category="filesystem",
            capabilities=["file.search"],
        ),
        ToolContract(
            id="system.info",
            name="System Info",
            description="Get system information",
            parameters={},
            returns={"os": {"type": "string"}, "hostname": {"type": "string"}},
            permission_level=PermissionLevel.READ,
            category="system",
            capabilities=["system.info"],
        ),
        ToolContract(
            id="command.execute",
            name="Execute Command",
            description="Execute a shell command",
            parameters={"command": {"type": "string"}, "timeout": {"type": "integer"}},
            returns={"stdout": {"type": "string"}, "stderr": {"type": "string"}},
            permission_level=PermissionLevel.SENSITIVE,
            category="system",
            capabilities=["command.execute"],
        ),
    ]

    handlers = [
        _read_file, _write_file, _list_directory,
        _search_files, _get_system_info, _execute_command,
    ]

    for contract, handler in zip(tools, handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
