"""Developer Toolkit — Terminal, PowerShell, Process, Environment, WSL tools for AIOS Phase 5.2."""

import asyncio
import os
import platform
import signal
from datetime import datetime, timezone
from typing import Any

from aios.core.tool_manager import ToolResult
from aios.core.event_bus import EventBus

_running_commands: dict[str, dict[str, Any]] = {}
_cmd_counter = 0


def _next_cmd_id() -> str:
    global _cmd_counter
    _cmd_counter += 1
    return f"cmd_{_cmd_counter}_{datetime.now(timezone.utc).timestamp()}"


def _format_env(env_dict: dict[str, str] | None) -> dict[str, str]:
    base = dict(os.environ)
    if env_dict:
        base.update(env_dict)
    return base


async def _run_command(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        command = params.get("command", "")
        cwd = params.get("cwd")
        env = params.get("env")
        timeout = params.get("timeout", 0)

        if not command:
            return ToolResult(success=False, error="No command provided")

        cmd_id = _next_cmd_id()
        proc_env = _format_env(env)

        import shlex
        args = shlex.split(command)
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=proc_env,
        )

        _running_commands[cmd_id] = {
            "proc": proc,
            "command": command,
            "started_at": datetime.now(timezone.utc),
            "status": "running",
        }

        if event_bus:
            await event_bus.publish(
                "terminal:started",
                {"command_id": cmd_id, "command": command, "cwd": cwd, "shell": shell},
                source="developer_tools",
            )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout if timeout > 0 else None
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            _running_commands[cmd_id]["status"] = "timeout"
            if event_bus:
                await event_bus.publish(
                    "terminal:timeout",
                    {"command_id": cmd_id, "command": command, "timeout": timeout},
                    source="developer_tools",
                )
            return ToolResult(success=False, data={
                "command_id": cmd_id, "command": command,
                "stdout": "", "stderr": f"Command timed out after {timeout}s",
                "exit_code": -1, "status": "timeout",
            })

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode
        duration = (datetime.now(timezone.utc) - _running_commands[cmd_id]["started_at"]).total_seconds()
        _running_commands[cmd_id]["status"] = "completed" if exit_code == 0 else "failed"
        _running_commands[cmd_id]["exit_code"] = exit_code

        if event_bus:
            await event_bus.publish(
                "terminal:completed" if exit_code == 0 else "terminal:failed",
                {
                    "command_id": cmd_id, "command": command, "exit_code": exit_code,
                    "stdout": stdout[-1000:], "stderr": stderr[-1000:],
                    "duration": duration,
                },
                source="developer_tools",
            )

        return ToolResult(success=exit_code == 0, data={
            "command_id": cmd_id, "command": command,
            "stdout": stdout, "stderr": stderr,
            "exit_code": exit_code, "duration": duration,
            "status": _running_commands[cmd_id]["status"],
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _stream_output(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        command = params.get("command", "")
        cwd = params.get("cwd")
        env = params.get("env")
        timeout = params.get("timeout", 0)
        chunk_size = params.get("chunk_size", 4096)

        if not command:
            return ToolResult(success=False, error="No command provided")

        cmd_id = _next_cmd_id()
        proc_env = _format_env(env)

        import shlex
        args = shlex.split(command)
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=proc_env,
        )

        _running_commands[cmd_id] = {
            "proc": proc, "command": command, "started_at": datetime.now(timezone.utc),
            "status": "running", "streaming": True,
        }

        if event_bus:
            await event_bus.publish(
                "terminal:stream:started",
                {"command_id": cmd_id, "command": command, "cwd": cwd},
                source="developer_tools",
            )

        async def _read_stream(stream, stream_name: str):
            full_output = []
            while True:
                chunk = await stream.read(chunk_size)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                full_output.append(text)
                if event_bus:
                    await event_bus.publish(
                        "terminal:stream:output",
                        {"command_id": cmd_id, "stream": stream_name, "data": text},
                        source="developer_tools",
                    )
            return "".join(full_output)

        try:
            stdout_task = asyncio.create_task(_read_stream(proc.stdout, "stdout"))
            stderr_task = asyncio.create_task(_read_stream(proc.stderr, "stderr"))

            if timeout > 0:
                try:
                    exit_code = await asyncio.wait_for(proc.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    await stdout_task
                    await stderr_task
                    _running_commands[cmd_id]["status"] = "timeout"
                    if event_bus:
                        await event_bus.publish(
                            "terminal:stream:timeout",
                            {"command_id": cmd_id, "command": command, "timeout": timeout},
                            source="developer_tools",
                        )
                    return ToolResult(success=False, data={
                        "command_id": cmd_id, "command": command, "exit_code": -1,
                        "stdout": "", "stderr": f"Command timed out after {timeout}s",
                        "status": "timeout",
                    })
            else:
                exit_code = await proc.wait()

            stdout_text = await stdout_task
            stderr_text = await stderr_task

        except asyncio.CancelledError:
            proc.kill()
            await proc.wait()
            _running_commands[cmd_id]["status"] = "cancelled"
            if event_bus:
                await event_bus.publish(
                    "terminal:stream:cancelled",
                    {"command_id": cmd_id, "command": command},
                    source="developer_tools",
                )
            return ToolResult(success=False, data={
                "command_id": cmd_id, "command": command, "exit_code": -1,
                "stdout": "", "stderr": "Command was cancelled",
                "status": "cancelled",
            })

        duration = (datetime.now(timezone.utc) - _running_commands[cmd_id]["started_at"]).total_seconds()
        _running_commands[cmd_id]["status"] = "completed" if exit_code == 0 else "failed"
        _running_commands[cmd_id]["exit_code"] = exit_code

        if event_bus:
            await event_bus.publish(
                "terminal:stream:completed",
                {"command_id": cmd_id, "exit_code": exit_code, "duration": duration},
                source="developer_tools",
            )

        return ToolResult(success=exit_code == 0, data={
            "command_id": cmd_id, "command": command,
            "stdout": stdout_text, "stderr": stderr_text,
            "exit_code": exit_code, "duration": duration,
            "status": _running_commands[cmd_id]["status"],
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _cancel_command(params: dict) -> ToolResult:
    try:
        command_id = params.get("command_id", "")
        if not command_id:
            return ToolResult(success=False, error="No command_id provided")

        entry = _running_commands.get(command_id)
        if not entry:
            return ToolResult(success=False, error=f"Command not found: {command_id}")

        proc = entry.get("proc")
        if not proc or proc.returncode is not None:
            entry["status"] = "completed"
            return ToolResult(success=False, data={
                "command_id": command_id, "status": "already_completed",
                "message": "Command is no longer running",
            })

        try:
            if platform.system() == "Windows":
                proc.kill()
            else:
                proc.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
        except ProcessLookupError:
            pass

        entry["status"] = "cancelled"
        return ToolResult(success=True, data={
            "command_id": command_id, "status": "cancelled",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _command_status(params: dict) -> ToolResult:
    try:
        command_id = params.get("command_id", "")
        if not command_id:
            statuses = []
            for cid, entry in list(_running_commands.items()):
                proc = entry.get("proc")
                statuses.append({
                    "command_id": cid, "command": entry.get("command", ""),
                    "status": entry.get("status", "unknown"),
                    "running": proc is not None and proc.returncode is None,
                    "started_at": entry.get("started_at").isoformat() if entry.get("started_at") else None,
                })
            return ToolResult(success=True, data={"commands": statuses, "count": len(statuses)})

        entry = _running_commands.get(command_id)
        if not entry:
            return ToolResult(success=False, error=f"Command not found: {command_id}")

        proc = entry.get("proc")
        running = proc is not None and proc.returncode is None
        return ToolResult(success=True, data={
            "command_id": command_id, "command": entry.get("command", ""),
            "status": entry.get("status", "unknown"),
            "running": running,
            "started_at": entry.get("started_at").isoformat() if entry.get("started_at") else None,
            "exit_code": entry.get("exit_code") if not running else None,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _run_powershell(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        command = params.get("command", "")
        cwd = params.get("cwd")
        timeout = params.get("timeout", 0)

        if not command:
            return ToolResult(success=False, error="No command provided")

        powershell = "powershell.exe" if platform.system() == "Windows" else "pwsh"
        proc = await asyncio.create_subprocess_exec(
            powershell, "-NoProfile", "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout if timeout > 0 else None
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ToolResult(success=False, data={
                "stdout": "", "stderr": f"PowerShell command timed out after {timeout}s",
                "exit_code": -1, "status": "timeout",
            })

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode

        return ToolResult(success=exit_code == 0, data={
            "stdout": stdout, "stderr": stderr,
            "exit_code": exit_code, "shell": "powershell",
            "status": "completed" if exit_code == 0 else "failed",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _run_powershell_script(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    try:
        script_path = params.get("script_path", "")
        parameters = params.get("parameters", {})
        cwd = params.get("cwd")
        timeout = params.get("timeout", 0)

        if not script_path:
            return ToolResult(success=False, error="No script_path provided")

        if not os.path.exists(script_path):
            return ToolResult(success=False, error=f"Script not found: {script_path}")

        ps_params = " ".join(f"-{k} '{v}'" for k, v in parameters.items())
        command = f"& '{script_path}' {ps_params}"

        powershell = "powershell.exe" if platform.system() == "Windows" else "pwsh"
        proc = await asyncio.create_subprocess_exec(
            powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout if timeout > 0 else None
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ToolResult(success=False, data={
                "stdout": "", "stderr": f"PowerShell script timed out after {timeout}s",
                "exit_code": -1, "status": "timeout",
            })

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode

        return ToolResult(success=exit_code == 0, data={
            "script_path": script_path, "stdout": stdout, "stderr": stderr,
            "exit_code": exit_code, "status": "completed" if exit_code == 0 else "failed",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_processes(params: dict) -> ToolResult:
    try:
        filter_name = params.get("filter", "")
        if platform.system() == "Windows":
            proc = await asyncio.create_subprocess_exec(
                "tasklist", "/V", "/FO", "CSV",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return ToolResult(success=False, error=stderr.decode("utf-8", errors="replace"))

            import csv
            import io
            reader = csv.DictReader(io.StringIO(stdout.decode("utf-8", errors="replace")))
            processes = []
            for row in reader:
                name = row.get("Image Name", "")
                if filter_name and filter_name.lower() not in name.lower():
                    continue
                processes.append({
                    "name": name,
                    "pid": row.get("PID", ""),
                    "session": row.get("Session Name", ""),
                    "mem_usage": row.get("Mem Usage", ""),
                    "status": row.get("Status", ""),
                })
            return ToolResult(success=True, data={
                "processes": processes, "count": len(processes),
                "platform": platform.system(),
            })
        else:
            proc = await asyncio.create_subprocess_exec(
                "ps", "aux",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return ToolResult(success=False, error=stderr.decode("utf-8", errors="replace"))

            lines = stdout.decode("utf-8", errors="replace").splitlines()
            if not lines:
                return ToolResult(success=True, data={"processes": [], "count": 0})
            headers = lines[0].split()
            processes = []
            for line in lines[1:]:
                parts = line.split(None, len(headers) - 1)
                if len(parts) < len(headers):
                    continue
                entry = dict(zip(headers, parts))
                name = entry.get("COMMAND", "")
                if filter_name and filter_name.lower() not in name.lower():
                    continue
                processes.append({
                    "user": entry.get("USER", ""),
                    "pid": entry.get("PID", ""),
                    "cpu": entry.get("%CPU", ""),
                    "mem": entry.get("%MEM", ""),
                    "command": name,
                })
            return ToolResult(success=True, data={
                "processes": processes, "count": len(processes),
                "platform": platform.system(),
            })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _start_process(params: dict) -> ToolResult:
    try:
        executable = params.get("executable", "")
        args = params.get("args", [])
        cwd = params.get("cwd")
        wait = params.get("wait", False)
        timeout = params.get("timeout", 30)

        if not executable:
            return ToolResult(success=False, error="No executable provided")

        cmd = [executable] + args
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd,
            stdout=asyncio.subprocess.PIPE if wait else asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE if wait else asyncio.subprocess.DEVNULL,
        )

        if wait:
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return ToolResult(success=False, data={
                    "pid": proc.pid, "error": f"Process timed out after {timeout}s",
                    "exit_code": -1,
                })
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            return ToolResult(success=proc.returncode == 0, data={
                "pid": proc.pid, "executable": executable,
                "stdout": stdout, "stderr": stderr,
                "exit_code": proc.returncode,
            })

        return ToolResult(success=True, data={
            "pid": proc.pid, "executable": executable,
            "status": "started",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _stop_process(params: dict) -> ToolResult:
    try:
        pid = params.get("pid", 0)
        force = params.get("force", False)

        if not pid:
            return ToolResult(success=False, error="No pid provided")

        if platform.system() == "Windows":
            cmd = ["taskkill", "/F" if force else "", "/PID", str(pid)]
            cmd = [c for c in cmd if c]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
        else:
            sig = signal.SIGKILL if force else signal.SIGTERM
            try:
                os.kill(pid, sig)
                return ToolResult(success=True, data={
                    "pid": pid, "signal": "SIGKILL" if force else "SIGTERM",
                    "status": "stopped",
                })
            except ProcessLookupError:
                return ToolResult(success=False, error=f"Process not found: {pid}")
            except PermissionError:
                return ToolResult(success=False, error=f"Permission denied to stop process: {pid}")

        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return ToolResult(success=False, data={
                "pid": pid, "error": stderr.decode("utf-8", errors="replace").strip(),
            })

        return ToolResult(success=True, data={
            "pid": pid, "force": force, "status": "stopped",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _restart_process(params: dict) -> ToolResult:
    try:
        pid = params.get("pid", 0)
        executable = params.get("executable", "")
        args = params.get("args", [])

        stop_result = await _stop_process({"pid": pid, "force": True})
        if not stop_result.success:
            return stop_result

        if executable:
            start_result = await _start_process({
                "executable": executable, "args": args, "wait": False,
            })
            return start_result

        return ToolResult(success=True, data={
            "old_pid": pid, "status": "restarted",
            "note": "Process stopped. No executable provided to restart.",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _process_info(params: dict) -> ToolResult:
    try:
        pid = params.get("pid", 0)
        if not pid:
            return ToolResult(success=False, error="No pid provided")

        if platform.system() == "Windows":
            proc = await asyncio.create_subprocess_exec(
                "tasklist", "/V", "/FO", "CSV", "/FI", f"PID eq {pid}",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0 or not stdout.strip():
                return ToolResult(success=False, error=f"Process not found: {pid}")

            import csv
            import io
            reader = csv.DictReader(io.StringIO(stdout.decode("utf-8", errors="replace")))
            for row in reader:
                return ToolResult(success=True, data={
                    "pid": pid, "name": row.get("Image Name", ""),
                    "session": row.get("Session Name", ""),
                    "mem_usage": row.get("Mem Usage", ""),
                    "status": row.get("Status", ""),
                    "cpu_time": row.get("CPU Time", ""),
                    "window_title": row.get("Window Title", ""),
                })
            return ToolResult(success=False, error=f"Process not found: {pid}")
        else:
            proc = await asyncio.create_subprocess_exec(
                "ps", "-p", str(pid), "-o", "pid,user,%cpu,%mem,comm",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return ToolResult(success=False, error=f"Process not found: {pid}")
            lines = stdout.decode("utf-8", errors="replace").splitlines()
            if len(lines) < 2:
                return ToolResult(success=False, error=f"Process not found: {pid}")
            parts = lines[1].split(None, 4)
            return ToolResult(success=True, data={
                "pid": parts[0] if len(parts) > 0 else "",
                "user": parts[1] if len(parts) > 1 else "",
                "cpu": parts[2] if len(parts) > 2 else "",
                "mem": parts[3] if len(parts) > 3 else "",
                "command": parts[4] if len(parts) > 4 else "",
            })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_environment(params: dict) -> ToolResult:
    try:
        pattern = params.get("pattern", "")
        values = {}
        for key, val in os.environ.items():
            if pattern and pattern.lower() not in key.lower():
                continue
            values[key] = val
        return ToolResult(success=True, data={
            "variables": values, "count": len(values),
            "pattern": pattern or None,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _get_environment(params: dict) -> ToolResult:
    try:
        name = params.get("name", "")
        if not name:
            return ToolResult(success=False, error="No variable name provided")
        value = os.environ.get(name)
        return ToolResult(success=True, data={
            "name": name, "value": value, "exists": value is not None,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _set_environment_process(params: dict) -> ToolResult:
    try:
        name = params.get("name", "")
        value = params.get("value", "")

        if not name:
            return ToolResult(success=False, error="No variable name provided")

        os.environ[name] = str(value)
        return ToolResult(success=True, data={
            "name": name, "value": str(value), "scope": "process",
            "note": "Only affects the current process. System/user env not modified.",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _detect_wsl(params: dict) -> ToolResult:
    try:
        if platform.system() != "Windows":
            return ToolResult(success=True, data={
                "available": False, "reason": "WSL is only available on Windows",
            })

        proc = await asyncio.create_subprocess_exec(
            "wsl", "--status",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        available = proc.returncode == 0

        if not available:
            wsl_proc = await asyncio.create_subprocess_exec(
                "wsl", "-l", "-q",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            wsl_stdout, _ = await wsl_proc.communicate()
            available = wsl_proc.returncode == 0 and bool(wsl_stdout.strip())

        return ToolResult(success=True, data={
            "available": available,
            "default_version": None,
            "status": stdout.decode("utf-8", errors="replace").strip() if available else "",
        })
    except FileNotFoundError:
        return ToolResult(success=True, data={
            "available": False, "reason": "WSL is not installed",
        })
    except Exception as e:
        return ToolResult(success=True, data={
            "available": False, "reason": str(e),
        })


async def _list_wsl_distributions(params: dict) -> ToolResult:
    try:
        if platform.system() != "Windows":
            return ToolResult(success=True, data={
                "distributions": [], "count": 0,
                "note": "WSL is only available on Windows",
            })

        proc = await asyncio.create_subprocess_exec(
            "wsl", "-l", "-v",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return ToolResult(success=False, data={
                "distributions": [], "error": stderr.decode("utf-8", errors="replace").strip(),
                "note": "WSL may not be installed",
            })

        lines = stdout.decode("utf-8", errors="replace").splitlines()
        distributions = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                distributions.append({
                    "name": parts[0],
                    "state": parts[1],
                    "version": parts[2],
                })
        return ToolResult(success=True, data={
            "distributions": distributions, "count": len(distributions),
        })
    except FileNotFoundError:
        return ToolResult(success=True, data={
            "distributions": [], "count": 0, "note": "WSL is not installed",
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _run_wsl_command(params: dict) -> ToolResult:
    try:
        command = params.get("command", "")
        distribution = params.get("distribution", "")
        timeout = params.get("timeout", 0)

        if not command:
            return ToolResult(success=False, error="No command provided")

        if platform.system() != "Windows":
            return ToolResult(success=False, error="WSL is only available on Windows")

        import shlex
        cmd = ["wsl"]
        if distribution:
            cmd.extend(["-d", distribution])
        cmd.extend(["--"] + shlex.split(command))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout if timeout > 0 else None
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ToolResult(success=False, data={
                "stdout": "", "stderr": f"WSL command timed out after {timeout}s",
                "exit_code": -1, "status": "timeout",
            })

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = proc.returncode

        return ToolResult(success=exit_code == 0, data={
            "stdout": stdout, "stderr": stderr, "exit_code": exit_code,
            "status": "completed" if exit_code == 0 else "failed",
        })
    except FileNotFoundError:
        return ToolResult(success=False, error="WSL is not installed")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


TOOL_HANDLERS: dict[str, tuple] = {}

def register_developer_tools(tm, event_bus=None):
    import asyncio
    from aios.core.tool_manager import ToolContract
    from aios.core.permission_manager import PermissionLevel

    terminal_tools = [
        ToolContract(
            id="terminal.run_command", name="Run Command",
            description="Execute a shell command and return output",
            parameters={
                "command": {"type": "string", "description": "Command to execute"},
                "cwd": {"type": "string", "description": "Working directory", "required": False},
                "env": {"type": "object", "description": "Additional environment variables", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds (0 = no limit)", "default": 0},
                "shell": {"type": "boolean", "description": "Use shell to execute", "default": False},
            },
            returns={
                "stdout": {"type": "string"}, "stderr": {"type": "string"},
                "exit_code": {"type": "integer"}, "duration": {"type": "number"},
            },
            permission_level=PermissionLevel.WORKSPACE, category="developer",
            capabilities=["terminal.run_command"], tags=["terminal", "command", "shell"],
        ),
        ToolContract(
            id="terminal.stream_output", name="Stream Output",
            description="Execute a command and stream output via events (terminal:stream:output)",
            parameters={
                "command": {"type": "string", "description": "Command to execute"},
                "cwd": {"type": "string", "description": "Working directory", "required": False},
                "env": {"type": "object", "description": "Additional environment variables", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 0},
                "shell": {"type": "boolean", "description": "Use shell to execute", "default": False},
            },
            returns={
                "command_id": {"type": "string"}, "stdout": {"type": "string"},
                "stderr": {"type": "string"}, "exit_code": {"type": "integer"},
            },
            permission_level=PermissionLevel.WORKSPACE, category="developer",
            capabilities=["terminal.stream_output"], tags=["terminal", "stream", "output"],
        ),
        ToolContract(
            id="terminal.cancel_command", name="Cancel Command",
            description="Cancel a running command by its command_id",
            parameters={
                "command_id": {"type": "string", "description": "ID of the command to cancel"},
            },
            returns={"command_id": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="developer",
            capabilities=["terminal.cancel_command"], tags=["terminal", "cancel"],
        ),
        ToolContract(
            id="terminal.command_status", name="Command Status",
            description="Get status of a running or completed command (omit command_id to list all)",
            parameters={
                "command_id": {"type": "string", "description": "Command ID (omit to list all)", "required": False},
            },
            returns={"commands": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="developer",
            capabilities=["terminal.command_status"], tags=["terminal", "status"],
        ),
    ]

    powershell_tools = [
        ToolContract(
            id="powershell.run", name="Run PowerShell",
            description="Execute a PowerShell command and return structured output",
            parameters={
                "command": {"type": "string", "description": "PowerShell command to execute"},
                "cwd": {"type": "string", "description": "Working directory", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 0},
            },
            returns={"stdout": {"type": "string"}, "stderr": {"type": "string"}, "exit_code": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="developer",
            capabilities=["powershell.run"], tags=["powershell", "shell"],
        ),
        ToolContract(
            id="powershell.run_script", name="Run PowerShell Script",
            description="Execute a PowerShell script file (requires SENSITIVE permission)",
            parameters={
                "script_path": {"type": "string", "description": "Path to the .ps1 script file"},
                "parameters": {"type": "object", "description": "Script parameters as key-value pairs", "default": {}},
                "cwd": {"type": "string", "description": "Working directory", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 0},
            },
            returns={"stdout": {"type": "string"}, "stderr": {"type": "string"}, "exit_code": {"type": "integer"}},
            permission_level=PermissionLevel.SENSITIVE, category="developer",
            requires_confirmation=True,
            capabilities=["powershell.run_script"], tags=["powershell", "script"],
        ),
    ]

    process_tools = [
        ToolContract(
            id="process.list", name="List Processes",
            description="List running processes (optionally filter by name)",
            parameters={
                "filter": {"type": "string", "description": "Filter by process name", "required": False},
            },
            returns={"processes": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="developer",
            capabilities=["process.list"], tags=["process", "list"],
        ),
        ToolContract(
            id="process.start", name="Start Process",
            description="Start a new process",
            parameters={
                "executable": {"type": "string", "description": "Path to executable"},
                "args": {"type": "array", "description": "Command-line arguments", "default": []},
                "cwd": {"type": "string", "description": "Working directory", "required": False},
                "wait": {"type": "boolean", "description": "Wait for completion", "default": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds when waiting", "default": 30},
            },
            returns={"pid": {"type": "integer"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="developer",
            capabilities=["process.start"], tags=["process", "start"],
        ),
        ToolContract(
            id="process.stop", name="Stop Process",
            description="Stop a running process by PID (requires SENSITIVE permission)",
            parameters={
                "pid": {"type": "integer", "description": "Process ID to stop"},
                "force": {"type": "boolean", "description": "Force kill if graceful stop fails", "default": False},
            },
            returns={"pid": {"type": "integer"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SENSITIVE, category="developer",
            requires_confirmation=True,
            capabilities=["process.stop"], tags=["process", "stop", "kill"],
        ),
        ToolContract(
            id="process.restart", name="Restart Process",
            description="Restart a process (stop then optionally start again)",
            parameters={
                "pid": {"type": "integer", "description": "Process ID to restart"},
                "executable": {"type": "string", "description": "Executable to start (optional)", "required": False},
                "args": {"type": "array", "description": "Arguments for new process", "default": []},
            },
            returns={"old_pid": {"type": "integer"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SENSITIVE, category="developer",
            requires_confirmation=True,
            capabilities=["process.restart"], tags=["process", "restart"],
        ),
        ToolContract(
            id="process.info", name="Process Info",
            description="Get detailed information about a process by PID",
            parameters={
                "pid": {"type": "integer", "description": "Process ID"},
            },
            returns={"pid": {"type": "integer"}, "name": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.READ, category="developer",
            capabilities=["process.info"], tags=["process", "info"],
        ),
    ]

    environment_tools = [
        ToolContract(
            id="environment.list", name="List Environment",
            description="List environment variables (optionally filter by pattern)",
            parameters={
                "pattern": {"type": "string", "description": "Filter by variable name pattern", "required": False},
            },
            returns={"variables": {"type": "object"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="developer",
            capabilities=["environment.list"], tags=["environment", "list"],
        ),
        ToolContract(
            id="environment.get", name="Get Environment",
            description="Get the value of a specific environment variable",
            parameters={
                "name": {"type": "string", "description": "Environment variable name"},
            },
            returns={"name": {"type": "string"}, "value": {"type": "string"}, "exists": {"type": "boolean"}},
            permission_level=PermissionLevel.READ, category="developer",
            capabilities=["environment.get"], tags=["environment", "get"],
        ),
        ToolContract(
            id="environment.set_process", name="Set Environment (Process)",
            description="Set an environment variable for the current process only",
            parameters={
                "name": {"type": "string", "description": "Variable name"},
                "value": {"type": "string", "description": "Variable value"},
            },
            returns={"name": {"type": "string"}, "value": {"type": "string"}, "scope": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, category="developer",
            capabilities=["environment.set_process"], tags=["environment", "set"],
        ),
    ]

    wsl_tools = [
        ToolContract(
            id="wsl.detect", name="Detect WSL",
            description="Check if WSL (Windows Subsystem for Linux) is available",
            parameters={},
            returns={"available": {"type": "boolean"}},
            permission_level=PermissionLevel.READ, category="developer",
            capabilities=["wsl.detect"], tags=["wsl", "detect"],
        ),
        ToolContract(
            id="wsl.list_distributions", name="List WSL Distributions",
            description="List installed WSL distributions and their status",
            parameters={},
            returns={"distributions": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, category="developer",
            capabilities=["wsl.list_distributions"], tags=["wsl", "distributions"],
        ),
        ToolContract(
            id="wsl.run_command", name="Run WSL Command",
            description="Execute a command in a WSL distribution",
            parameters={
                "command": {"type": "string", "description": "Command to execute in WSL"},
                "distribution": {"type": "string", "description": "WSL distribution name (optional)", "required": False},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 0},
            },
            returns={"stdout": {"type": "string"}, "stderr": {"type": "string"}, "exit_code": {"type": "integer"}},
            permission_level=PermissionLevel.WORKSPACE, category="developer",
            capabilities=["wsl.run_command"], tags=["wsl", "command"],
        ),
    ]

    all_tools = terminal_tools + powershell_tools + process_tools + environment_tools + wsl_tools
    terminal_handlers = [
        lambda p, eb=event_bus: _run_command(p, eb),
        lambda p, eb=event_bus: _stream_output(p, eb),
        _cancel_command,
        _command_status,
    ]
    powershell_handlers = [
        lambda p, eb=event_bus: _run_powershell(p, eb),
        lambda p, eb=event_bus: _run_powershell_script(p, eb),
    ]
    process_handlers = [
        _list_processes, _start_process, _stop_process, _restart_process, _process_info,
    ]
    environment_handlers = [
        _list_environment, _get_environment, _set_environment_process,
    ]
    wsl_handlers = [
        _detect_wsl, _list_wsl_distributions, _run_wsl_command,
    ]

    all_handlers = terminal_handlers + powershell_handlers + process_handlers + environment_handlers + wsl_handlers

    for contract, handler in zip(all_tools, all_handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
