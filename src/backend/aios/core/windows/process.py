"""Process management — enumerate, lookup, state, termination."""

import subprocess
from datetime import datetime

from .exceptions import (
    ProcessError,
    ProcessNotFoundError,
    ProcessTerminationError,
)
from .validation import validate_pid, validate_process_name


class ProcessService:
    def list_processes(self) -> list[dict]:
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "create_time", "status"]):
                try:
                    pinfo = proc.info
                    processes.append({
                        "pid": pinfo["pid"],
                        "name": pinfo["name"] or "",
                        "cpu_percent": pinfo["cpu_percent"] or 0.0,
                        "memory_mb": round((pinfo["memory_info"].rss / 1024 / 1024), 1) if pinfo["memory_info"] else 0.0,
                        "create_time": datetime.fromtimestamp(pinfo["create_time"]).isoformat() if pinfo["create_time"] else "",
                        "status": pinfo["status"] or "",
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return sorted(processes, key=lambda p: p["memory_mb"], reverse=True)
        except ImportError:
            raise ProcessError("psutil is not installed")

    def get_process_info(self, pid: int) -> dict:
        safe_pid = validate_pid(pid)
        try:
            import psutil
            proc = psutil.Process(safe_pid)
            with proc.oneshot():
                create_time = proc.create_time()
                return {
                    "pid": proc.pid,
                    "name": proc.name() or "",
                    "exe": proc.exe() or "",
                    "cmdline": proc.cmdline() or [],
                    "cpu_percent": proc.cpu_percent() or 0.0,
                    "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 1),
                    "create_time": datetime.fromtimestamp(create_time).isoformat(),
                    "status": proc.status() or "",
                    "num_threads": proc.num_threads(),
                    "username": proc.username() or "",
                }
        except ImportError:
            raise ProcessError("psutil is not installed")
        except psutil.NoSuchProcess:
            raise ProcessNotFoundError(f"Process not found: {pid}")
        except psutil.AccessDenied:
            raise ProcessError(f"Access denied to process: {pid}")

    def find_process(self, name: str) -> list[dict]:
        safe_name = validate_process_name(name).lower()
        try:
            import psutil
            results = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
                try:
                    pinfo = proc.info
                    proc_name = (pinfo["name"] or "").lower()
                    if safe_name in proc_name:
                        results.append({
                            "pid": pinfo["pid"],
                            "name": pinfo["name"] or "",
                            "cpu_percent": pinfo["cpu_percent"] or 0.0,
                            "memory_mb": round((pinfo["memory_info"].rss / 1024 / 1024), 1) if pinfo["memory_info"] else 0.0,
                            "status": pinfo["status"] or "",
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return results
        except ImportError:
            raise ProcessError("psutil is not installed")

    def terminate_process(self, pid: int, force: bool = False) -> None:
        safe_pid = validate_pid(pid)
        try:
            import psutil
            proc = psutil.Process(safe_pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
        except ImportError:
            raise ProcessError("psutil is not installed")
        except psutil.NoSuchProcess:
            raise ProcessNotFoundError(f"Process not found: {pid}")
        except psutil.AccessDenied:
            raise ProcessTerminationError(f"Permission denied terminating process: {pid}")
        except Exception as e:
            raise ProcessTerminationError(f"Failed to terminate process {pid}: {e}")

    def start_process(self, command: str, shell: bool = False) -> int:
        if not command or not command.strip():
            raise ProcessError("Command must not be empty")
        try:
            import shlex
            args = shlex.split(command)
            proc = subprocess.Popen(args, shell=False)
            return proc.pid
        except OSError as e:
            raise ProcessError(f"Failed to start process: {command}: {e}")
