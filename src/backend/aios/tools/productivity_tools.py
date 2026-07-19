"""Productivity & Automation Toolkit — Notifications, Timers, Watchers, Workflows for AIOS Phase 5.6."""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios.core.tool_manager import ToolResult
from aios.core.event_bus import EventBus


# ── Persistence ──

_DATA_DIR = Path.home() / ".eve" / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_TIMERS_FILE = _DATA_DIR / "timers.json"
_WORKFLOWS_DIR = _DATA_DIR / "workflows"
_FAVORITES_FILE = _DATA_DIR / "favorites.json"
_RECENT_FILE = _DATA_DIR / "recent_files.json"
_SCHEDULED_FILE = _DATA_DIR / "scheduled_tasks.json"

_WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> list | dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return [] if path.suffix == ".json" else {}
    return [] if path.suffix == ".json" else {}


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


# ── State ──

_timers: dict[str, asyncio.Task] = {}
_scheduled_tasks: dict[str, asyncio.Task] = {}
_workflow_runs: dict[str, asyncio.Task] = {}
_file_watchers: dict[str, asyncio.Task] = {}
_process_watchers: dict[str, asyncio.Task] = {}
_http_watchers: dict[str, asyncio.Task] = {}
_timer_counter: int = 0
_schedule_counter: int = 0
_workflow_run_counter: int = 0
_watcher_counter: int = 0


def _next_id(prefix: str) -> str:
    global _timer_counter, _schedule_counter, _workflow_run_counter, _watcher_counter
    if prefix == "timer":
        _timer_counter += 1
        return f"{prefix}_{_timer_counter}"
    if prefix == "sched":
        _schedule_counter += 1
        return f"{prefix}_{_schedule_counter}"
    if prefix == "wf":
        _workflow_run_counter += 1
        return f"{prefix}_{_workflow_run_counter}"
    _watcher_counter += 1
    return f"{prefix}_{_watcher_counter}"


# ── Persistence helpers for timers ──


def _persist_timers() -> None:
    data = _load_json(_TIMERS_FILE)
    _save_json(_TIMERS_FILE, data)


def _restore_timers() -> list[dict]:
    return _load_json(_TIMERS_FILE) if isinstance(_load_json(_TIMERS_FILE), list) else []


# ── Productivity Tools ──


async def _send_notification(params: dict) -> ToolResult:
    title = params.get("title", "Notification")
    message = params.get("message", "")
    try:
        import platform
        system = platform.system().lower()
        if system == "windows":
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=5, threaded=True)
        elif system == "darwin":
            subprocess.Popen(["osascript", "-e",
                f'display notification "{message}" with title "{title}"'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["notify-send", title, message], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ToolResult(success=True, data={"title": title, "message": message, "sent": True})
    except ImportError:
        return ToolResult(success=True, data={"title": title, "message": message, "sent": False, "warning": "win10toast not installed"})
    except Exception as e:
        return ToolResult(success=True, data={"title": title, "message": message, "sent": False, "warning": str(e)})


async def _create_timer(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    label = params.get("label", f"Timer {_timer_counter + 1}")
    seconds = params.get("seconds", 0)
    if seconds <= 0:
        return ToolResult(success=False, error="Timer duration must be > 0 seconds")

    tid = _next_id("timer")

    async def _run_timer():
        try:
            await asyncio.sleep(seconds)
            if event_bus:
                await event_bus.publish(
                    "timer:fire",
                    {"timer_id": tid, "label": label, "seconds": seconds},
                    source="productivity_tools",
                )
        except asyncio.CancelledError:
            pass
        finally:
            _timers.pop(tid, None)
            _persist_timers()

    task = asyncio.create_task(_run_timer())
    _timers[tid] = task

    timer_data = {"timer_id": tid, "label": label, "seconds": seconds, "created_at": datetime.now(timezone.utc).isoformat()}
    data = _load_json(_TIMERS_FILE)
    if isinstance(data, list):
        data.append(timer_data)
    else:
        data = [timer_data]
    _save_json(_TIMERS_FILE, data)

    if event_bus:
        await event_bus.publish("timer:created", timer_data, source="productivity_tools")

    return ToolResult(success=True, data={"timer_id": tid, "label": label, "seconds": seconds, "status": "active"})


async def _cancel_timer(params: dict) -> ToolResult:
    tid = params.get("timer_id", "")
    task = _timers.pop(tid, None)
    if task:
        task.cancel()
        data = _load_json(_TIMERS_FILE)
        if isinstance(data, list):
            data = [t for t in data if t.get("timer_id") != tid]
            _save_json(_TIMERS_FILE, data)
        return ToolResult(success=True, data={"timer_id": tid, "status": "cancelled"})
    return ToolResult(success=False, error=f"Timer not found: {tid}")


async def _list_timers(params: dict) -> ToolResult:
    data = _load_json(_TIMERS_FILE)
    timers = data if isinstance(data, list) else []
    active = len([t for t in timers if t.get("timer_id") in _timers])
    return ToolResult(success=True, data={
        "timers": timers,
        "total": len(timers),
        "active": active,
    })


async def _recent_files(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    action = params.get("action", "list")
    file_path = params.get("path", "")
    max_items = params.get("max", 20)

    files = _load_json(_RECENT_FILE)
    if not isinstance(files, list):
        files = []

    if action == "add" and file_path:
        p = Path(file_path).resolve()
        entry = {"path": str(p), "name": p.name, "added_at": datetime.now(timezone.utc).isoformat()}
        files = [e for e in files if e.get("path") != str(p)]
        files.insert(0, entry)
        files = files[:max_items]
        _save_json(_RECENT_FILE, files)
        if event_bus:
            await event_bus.publish("recent:added", entry, source="productivity_tools")

    if action == "clear":
        _save_json(_RECENT_FILE, [])
        files = []

    return ToolResult(success=True, data={
        "files": files,
        "count": len(files),
        "action": action,
    })


async def _favorite_paths(params: dict) -> ToolResult:
    action = params.get("action", "list")
    name = params.get("name", "")
    path = params.get("path", "")
    max_items = params.get("max", 50)

    favorites = _load_json(_FAVORITES_FILE)
    if not isinstance(favorites, list):
        favorites = []

    if action == "add" and name and path:
        p = Path(path).resolve()
        entry = {"name": name, "path": str(p), "added_at": datetime.now(timezone.utc).isoformat()}
        favorites = [e for e in favorites if e.get("name") != name]
        favorites.append(entry)
        favorites = favorites[-max_items:]
        _save_json(_FAVORITES_FILE, favorites)

    if action == "remove" and name:
        favorites = [e for e in favorites if e.get("name") != name]
        _save_json(_FAVORITES_FILE, favorites)

    if action == "clear":
        _save_json(_FAVORITES_FILE, [])
        favorites = []

    return ToolResult(success=True, data={
        "favorites": favorites,
        "count": len(favorites),
        "action": action,
    })


async def _launch_application(params: dict) -> ToolResult:
    app_path = params.get("path", "")
    args = params.get("args", "")
    if not app_path:
        return ToolResult(success=False, error="No application path provided")
    try:
        p = Path(app_path)
        if not p.exists():
            return ToolResult(success=False, error=f"Application not found: {app_path}")
        cmd = [str(p)]
        if args:
            cmd.extend(args.split())
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ToolResult(success=True, data={
            "path": str(p), "pid": proc.pid, "launched": True,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _open_file(params: dict) -> ToolResult:
    file_path = params.get("path", "")
    if not file_path:
        return ToolResult(success=False, error="No file path provided")
    try:
        p = Path(file_path)
        if not p.exists():
            return ToolResult(success=False, error=f"File not found: {file_path}")
        import platform
        system = platform.system().lower()
        if system == "windows":
            os.startfile(str(p))
        elif system == "darwin":
            subprocess.Popen(["open", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ToolResult(success=True, data={"path": str(p), "opened": True})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ── Automation Tools ──


async def _delay(params: dict) -> ToolResult:
    seconds = params.get("seconds", 1)
    if seconds <= 0:
        return ToolResult(success=False, error="Delay must be > 0 seconds")
    await asyncio.sleep(seconds)
    return ToolResult(success=True, data={"delayed": seconds})


async def _retry(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    tool_id = params.get("tool", "")
    tool_params = params.get("params", {})
    max_retries = params.get("max_retries", 3)
    delay_seconds = params.get("delay", 1)
    backoff = params.get("backoff", 1)

    if not tool_id:
        return ToolResult(success=False, error="No tool ID provided")

    import importlib
    attempts = []
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            module = importlib.import_module("aios.tools.productivity_tools")
            handler = getattr(module, f"_{tool_id.replace('.', '_')}", None)
            if not handler:
                module = importlib.import_module("aios.tools.system_tools")
                handler = getattr(module, f"_{tool_id.replace('.', '_')}", None)
        except Exception:
            handler = None

        if handler:
            result = await handler(tool_params) if not hasattr(handler, "__code__") else await handler(tool_params)
        else:
            result = ToolResult(success=False, error=f"Handler not found for {tool_id}")

        attempts.append({"attempt": attempt, "success": result.success, "error": result.error})
        if result.success:
            if event_bus:
                await event_bus.publish("retry:success", {"tool": tool_id, "attempts": attempt}, source="productivity_tools")
            return ToolResult(success=True, data={
                "tool": tool_id,
                "attempts": attempt,
                "last_result": result.data,
                "attempts_log": attempts,
            })
        last_error = result.error
        if attempt < max_retries:
            await asyncio.sleep(delay_seconds * (backoff ** (attempt - 1)))

    if event_bus:
        await event_bus.publish("retry:failed", {"tool": tool_id, "max_retries": max_retries}, source="productivity_tools")
    return ToolResult(success=False, error=f"All {max_retries} attempts failed for {tool_id}: {last_error}", data={"attempts": attempts})


async def _wait_for_event(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    event_type = params.get("event_type", "")
    timeout = params.get("timeout", 30)
    if not event_type:
        return ToolResult(success=False, error="No event_type provided")
    received = asyncio.Event()

    async def handler(event):
        received.set()

    sub_id = await event_bus.subscribe(event_type, handler)
    try:
        await asyncio.wait_for(received.wait(), timeout=timeout)
        return ToolResult(success=True, data={"event_type": event_type, "received": True})
    except asyncio.TimeoutError:
        return ToolResult(success=False, error=f"Timeout waiting for event: {event_type}")
    finally:
        await event_bus.unsubscribe(sub_id)


async def _schedule_task(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    tool_id = params.get("tool", "")
    tool_params = params.get("params", {})
    interval = params.get("interval", 0)
    times = params.get("times", 0)

    if not tool_id:
        return ToolResult(success=False, error="No tool ID provided")
    if interval <= 0:
        return ToolResult(success=False, error="Interval must be > 0 seconds")

    sid = _next_id("sched")

    async def _run_scheduled():
        remaining = times
        try:
            while True:
                await asyncio.sleep(interval)

                import importlib
                try:
                    module = importlib.import_module("aios.tools.productivity_tools")
                    handler = getattr(module, f"_{tool_id.replace('.', '_')}", None)
                    if not handler:
                        module = importlib.import_module("aios.tools.system_tools")
                        handler = getattr(module, f"_{tool_id.replace('.', '_')}", None)
                except Exception:
                    handler = None

                if handler:
                    result = await handler(tool_params)
                else:
                    result = ToolResult(success=False, error=f"Handler not found")

                if event_bus:
                    await event_bus.publish(
                        "scheduled:executed",
                        {"schedule_id": sid, "tool": tool_id, "success": result.success},
                        source="productivity_tools",
                    )

                if times > 0:
                    remaining -= 1
                    if remaining <= 0:
                        break
        except asyncio.CancelledError:
            pass
        finally:
            _scheduled_tasks.pop(sid, None)

    task = asyncio.create_task(_run_scheduled())
    _scheduled_tasks[sid] = task

    sched_data = {
        "schedule_id": sid, "tool": tool_id,
        "interval": interval, "times": times,
    }
    data = _load_json(_SCHEDULED_FILE)
    if isinstance(data, list):
        data.append(sched_data)
        _save_json(_SCHEDULED_FILE, data)

    return ToolResult(success=True, data={"schedule_id": sid, "status": "scheduled", "tool": tool_id})


async def _cancel_task(params: dict) -> ToolResult:
    sid = params.get("schedule_id", "")
    task = _scheduled_tasks.pop(sid, None)
    if task:
        task.cancel()
        data = _load_json(_SCHEDULED_FILE)
        if isinstance(data, list):
            data = [s for s in data if s.get("schedule_id") != sid]
            _save_json(_SCHEDULED_FILE, data)
        return ToolResult(success=True, data={"schedule_id": sid, "status": "cancelled"})
    return ToolResult(success=False, error=f"Scheduled task not found: {sid}")


async def _file_watch(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    path = params.get("path", "")
    action = params.get("action", "start")
    events_filter = params.get("events", ["modified", "created", "deleted"])
    poll_interval = params.get("poll_interval", 1.0)

    if action == "stop":
        wid = params.get("watcher_id", "")
        task = _file_watchers.pop(wid, None)
        if task:
            task.cancel()
            return ToolResult(success=True, data={"watcher_id": wid, "status": "stopped"})
        return ToolResult(success=False, error=f"File watcher not found: {wid}")

    if not path:
        return ToolResult(success=False, error="No path provided")

    target = Path(path)
    if not target.exists():
        return ToolResult(success=False, error=f"Path not found: {path}")

    wid = _next_id("file_watch")

    async def _watch_loop():
        try:
            snapshots: dict[str, tuple[float, int]] = {}
            if target.is_file():
                snapshots[str(target)] = (target.stat().st_mtime, target.stat().st_size)
            else:
                for entry in target.rglob("*"):
                    if entry.is_file():
                        try:
                            snapshots[str(entry)] = (entry.stat().st_mtime, entry.stat().st_size)
                        except OSError:
                            pass
            while True:
                await asyncio.sleep(poll_interval)
                if target.is_file():
                    current_files = [target]
                else:
                    current_files = list(target.rglob("*"))

                current_paths = set()
                for entry in current_files:
                    if not entry.is_file():
                        continue
                    sp = str(entry)
                    current_paths.add(sp)
                    try:
                        mtime = entry.stat().st_mtime
                        size = entry.stat().st_size
                    except OSError:
                        continue
                    prev = snapshots.get(sp)
                    if prev is None and "created" in events_filter:
                        snapshots[sp] = (mtime, size)
                        if event_bus:
                            await event_bus.publish("file_watch:created", {"path": sp}, source="productivity_tools")
                    elif prev and (prev[0] != mtime or prev[1] != size) and "modified" in events_filter:
                        snapshots[sp] = (mtime, size)
                        if event_bus:
                            await event_bus.publish("file_watch:modified", {"path": sp}, source="productivity_tools")

                for sp in list(snapshots.keys()):
                    if sp not in current_paths and "deleted" in events_filter:
                        del snapshots[sp]
                        if event_bus:
                            await event_bus.publish("file_watch:deleted", {"path": sp}, source="productivity_tools")
        except asyncio.CancelledError:
            pass
        finally:
            _file_watchers.pop(wid, None)

    task = asyncio.create_task(_watch_loop())
    _file_watchers[wid] = task

    return ToolResult(success=True, data={
        "watcher_id": wid, "path": path, "status": "watching",
    })


async def _process_watch(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    process_name = params.get("name", "")
    action = params.get("action", "start")
    poll_interval = params.get("poll_interval", 2.0)

    if action == "stop":
        wid = params.get("watcher_id", "")
        task = _process_watchers.pop(wid, None)
        if task:
            task.cancel()
            return ToolResult(success=True, data={"watcher_id": wid, "status": "stopped"})
        return ToolResult(success=False, error=f"Process watcher not found: {wid}")

    if not process_name:
        return ToolResult(success=False, error="No process name provided")

    wid = _next_id("proc_watch")

    async def _watch_loop():
        was_running = None
        try:
            while True:
                await asyncio.sleep(poll_interval)
                running = False
                try:
                    if os.name == "nt":
                        result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                                                 capture_output=True, text=True, timeout=5)
                        running = process_name.lower() in result.stdout.lower() and "No tasks" not in result.stdout
                    else:
                        result = subprocess.run(["pgrep", "-x", process_name],
                                                 capture_output=True, timeout=5)
                        running = result.returncode == 0
                except Exception:
                    pass

                if was_running is not None and running != was_running:
                    if running and event_bus:
                        await event_bus.publish("process_watch:started", {"name": process_name}, source="productivity_tools")
                    elif not running and event_bus:
                        await event_bus.publish("process_watch:stopped", {"name": process_name}, source="productivity_tools")
                was_running = running
        except asyncio.CancelledError:
            pass
        finally:
            _process_watchers.pop(wid, None)

    task = asyncio.create_task(_watch_loop())
    _process_watchers[wid] = task

    return ToolResult(success=True, data={
        "watcher_id": wid, "name": process_name, "status": "watching",
    })


async def _http_watch(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    url = params.get("url", "")
    action = params.get("action", "start")
    poll_interval = params.get("poll_interval", 30.0)
    expected_status = params.get("expected_status", 200)

    if action == "stop":
        wid = params.get("watcher_id", "")
        task = _http_watchers.pop(wid, None)
        if task:
            task.cancel()
            return ToolResult(success=True, data={"watcher_id": wid, "status": "stopped"})
        return ToolResult(success=False, error=f"HTTP watcher not found: {wid}")

    if not url:
        return ToolResult(success=False, error="No URL provided")

    wid = _next_id("http_watch")

    async def _watch_loop():
        last_status = None
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                while True:
                    await asyncio.sleep(poll_interval)
                    try:
                        resp = await client.get(url, follow_redirects=True, timeout=10)
                        current_status = resp.status_code
                    except Exception:
                        current_status = 0

                    if last_status is not None and current_status != last_status:
                        is_up = current_status == expected_status
                        if event_bus:
                            await event_bus.publish(
                                "http_watch:changed",
                                {"url": url, "status": "up" if is_up else "down",
                                 "status_code": current_status, "previous_code": last_status},
                                source="productivity_tools",
                            )
                    last_status = current_status
        except asyncio.CancelledError:
            pass
        finally:
            _http_watchers.pop(wid, None)

    task = asyncio.create_task(_watch_loop())
    _http_watchers[wid] = task

    return ToolResult(success=True, data={
        "watcher_id": wid, "url": url, "status": "watching", "poll_interval": poll_interval,
    })


# ── Workflow Tools ──


def _workflow_path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    return _WORKFLOWS_DIR / f"{safe}.json"


async def _save_workflow(params: dict) -> ToolResult:
    name = params.get("name", "")
    steps = params.get("steps", [])
    description = params.get("description", "")

    if not name:
        return ToolResult(success=False, error="No workflow name provided")
    if not steps:
        return ToolResult(success=False, error="No steps provided")

    wf = {
        "name": name,
        "description": description,
        "steps": steps,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path = _workflow_path(name)
    _save_json(path, wf)

    return ToolResult(success=True, data={
        "name": name, "steps": len(steps), "path": str(path), "saved": True,
    })


async def _load_workflow(params: dict) -> ToolResult:
    name = params.get("name", "")
    if not name:
        return ToolResult(success=False, error="No workflow name provided")
    path = _workflow_path(name)
    if not path.exists():
        return ToolResult(success=False, error=f"Workflow not found: {name}")
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
        return ToolResult(success=True, data=wf)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_workflows(params: dict) -> ToolResult:
    workflows = []
    for f in sorted(_WORKFLOWS_DIR.glob("*.json")):
        try:
            wf = json.loads(f.read_text(encoding="utf-8"))
            workflows.append({
                "name": wf.get("name", f.stem),
                "description": wf.get("description", ""),
                "steps": len(wf.get("steps", [])),
                "created_at": wf.get("created_at", ""),
                "updated_at": wf.get("updated_at", ""),
            })
        except Exception:
            pass
    return ToolResult(success=True, data={
        "workflows": workflows, "count": len(workflows),
    })


async def _export_workflow(params: dict) -> ToolResult:
    name = params.get("name", "")
    output_path = params.get("output", "")
    if not name:
        return ToolResult(success=False, error="No workflow name provided")
    src = _workflow_path(name)
    if not src.exists():
        return ToolResult(success=False, error=f"Workflow not found: {name}")
    try:
        wf = json.loads(src.read_text(encoding="utf-8"))
        dst = Path(output_path) if output_path else src
        if output_path:
            dst.parent.mkdir(parents=True, exist_ok=True)
        _save_json(dst, wf)
        return ToolResult(success=True, data={
            "name": name, "output": str(dst), "exported": True,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _import_workflow(params: dict, event_bus: EventBus | None = None) -> ToolResult:
    path = params.get("path", "")
    if not path:
        return ToolResult(success=False, error="No import path provided")
    src = Path(path)
    if not src.exists():
        return ToolResult(success=False, error=f"File not found: {path}")
    try:
        wf = json.loads(src.read_text(encoding="utf-8"))
        name = wf.get("name", src.stem)
        wf["name"] = name
        wf["updated_at"] = datetime.now(timezone.utc).isoformat()
        dst = _workflow_path(name)
        _save_json(dst, wf)
        if event_bus:
            await event_bus.publish("workflow:imported", {"name": name}, source="productivity_tools")
        return ToolResult(success=True, data={
            "name": name, "steps": len(wf.get("steps", [])), "imported": True,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _run_workflow(params: dict, event_bus: EventBus | None = None, tool_manager=None) -> ToolResult:
    name = params.get("name", "")
    if not name:
        return ToolResult(success=False, error="No workflow name provided")
    path = _workflow_path(name)
    if not path.exists():
        return ToolResult(success=False, error=f"Workflow not found: {name}")
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return ToolResult(success=False, error=str(e))

    run_id = _next_id("wf")

    async def _execute_workflow():
        results = []
        for i, step in enumerate(wf.get("steps", [])):
            step_tool = step.get("tool", "")
            step_params = step.get("params", {})
            try:
                if tool_manager:
                    result = await tool_manager.execute(step_tool, step_params)
                else:
                    result = ToolResult(success=False, error="No tool_manager available")
                results.append({
                    "step": i + 1,
                    "tool": step_tool,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                })
                if event_bus:
                    await event_bus.publish(
                        "workflow:step_completed",
                        {"run_id": run_id, "workflow": name, "step": i + 1, "tool": step_tool, "success": result.success},
                        source="productivity_tools",
                    )
            except asyncio.CancelledError:
                results.append({"step": i + 1, "tool": step_tool, "success": False, "error": "Cancelled"})
                break
            except Exception as e:
                results.append({"step": i + 1, "tool": step_tool, "success": False, "error": str(e)})
        _workflow_runs.pop(run_id, None)
        if event_bus:
            await event_bus.publish(
                "workflow:completed",
                {"run_id": run_id, "workflow": name, "total_steps": len(results),
                 "success_count": sum(1 for r in results if r["success"])},
                source="productivity_tools",
            )
        return results

    task = asyncio.create_task(_execute_workflow())
    _workflow_runs[run_id] = task

    if event_bus:
        await event_bus.publish("workflow:started", {"run_id": run_id, "workflow": name}, source="productivity_tools")

    return ToolResult(success=True, data={
        "run_id": run_id,
        "workflow": name,
        "total_steps": len(wf.get("steps", [])),
        "status": "running",
    })


async def _cancel_workflow(params: dict) -> ToolResult:
    run_id = params.get("run_id", "")
    task = _workflow_runs.pop(run_id, None)
    if task:
        task.cancel()
        return ToolResult(success=True, data={"run_id": run_id, "status": "cancelled"})
    return ToolResult(success=False, error=f"Workflow run not found: {run_id}")


# ── Registration ──

def register_productivity_tools(tm, event_bus=None):
    import asyncio
    from aios.core.tool_manager import ToolContract
    from aios.core.permission_manager import PermissionLevel

    productivity_tools = [
        ToolContract(
            id="notification.send", name="Send Notification",
            description="Send a desktop notification",
            parameters={
                "title": {"type": "string", "description": "Notification title", "default": "Notification"},
                "message": {"type": "string", "description": "Notification message"},
            },
            returns={"title": {"type": "string"}, "message": {"type": "string"}, "sent": {"type": "boolean"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["notification.send"], tags=["notification", "desktop"],
        ),
        ToolContract(
            id="timer.create", name="Create Timer",
            description="Create a countdown timer that fires an event",
            parameters={
                "label": {"type": "string", "description": "Timer label", "default": "Timer"},
                "seconds": {"type": "number", "description": "Countdown in seconds"},
            },
            returns={"timer_id": {"type": "string"}, "label": {"type": "string"}, "seconds": {"type": "number"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["timer.create"], tags=["timer", "countdown"],
        ),
        ToolContract(
            id="timer.cancel", name="Cancel Timer",
            description="Cancel a running timer",
            parameters={
                "timer_id": {"type": "string", "description": "Timer ID to cancel"},
            },
            returns={"timer_id": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["timer.cancel"], tags=["timer", "cancel"],
        ),
        ToolContract(
            id="timer.list", name="List Timers",
            description="List all timers (active and completed)",
            parameters={},
            returns={"timers": {"type": "array"}, "total": {"type": "integer"}, "active": {"type": "integer"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["timer.list"], tags=["timer", "list"],
        ),
        ToolContract(
            id="files.recent", name="Recent Files",
            description="List, add to, or clear recent files",
            parameters={
                "action": {"type": "string", "description": "list, add, or clear", "default": "list"},
                "path": {"type": "string", "description": "File path (for add action)", "required": False},
                "max": {"type": "integer", "description": "Max items", "default": 20},
            },
            returns={"files": {"type": "array"}, "count": {"type": "integer"}, "action": {"type": "string"}},
            permission_level=PermissionLevel.READ, requires_confirmation=False, category="productivity",
            capabilities=["files.recent"], tags=["files", "recent"],
        ),
        ToolContract(
            id="files.favorites", name="Favorite Paths",
            description="Manage favorite file/directory paths",
            parameters={
                "action": {"type": "string", "description": "list, add, remove, or clear", "default": "list"},
                "name": {"type": "string", "description": "Favorite name (for add/remove)", "required": False},
                "path": {"type": "string", "description": "Path (for add action)", "required": False},
            },
            returns={"favorites": {"type": "array"}, "count": {"type": "integer"}, "action": {"type": "string"}},
            permission_level=PermissionLevel.READ, requires_confirmation=False, category="productivity",
            capabilities=["files.favorites"], tags=["files", "favorites"],
        ),
        ToolContract(
            id="app.launch", name="Launch Application",
            description="Launch a desktop application (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Application path"},
                "args": {"type": "string", "description": "Command-line arguments", "required": False},
            },
            returns={"path": {"type": "string"}, "pid": {"type": "integer"}, "launched": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=True, category="productivity",
            capabilities=["app.launch"], tags=["app", "launch"],
        ),
        ToolContract(
            id="file.open", name="Open File",
            description="Open a file with its default application",
            parameters={
                "path": {"type": "string", "description": "File path to open"},
            },
            returns={"path": {"type": "string"}, "opened": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=False, category="productivity",
            capabilities=["file.open"], tags=["file", "open"],
        ),
    ]

    automation_tools = [
        ToolContract(
            id="flow.delay", name="Delay",
            description="Pause execution for a specified duration",
            parameters={
                "seconds": {"type": "number", "description": "Seconds to delay", "default": 1},
            },
            returns={"delayed": {"type": "number"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["flow.delay"], tags=["flow", "delay"],
        ),
        ToolContract(
            id="flow.retry", name="Retry",
            description="Retry a tool call with backoff on failure",
            parameters={
                "tool": {"type": "string", "description": "Tool ID to retry"},
                "params": {"type": "object", "description": "Parameters for the tool", "default": {}},
                "max_retries": {"type": "integer", "description": "Max retry attempts", "default": 3},
                "delay": {"type": "number", "description": "Initial delay between retries", "default": 1},
                "backoff": {"type": "number", "description": "Multiplier for each retry", "default": 1},
            },
            returns={"tool": {"type": "string"}, "attempts": {"type": "integer"}, "attempts_log": {"type": "array"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["flow.retry"], tags=["flow", "retry"],
        ),
        ToolContract(
            id="flow.wait_for_event", name="Wait For Event",
            description="Pause until a specific Event Bus event is received",
            parameters={
                "event_type": {"type": "string", "description": "Event type to wait for"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
            },
            returns={"event_type": {"type": "string"}, "received": {"type": "boolean"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["flow.wait_for_event"], tags=["flow", "event", "wait"],
        ),
        ToolContract(
            id="scheduler.create", name="Schedule Task",
            description="Schedule a recurring tool execution (requires confirmation)",
            parameters={
                "tool": {"type": "string", "description": "Tool ID to execute"},
                "params": {"type": "object", "description": "Parameters for the tool", "default": {}},
                "interval": {"type": "number", "description": "Interval in seconds between executions"},
                "times": {"type": "integer", "description": "Number of executions (0 = infinite)", "default": 0},
            },
            returns={"schedule_id": {"type": "string"}, "status": {"type": "string"}, "tool": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=True, category="productivity",
            capabilities=["scheduler.create"], tags=["scheduler", "schedule", "cron"],
        ),
        ToolContract(
            id="scheduler.cancel", name="Cancel Scheduled Task",
            description="Cancel a scheduled recurring task",
            parameters={
                "schedule_id": {"type": "string", "description": "Schedule ID to cancel"},
            },
            returns={"schedule_id": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["scheduler.cancel"], tags=["scheduler", "cancel"],
        ),
        ToolContract(
            id="watch.file", name="File Watcher",
            description="Watch a file or directory for changes (publishes events)",
            parameters={
                "path": {"type": "string", "description": "File or directory to watch"},
                "action": {"type": "string", "description": "start or stop", "default": "start"},
                "events": {"type": "array", "description": "Events: modified, created, deleted", "default": ["modified", "created", "deleted"]},
                "poll_interval": {"type": "number", "description": "Poll interval in seconds", "default": 1.0},
                "watcher_id": {"type": "string", "description": "Watcher ID (for stop action)", "required": False},
            },
            returns={"watcher_id": {"type": "string"}, "path": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["watch.file"], tags=["watch", "file"],
        ),
        ToolContract(
            id="watch.process", name="Process Watcher",
            description="Watch a process by name for start/stop events",
            parameters={
                "name": {"type": "string", "description": "Process name to watch (e.g. notepad.exe)"},
                "action": {"type": "string", "description": "start or stop", "default": "start"},
                "poll_interval": {"type": "number", "description": "Poll interval in seconds", "default": 2.0},
                "watcher_id": {"type": "string", "description": "Watcher ID (for stop action)", "required": False},
            },
            returns={"watcher_id": {"type": "string"}, "name": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["watch.process"], tags=["watch", "process"],
        ),
        ToolContract(
            id="watch.http", name="HTTP Watcher",
            description="Watch a URL for availability changes (publishes events)",
            parameters={
                "url": {"type": "string", "description": "URL to watch"},
                "action": {"type": "string", "description": "start or stop", "default": "start"},
                "poll_interval": {"type": "number", "description": "Poll interval in seconds", "default": 30.0},
                "expected_status": {"type": "integer", "description": "Expected HTTP status", "default": 200},
                "watcher_id": {"type": "string", "description": "Watcher ID (for stop action)", "required": False},
            },
            returns={"watcher_id": {"type": "string"}, "url": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["watch.http"], tags=["watch", "http", "uptime"],
        ),
    ]

    workflow_tools = [
        ToolContract(
            id="workflow.save", name="Save Workflow",
            description="Save a sequence of tool calls as a reusable workflow",
            parameters={
                "name": {"type": "string", "description": "Workflow name"},
                "steps": {"type": "array", "description": "Array of {tool, params} steps"},
                "description": {"type": "string", "description": "Workflow description", "default": ""},
            },
            returns={"name": {"type": "string"}, "steps": {"type": "integer"}, "saved": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=False, category="productivity",
            capabilities=["workflow.save"], tags=["workflow", "save"],
        ),
        ToolContract(
            id="workflow.load", name="Load Workflow",
            description="Load a saved workflow by name",
            parameters={
                "name": {"type": "string", "description": "Workflow name"},
            },
            returns={"name": {"type": "string"}, "steps": {"type": "array"}},
            permission_level=PermissionLevel.READ, requires_confirmation=False, category="productivity",
            capabilities=["workflow.load"], tags=["workflow", "load"],
        ),
        ToolContract(
            id="workflow.list", name="List Workflows",
            description="List all saved workflows",
            parameters={},
            returns={"workflows": {"type": "array"}, "count": {"type": "integer"}},
            permission_level=PermissionLevel.READ, requires_confirmation=False, category="productivity",
            capabilities=["workflow.list"], tags=["workflow", "list"],
        ),
        ToolContract(
            id="workflow.export", name="Export Workflow",
            description="Export a workflow to a JSON file",
            parameters={
                "name": {"type": "string", "description": "Workflow name"},
                "output": {"type": "string", "description": "Output file path", "required": False},
            },
            returns={"name": {"type": "string"}, "output": {"type": "string"}, "exported": {"type": "boolean"}},
            permission_level=PermissionLevel.READ, requires_confirmation=False, category="productivity",
            capabilities=["workflow.export"], tags=["workflow", "export"],
        ),
        ToolContract(
            id="workflow.import", name="Import Workflow",
            description="Import a workflow from a JSON file (requires confirmation)",
            parameters={
                "path": {"type": "string", "description": "Path to workflow JSON file"},
            },
            returns={"name": {"type": "string"}, "steps": {"type": "integer"}, "imported": {"type": "boolean"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=True, category="productivity",
            capabilities=["workflow.import"], tags=["workflow", "import"],
        ),
        ToolContract(
            id="workflow.run", name="Run Workflow",
            description="Execute a saved workflow (requires confirmation)",
            parameters={
                "name": {"type": "string", "description": "Workflow name"},
            },
            returns={"run_id": {"type": "string"}, "workflow": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.WORKSPACE, requires_confirmation=True, category="productivity",
            capabilities=["workflow.run"], tags=["workflow", "run"],
        ),
        ToolContract(
            id="workflow.cancel", name="Cancel Workflow",
            description="Cancel a running workflow",
            parameters={
                "run_id": {"type": "string", "description": "Workflow run ID to cancel"},
            },
            returns={"run_id": {"type": "string"}, "status": {"type": "string"}},
            permission_level=PermissionLevel.SAFE, requires_confirmation=False, category="productivity",
            capabilities=["workflow.cancel"], tags=["workflow", "cancel"],
        ),
    ]

    all_tools = productivity_tools + automation_tools + workflow_tools

    prod_handlers = [
        _send_notification,
        lambda p, eb=event_bus: _create_timer(p, eb),
        _cancel_timer,
        _list_timers,
        lambda p, eb=event_bus: _recent_files(p, eb),
        _favorite_paths,
        _launch_application,
        _open_file,
    ]

    auto_handlers = [
        _delay,
        lambda p, eb=event_bus: _retry(p, eb),
        lambda p, eb=event_bus: _wait_for_event(p, eb),
        lambda p, eb=event_bus: _schedule_task(p, eb),
        _cancel_task,
        lambda p, eb=event_bus: _file_watch(p, eb),
        lambda p, eb=event_bus: _process_watch(p, eb),
        lambda p, eb=event_bus: _http_watch(p, eb),
    ]

    wf_handlers = [
        _save_workflow,
        _load_workflow,
        _list_workflows,
        _export_workflow,
        lambda p, eb=event_bus: _import_workflow(p, eb),
        lambda p, eb=event_bus: _run_workflow(p, eb, tm),
        _cancel_workflow,
    ]

    all_handlers = prod_handlers + auto_handlers + wf_handlers

    for contract, handler in zip(all_tools, all_handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
