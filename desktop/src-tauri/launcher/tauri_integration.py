"""Tauri integration — LauncherService adapter for Tauri Desktop.

This script is spawned as a child process by the Tauri Rust side.
It communicates via stdin/stdout JSON lines.

Protocol:
  Stdin (Rust → Python):  {"type":"command","command":"<cmd>"}
  Stdout (Python → Rust): {"type":"status","state":"<state>",...}
  Stdout (Python → Rust): {"type":"lifecycle","event":"<event>",...}
"""

import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path

from launcher.launcher_service import LauncherService


TRACE_LOG = Path.home() / ".eve" / "logs" / "startup_trace.log"


def trace(msg: str = ""):
    ts = time.strftime("%H:%M:%S", time.localtime())
    line = f"[{ts}] {msg}"
    print(line, file=sys.stderr, flush=True)
    try:
        TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACE_LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def emit(obj: dict):
    line = json.dumps(obj)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def read_line() -> str | None:
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return line.strip()
    except EOFError:
        return None


def _lifecycle_event_handler(event):
    emit({
        "type": "lifecycle",
        "event": event.type,
        "data": event.data,
        "timestamp": event.timestamp,
    })


async def run_launcher():
    trace("=== Eve Launcher Startup Trace ===")
    t0 = time.monotonic()

    trace("[01] Creating LauncherService")
    svc = LauncherService()

    trace("[02] Initializing services")
    await svc.initialize()
    svc.on_event(_lifecycle_event_handler)
    trace(f"[02] Launcher v{svc.status().version}")
    emit({
        "type": "status",
        "state": "initialized",
        "version": svc.status().version,
    })

    trace("[03] Starting backend process")
    ok = await svc.start()
    if ok:
        status = svc.status()
        elapsed = time.monotonic() - t0
        trace(f"[OK] Backend ready in {elapsed:.1f}s")
        emit({
            "type": "status",
            "state": "ready",
            "backend_url": status.backend_url,
            "frontend_url": status.frontend_url,
            "uptime": status.uptime,
            "version": status.version,
        })
    else:
        elapsed = time.monotonic() - t0
        trace(f"[FAIL] Backend failed after {elapsed:.1f}s")
        trace("       Check backend.log for details")
        emit({
            "type": "status",
            "state": "error",
            "error": "launcher start failed",
        })
        return
    trace(f"[{'.' * 50}]")

    while True:
        line = await asyncio.to_thread(read_line)
        if line is None:
            break
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") != "command":
            continue
        cmd = msg.get("command", "")
        if cmd == "status":
            status = svc.status()
            emit({
                "type": "response",
                "command": "status",
                "state": status.state,
                "backend_healthy": status.services.get("backend") == "up",
                "backend_url": status.backend_url,
                "uptime": status.uptime,
            })
        elif cmd == "health":
            await svc.health()
            emit({
                "type": "response",
                "command": "health",
                "services": {n: s.status for n, s in svc.health_service.services.items()},
                "providers": {
                    n: {"connected": p.connected, "error": p.error}
                    for n, p in svc.health_service.providers.items()
                },
            })
        elif cmd == "restart":
            r_ok = await svc.restart()
            emit({"type": "response", "command": "restart", "ok": r_ok})
        elif cmd == "shutdown":
            emit({"type": "response", "command": "shutdown", "ok": True})
            await svc.shutdown()
            break
        elif cmd == "get_config":
            cfg = svc.config
            emit({
                "type": "response",
                "command": "get_config",
                "theme": cfg.get("theme", "dark"),
                "backend_url": cfg.backend_url,
                "frontend_url": cfg.frontend_url,
                "auto_start": cfg.get("auto_start", False),
                "dev_mode": cfg.get("dev_mode", False),
            })
        elif cmd == "lifecycle":
            backend = svc.backend
            emit({
                "type": "response",
                "command": "lifecycle",
                "state": svc.state,
                "uptime": round(backend.uptime, 1),
                "restart_count": backend.restart_count,
                "max_restarts": backend._max_restarts,
                "backend_pid": backend.get_pid(),
            })
        else:
            emit({"type": "response", "command": cmd, "error": "unknown command"})


def main():
    try:
        asyncio.run(run_launcher())
    except KeyboardInterrupt:
        trace("Interrupted")
    except Exception:
        trace(f"Unhandled exception: {traceback.format_exc()}")
        emit({
            "type": "status",
            "state": "error",
            "error": traceback.format_exc(),
        })
    finally:
        emit({"type": "status", "state": "stopped"})


if __name__ == "__main__":
    main()
