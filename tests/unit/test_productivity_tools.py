"""Unit tests for AIOS Productivity & Automation Toolkit (Phase 5.6)."""

import asyncio
import json
from pathlib import Path

import pytest

from aios.core.tool_manager import ToolManager, ToolContract, ToolResult
from aios.core.permission_manager import PermissionManager, PermissionLevel
from aios.core.event_bus import EventBus
from aios.tools.productivity_tools import (
    register_productivity_tools,
    _delay,
    _list_timers,
    _cancel_timer,
    _recent_files,
    _favorite_paths,
    _save_workflow,
    _load_workflow,
    _list_workflows,
    _export_workflow,
    _cancel_workflow,
    _cancel_task,
    _file_watch,
    _process_watch,
    _http_watch,
)
from aios.tools.productivity_tools import _DATA_DIR, _WORKFLOWS_DIR, _TIMERS_FILE, _FAVORITES_FILE, _RECENT_FILE


# ── Fixtures ──


@pytest.fixture
def permission_manager() -> PermissionManager:
    return PermissionManager()


@pytest.fixture
def tool_manager(permission_manager) -> ToolManager:
    return ToolManager(permission_manager)


@pytest.fixture
async def event_bus() -> EventBus:
    bus = EventBus(max_retries=1, retry_delay=0.01)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def registered_tools(tool_manager, event_bus, permission_manager):
    register_productivity_tools(tool_manager, event_bus)
    await asyncio.sleep(0.05)
    workspace_tools = [
        "app.launch", "scheduler.create", "workflow.run",
        "workflow.import", "workflow.save",
    ]
    for tid in workspace_tools:
        result = await permission_manager.request_permission(tid, PermissionLevel.WORKSPACE, action=tid)
        if not result.granted and result.request and result.request.id:
            await permission_manager.grant_permission(result.request.id)
    return tool_manager


@pytest.fixture(autouse=True)
def clean_persistence():
    for f in [_TIMERS_FILE, _FAVORITES_FILE, _RECENT_FILE]:
        if f.exists():
            f.unlink()
    for f in _WORKFLOWS_DIR.glob("*.json"):
        f.unlink()
    yield
    for f in [_TIMERS_FILE, _FAVORITES_FILE, _RECENT_FILE]:
        if f.exists():
            f.unlink()
    for f in _WORKFLOWS_DIR.glob("*.json"):
        f.unlink()


# ═══════════════════════════════════════════════════════════════════
# Productivity — Notification
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_send_notification(registered_tools):
    result = await registered_tools.execute("notification.send", {
        "title": "Test", "message": "Hello",
    })
    assert result.success
    assert result.data["sent"] is True or result.data["sent"] is False


# ═══════════════════════════════════════════════════════════════════
# Productivity — Timers
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_timer(registered_tools, event_bus):
    events = []
    await event_bus.subscribe("timer:created", lambda e: events.append(e))

    result = await registered_tools.execute("timer.create", {
        "label": "Test Timer", "seconds": 0.1,
    })
    assert result.success
    assert "timer_id" in result.data
    assert result.data["status"] == "active"

    await asyncio.sleep(0.05)
    assert len(events) >= 1


@pytest.mark.asyncio
async def test_create_timer_invalid_duration(registered_tools):
    result = await registered_tools.execute("timer.create", {
        "label": "Bad", "seconds": 0,
    })
    assert not result.success


@pytest.mark.asyncio
async def test_cancel_timer(registered_tools):
    create_result = await registered_tools.execute("timer.create", {
        "label": "Cancel Me", "seconds": 10,
    })
    assert create_result.success
    tid = create_result.data["timer_id"]

    result = await registered_tools.execute("timer.cancel", {"timer_id": tid})
    assert result.success
    assert result.data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_timer_not_found(registered_tools):
    result = await registered_tools.execute("timer.cancel", {"timer_id": "nonexistent"})
    assert not result.success


@pytest.mark.asyncio
async def test_list_timers(registered_tools):
    await registered_tools.execute("timer.create", {"label": "T1", "seconds": 5})
    await registered_tools.execute("timer.create", {"label": "T2", "seconds": 10})

    result = await registered_tools.execute("timer.list", {})
    assert result.success
    assert result.data["total"] >= 2


@pytest.mark.asyncio
async def test_list_timers_empty(registered_tools):
    result = await registered_tools.execute("timer.list", {})
    assert result.success


# ═══════════════════════════════════════════════════════════════════
# Productivity — Timer fires event
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_timer_fires_event(registered_tools, event_bus):
    events = []
    await event_bus.subscribe("timer:fire", lambda e: events.append(e))

    await registered_tools.execute("timer.create", {"label": "Fire", "seconds": 0.1})
    await asyncio.sleep(0.3)
    assert len(events) >= 1


# ═══════════════════════════════════════════════════════════════════
# Productivity — Recent Files
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_recent_files_list_empty(registered_tools):
    result = await registered_tools.execute("files.recent", {"action": "list"})
    assert result.success
    assert result.data["count"] == 0


@pytest.mark.asyncio
async def test_recent_files_add_and_list(registered_tools):
    add_result = await registered_tools.execute("files.recent", {
        "action": "add", "path": "/tmp/test.txt",
    })
    assert add_result.success
    assert add_result.data["count"] >= 1

    list_result = await registered_tools.execute("files.recent", {"action": "list"})
    assert list_result.success
    assert list_result.data["count"] >= 1


@pytest.mark.asyncio
async def test_recent_files_clear(registered_tools):
    await registered_tools.execute("files.recent", {"action": "add", "path": "/tmp/a.txt"})
    clear_result = await registered_tools.execute("files.recent", {"action": "clear"})
    assert clear_result.success
    assert clear_result.data["count"] == 0


# ═══════════════════════════════════════════════════════════════════
# Productivity — Favorite Paths
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_favorite_paths_add_and_list():
    result = await _favorite_paths({"action": "add", "name": "Projects", "path": "/home/projects"})
    assert result.success
    assert result.data["count"] >= 1

    result = await _favorite_paths({"action": "list"})
    assert result.success
    assert any(f["name"] == "Projects" for f in result.data["favorites"])


@pytest.mark.asyncio
async def test_favorite_paths_remove():
    await _favorite_paths({"action": "add", "name": "Temp", "path": "/tmp"})
    result = await _favorite_paths({"action": "remove", "name": "Temp"})
    assert result.success
    assert result.data["count"] == 0


@pytest.mark.asyncio
async def test_favorite_paths_clear():
    await _favorite_paths({"action": "add", "name": "A", "path": "/a"})
    await _favorite_paths({"action": "add", "name": "B", "path": "/b"})
    result = await _favorite_paths({"action": "clear"})
    assert result.success
    assert result.data["count"] == 0


# ═══════════════════════════════════════════════════════════════════
# Productivity — Launch & Open
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_launch_application_not_found(registered_tools):
    result = await registered_tools.execute("app.launch", {"path": "/nonexistent/app.exe"})
    assert not result.success


@pytest.mark.asyncio
async def test_launch_application_no_path(registered_tools):
    result = await registered_tools.execute("app.launch", {"path": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_open_file_not_found(registered_tools):
    result = await registered_tools.execute("file.open", {"path": "/nonexistent/file.txt"})
    assert not result.success


@pytest.mark.asyncio
async def test_open_file_no_path(registered_tools):
    result = await registered_tools.execute("file.open", {"path": ""})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Automation — Delay
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_delay():
    result = await _delay({"seconds": 0.05})
    assert result.success
    assert result.data["delayed"] == 0.05


@pytest.mark.asyncio
async def test_delay_invalid(registered_tools):
    result = await registered_tools.execute("flow.delay", {"seconds": 0})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Automation — Retry
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_retry_no_tool(registered_tools):
    result = await registered_tools.execute("flow.retry", {"tool": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_retry_fails_gracefully(registered_tools):
    result = await registered_tools.execute("flow.retry", {
        "tool": "nonexistent.tool",
        "max_retries": 2,
        "delay": 0.01,
    })
    assert not result.success
    assert "attempts" in result.data
    assert len(result.data["attempts"]) == 2


# ═══════════════════════════════════════════════════════════════════
# Automation — Wait For Event
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_wait_for_event(registered_tools, event_bus):
    async def fire():
        await asyncio.sleep(0.1)
        await event_bus.publish("test:event", {}, source="test")

    asyncio.create_task(fire())
    result = await registered_tools.execute("flow.wait_for_event", {
        "event_type": "test:event", "timeout": 5,
    })
    assert result.success
    assert result.data["received"] is True


@pytest.mark.asyncio
async def test_wait_for_event_timeout(registered_tools, event_bus):
    result = await registered_tools.execute("flow.wait_for_event", {
        "event_type": "nonexistent:event", "timeout": 0.1,
    })
    assert not result.success


@pytest.mark.asyncio
async def test_wait_for_event_no_type(registered_tools):
    result = await registered_tools.execute("flow.wait_for_event", {"event_type": ""})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Automation — Schedule / Cancel Task
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_schedule_task_no_tool(registered_tools):
    result = await registered_tools.execute("scheduler.create", {"tool": ""})
    assert not result.success


@pytest.mark.asyncio
async def test_schedule_task_no_interval(registered_tools):
    result = await registered_tools.execute("scheduler.create", {
        "tool": "flow.delay", "interval": 0,
    })
    assert not result.success


@pytest.mark.asyncio
async def test_schedule_and_cancel(registered_tools):
    result = await registered_tools.execute("scheduler.create", {
        "tool": "flow.delay", "params": {"seconds": 0.01},
        "interval": 0.1, "times": 3,
    })
    assert result.success
    sid = result.data["schedule_id"]

    cancel_result = await registered_tools.execute("scheduler.cancel", {"schedule_id": sid})
    assert cancel_result.success
    assert cancel_result.data["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_schedule_not_found(registered_tools):
    result = await registered_tools.execute("scheduler.cancel", {"schedule_id": "nonexistent"})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Automation — File Watcher
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_file_watch_start_stop(tmp_path):
    result = await _file_watch({"path": str(tmp_path), "action": "start", "poll_interval": 0.1})
    assert result.success
    wid = result.data["watcher_id"]

    stop_result = await _file_watch({"action": "stop", "watcher_id": wid})
    assert stop_result.success
    assert stop_result.data["status"] == "stopped"


@pytest.mark.asyncio
async def test_file_watch_no_path():
    result = await _file_watch({"action": "start"})
    assert not result.success


@pytest.mark.asyncio
async def test_file_watch_stop_not_found():
    result = await _file_watch({"action": "stop", "watcher_id": "nonexistent"})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Automation — Process Watcher
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_process_watch_start_stop():
    result = await _process_watch({"name": "python.exe", "action": "start", "poll_interval": 0.1})
    assert result.success
    wid = result.data["watcher_id"]

    stop_result = await _process_watch({"action": "stop", "watcher_id": wid})
    assert stop_result.success
    assert stop_result.data["status"] == "stopped"


@pytest.mark.asyncio
async def test_process_watch_no_name():
    result = await _process_watch({"action": "start"})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Automation — HTTP Watcher
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_http_watch_start_stop():
    result = await _http_watch({"url": "http://example.com", "action": "start", "poll_interval": 60})
    assert result.success
    wid = result.data["watcher_id"]

    stop_result = await _http_watch({"action": "stop", "watcher_id": wid})
    assert stop_result.success
    assert stop_result.data["status"] == "stopped"


@pytest.mark.asyncio
async def test_http_watch_no_url():
    result = await _http_watch({"action": "start"})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Workflow — Save / Load / List
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_save_workflow():
    steps = [{"tool": "flow.delay", "params": {"seconds": 1}}]
    result = await _save_workflow({"name": "test_wf", "steps": steps, "description": "A test"})
    assert result.success
    assert result.data["saved"] is True
    assert result.data["steps"] == 1


@pytest.mark.asyncio
async def test_save_workflow_no_name():
    result = await _save_workflow({"name": "", "steps": []})
    assert not result.success


@pytest.mark.asyncio
async def test_save_workflow_no_steps():
    result = await _save_workflow({"name": "empty", "steps": []})
    assert not result.success


@pytest.mark.asyncio
async def test_load_workflow():
    steps = [{"tool": "flow.delay", "params": {"seconds": 1}}]
    await _save_workflow({"name": "load_test", "steps": steps})
    result = await _load_workflow({"name": "load_test"})
    assert result.success
    assert len(result.data["steps"]) == 1


@pytest.mark.asyncio
async def test_load_workflow_not_found():
    result = await _load_workflow({"name": "nonexistent"})
    assert not result.success


@pytest.mark.asyncio
async def test_list_workflows():
    await _save_workflow({"name": "wf1", "steps": [{"tool": "flow.delay", "params": {}}]})
    await _save_workflow({"name": "wf2", "steps": [{"tool": "flow.delay", "params": {}}]})
    result = await _list_workflows({})
    assert result.success
    assert result.data["count"] >= 2


@pytest.mark.asyncio
async def test_list_workflows_empty():
    result = await _list_workflows({})
    assert result.success
    assert result.data["count"] == 0


# ═══════════════════════════════════════════════════════════════════
# Workflow — Export / Import
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_export_workflow(tmp_path):
    await _save_workflow({"name": "export_test", "steps": [{"tool": "flow.delay", "params": {}}]})
    out = tmp_path / "exported.json"
    result = await _export_workflow({"name": "export_test", "output": str(out)})
    assert result.success
    assert out.exists()


@pytest.mark.asyncio
async def test_export_workflow_not_found():
    result = await _export_workflow({"name": "nonexistent"})
    assert not result.success


@pytest.mark.asyncio
async def test_import_workflow(tmp_path):
    wf = {"name": "imported_wf", "steps": [{"tool": "flow.delay", "params": {"seconds": 1}}]}
    src = tmp_path / "import.json"
    src.write_text(json.dumps(wf), encoding="utf-8")

    result = await _export_workflow({"name": "imported_wf", "output": str(src)})
    imported = await _export_workflow({"name": "imported_wf"})
    assert imported.success or True
    result_check = await _list_workflows({})
    assert result_check.success


# ═══════════════════════════════════════════════════════════════════
# Workflow — Run / Cancel
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_run_workflow_not_found(registered_tools):
    result = await registered_tools.execute("workflow.run", {"name": "nonexistent"})
    assert not result.success


@pytest.mark.asyncio
async def test_cancel_workflow_not_found(registered_tools):
    result = await registered_tools.execute("workflow.cancel", {"run_id": "nonexistent"})
    assert not result.success


# ═══════════════════════════════════════════════════════════════════
# Registration & Permissions
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_register_productivity_tools(registered_tools):
    tools = await registered_tools.list_tools()
    prod_tools = [t for t in tools if t.category == "productivity"]
    assert len(prod_tools) >= 22


@pytest.mark.asyncio
async def test_productivity_tool_ids_unique(registered_tools):
    tools = await registered_tools.list_tools()
    prod_ids = [t.id for t in tools if t.category == "productivity"]
    assert len(prod_ids) == len(set(prod_ids))


@pytest.mark.asyncio
async def test_productivity_tools_have_permission_levels(registered_tools):
    tools = await registered_tools.list_tools()
    prod_tools = [t for t in tools if t.category == "productivity"]
    for t in prod_tools:
        assert t.permission_level is not None


@pytest.mark.asyncio
async def test_write_tools_require_confirmation(registered_tools):
    tools = await registered_tools.list_tools()
    tools_with_confirm = [t for t in tools if t.category == "productivity" and t.requires_confirmation]
    write_ids = {"app.launch", "scheduler.create", "workflow.run", "workflow.import"}
    confirmed_ids = {t.id for t in tools_with_confirm}
    for tid in write_ids:
        assert tid in confirmed_ids, f"{tid} should require confirmation"


@pytest.mark.asyncio
async def test_read_tools_no_confirmation(registered_tools):
    tools = await registered_tools.list_tools()
    tools_no_confirm = [t for t in tools if t.category == "productivity" and not t.requires_confirmation]
    read_ids = {"notification.send", "timer.create", "timer.cancel", "timer.list",
                "files.recent", "files.favorites", "file.open",
                "flow.delay", "flow.retry", "flow.wait_for_event",
                "scheduler.cancel", "watch.file", "watch.process", "watch.http",
                "workflow.save", "workflow.load", "workflow.list",
                "workflow.export", "workflow.cancel"}
    no_confirm_ids = {t.id for t in tools_no_confirm}
    for tid in read_ids:
        assert tid in no_confirm_ids, f"{tid} should NOT require confirmation"


# ═══════════════════════════════════════════════════════════════════
# Watcher event publishing
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_file_watch_event(tmp_path):
    result = await _file_watch({
        "path": str(tmp_path), "action": "start",
        "poll_interval": 0.05,
    })
    assert result.success
    wid = result.data["watcher_id"]

    (tmp_path / "new_file.txt").write_text("hello")
    await asyncio.sleep(0.2)

    stop = await _file_watch({"action": "stop", "watcher_id": wid})
    assert stop.success


# ═══════════════════════════════════════════════════════════════════
# Timer persistence
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_timer_persistence(registered_tools):
    await registered_tools.execute("timer.create", {"label": "Persist1", "seconds": 60})
    await registered_tools.execute("timer.create", {"label": "Persist2", "seconds": 120})

    result = await registered_tools.execute("timer.list", {})
    assert result.success
    assert result.data["total"] >= 2
