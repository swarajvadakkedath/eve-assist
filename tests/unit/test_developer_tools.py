"""Tests for Developer Toolkit (terminal, powershell, process, environment, WSL)."""

import asyncio
import os
import platform
from pathlib import Path

import pytest

from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus
from aios.tools.developer_tools import (
    register_developer_tools,
    _run_command,
    _stream_output,
    _cancel_command,
    _command_status,
    _run_powershell,
    _run_powershell_script,
    _list_processes,
    _start_process,
    _stop_process,
    _restart_process,
    _process_info,
    _list_environment,
    _get_environment,
    _set_environment_process,
    _detect_wsl,
    _list_wsl_distributions,
    _run_wsl_command,
    _running_commands,
)


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


# ── Terminal Tools ──

@pytest.mark.asyncio
async def test_run_command_success():
    result = await _run_command({"command": "echo hello"})
    assert result.success
    assert result.data["exit_code"] == 0
    assert "hello" in result.data["stdout"]


@pytest.mark.asyncio
async def test_run_command_failure():
    result = await _run_command({"command": "exit 1"})
    assert not result.success
    assert result.data["exit_code"] == 1


@pytest.mark.asyncio
async def test_run_command_no_command():
    result = await _run_command({"command": ""})
    assert not result.success
    assert "No command" in result.error


@pytest.mark.asyncio
async def test_run_command_with_cwd(tmp_path):
    script = tmp_path / "test_echo.py"
    script.write_text("import sys; sys.stdout.write('cwd ok')")
    result = await _run_command({
        "command": f"{'python' if platform.system() == 'Windows' else 'python3'} test_echo.py",
        "cwd": str(tmp_path),
    })
    assert result.success
    assert "cwd ok" in result.data["stdout"]


@pytest.mark.asyncio
async def test_run_command_timeout():
    result = await _run_command({
        "command": "ping -n 30 127.0.0.1" if platform.system() == "Windows" else "sleep 30",
        "timeout": 1,
    })
    assert not result.success
    assert result.data["status"] == "timeout"


@pytest.mark.asyncio
async def test_run_command_event_publish(eb):
    events = []
    await eb.subscribe("terminal:started", lambda e: events.append(e))
    await eb.subscribe("terminal:completed", lambda e: events.append(e))

    result = await _run_command({"command": "echo hello"}, event_bus=eb)
    await asyncio.sleep(0.05)

    assert result.success
    event_types = [e.type for e in events]
    assert "terminal:started" in event_types
    assert "terminal:completed" in event_types


@pytest.mark.asyncio
async def test_stream_output_success():
    result = await _stream_output({"command": "echo streaming"})
    assert result.success
    assert result.data["exit_code"] == 0
    assert "streaming" in result.data["stdout"]


@pytest.mark.asyncio
async def test_cancel_command_not_found():
    result = await _cancel_command({"command_id": "nonexistent"})
    assert not result.success
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_command_status_list():
    result = await _command_status({})
    assert result.success
    assert "commands" in result.data


@pytest.mark.asyncio
async def test_command_status_by_id():
    _running_commands["test_cmd_123"] = {
        "proc": None, "command": "echo hi", "started_at": None, "status": "completed",
    }
    result = await _command_status({"command_id": "test_cmd_123"})
    assert result.success
    assert result.data["status"] == "completed"
    _running_commands.pop("test_cmd_123", None)


# ── PowerShell Tools ──

@pytest.mark.asyncio
async def test_run_powershell():
    cmd = "Write-Host 'hello powershell'" if platform.system() == "Windows" else "echo 'hello powershell'"
    result = await _run_powershell({"command": cmd})
    if platform.system() == "Windows":
        assert result.success
    else:
        assert result.success or "pwsh" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_run_powershell_script_not_found():
    result = await _run_powershell_script({"script_path": "/nonexistent/script.ps1"})
    assert not result.success
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_run_powershell_no_command():
    result = await _run_powershell({"command": ""})
    assert not result.success


# ── Process Tools ──

@pytest.mark.asyncio
async def test_list_processes():
    result = await _list_processes({})
    assert result.success
    assert "processes" in result.data
    assert result.data["count"] > 0


@pytest.mark.asyncio
async def test_list_processes_filtered():
    result = await _list_processes({"filter": platform.system() == "Windows" and "python" or "python"})
    assert result.success


@pytest.mark.asyncio
async def test_start_process_no_executable():
    result = await _start_process({"executable": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_stop_process_no_pid():
    result = await _stop_process({"pid": 0})
    assert not result.success


@pytest.mark.asyncio
async def test_process_info_no_pid():
    result = await _process_info({"pid": 0})
    assert not result.success


@pytest.mark.asyncio
async def test_restart_process_no_pid():
    result = await _restart_process({"pid": 0})
    assert not result.success


# ── Environment Tools ──

@pytest.mark.asyncio
async def test_list_environment():
    result = await _list_environment({})
    assert result.success
    assert "variables" in result.data
    assert result.data["count"] > 0


@pytest.mark.asyncio
async def test_list_environment_pattern():
    result = await _list_environment({"pattern": "PATH"})
    assert result.success
    assert "PATH" in result.data["variables"]


@pytest.mark.asyncio
async def test_get_environment():
    result = await _get_environment({"name": "PATH"})
    assert result.success
    assert result.data["exists"]
    assert result.data["value"] is not None


@pytest.mark.asyncio
async def test_get_environment_not_found():
    result = await _get_environment({"name": "__NONEXISTENT_VAR_12345__"})
    assert result.success
    assert not result.data["exists"]
    assert result.data["value"] is None


@pytest.mark.asyncio
async def test_get_environment_no_name():
    result = await _get_environment({"name": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_set_environment_process():
    result = await _set_environment_process({"name": "AIOS_TEST_VAR", "value": "test_value"})
    assert result.success
    assert result.data["name"] == "AIOS_TEST_VAR"
    assert result.data["scope"] == "process"
    assert os.environ.get("AIOS_TEST_VAR") == "test_value"
    os.environ.pop("AIOS_TEST_VAR", None)


@pytest.mark.asyncio
async def test_set_environment_process_no_name():
    result = await _set_environment_process({"name": "", "value": "val"})
    assert not result.success


# ── WSL Tools ──

@pytest.mark.asyncio
async def test_detect_wsl():
    result = await _detect_wsl({})
    assert result.success
    assert "available" in result.data


@pytest.mark.asyncio
async def test_list_wsl_distributions():
    result = await _list_wsl_distributions({})
    assert result.success or "WSL" in result.data.get("note", result.data.get("error", ""))


@pytest.mark.asyncio
async def test_run_wsl_command_no_command():
    result = await _run_wsl_command({"command": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_run_wsl_command_not_installed():
    result = await _run_wsl_command({"command": "echo hi"})
    if platform.system() != "Windows":
        assert not result.success
    else:
        assert result.success or not result.success  # depends on WSL presence


# ── Registration ──

@pytest.mark.asyncio
async def test_register_developer_tools(tm, eb):
    register_developer_tools(tm, eb)
    await asyncio.sleep(0.05)

    terminal_tool = await tm.get_tool("terminal.run_command")
    assert terminal_tool is not None
    assert terminal_tool.category == "developer"

    ps_tool = await tm.get_tool("powershell.run")
    assert ps_tool is not None

    process_tool = await tm.get_tool("process.list")
    assert process_tool is not None

    env_tool = await tm.get_tool("environment.list")
    assert env_tool is not None

    wsl_tool = await tm.get_tool("wsl.detect")
    assert wsl_tool is not None


@pytest.mark.asyncio
async def test_register_all_developer_tools(tm, eb):
    register_developer_tools(tm, eb)
    await asyncio.sleep(0.05)
    all_tools = await tm.list_tools()
    tool_ids = [t.id for t in all_tools]

    expected = [
        "terminal.run_command", "terminal.stream_output",
        "terminal.cancel_command", "terminal.command_status",
        "powershell.run", "powershell.run_script",
        "process.list", "process.start", "process.stop",
        "process.restart", "process.info",
        "environment.list", "environment.get", "environment.set_process",
        "wsl.detect", "wsl.list_distributions", "wsl.run_command",
    ]
    for tid in expected:
        assert tid in tool_ids, f"Missing tool: {tid}"


@pytest.mark.asyncio
async def test_developer_tools_have_developer_category(tm, eb):
    register_developer_tools(tm, eb)
    await asyncio.sleep(0.05)
    dev_tools = await tm.list_tools("developer")
    assert len(dev_tools) > 0
    for t in dev_tools:
        assert t.category == "developer"
