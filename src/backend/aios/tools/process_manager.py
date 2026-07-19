"""Process management tools."""

import psutil
import subprocess
from aios.core.tool_manager import ToolResult


async def list_processes(params: dict | None = None) -> ToolResult:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
        try:
            processes.append({
                "pid": proc.info["pid"],
                "name": proc.info["name"],
                "cpu_percent": proc.info["cpu_percent"] or 0.0,
                "memory_mb": round((proc.info["memory_info"].rss / 1024 / 1024), 1) if proc.info["memory_info"] else 0.0,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda p: p["memory_mb"], reverse=True)
    return ToolResult(success=True, data={"processes": processes, "count": len(processes)})


async def start_process(params: dict) -> ToolResult:
    command = params.get("command", "")
    try:
        proc = subprocess.Popen(command, shell=True)
        return ToolResult(success=True, data={"pid": proc.pid, "command": command})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def kill_process(params: dict) -> ToolResult:
    pid = params.get("pid", 0)
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=5)
        return ToolResult(success=True, data={"pid": pid, "status": "terminated"})
    except psutil.NoSuchProcess:
        return ToolResult(success=False, error=f"Process {pid} not found")
    except psutil.TimeoutExpired:
        proc.kill()
        return ToolResult(success=True, data={"pid": pid, "status": "killed"})
    except Exception as e:
        return ToolResult(success=False, error=str(e))
