# EVE v1.2.2 Backend Exit Investigation Report

**Date**: 2026-08-03  
**Backend PID**: 17952 (uvicorn reloader) + 6900 (uvicorn server child)  
**Exit time**: 20:20:04 (backend.log LastWriteTime)  
**Launcher PID**: unknown (child of eve-desktop 21520)  
**Eve-desktop PID**: 21520 (spawned 20:18:25)

---

## First Exit Reason

**The backend Python process tree was hard-terminated externally (TerminateProcess / `taskkill`-style kill) at ~20:20:04.** This was not a crash, not a graceful shutdown, and not triggered by any Eve code path. The exact killer (Task Manager, `taskkill`, script, or cleanup tool) cannot be identified from logs — the signature is consistent with all of them.

---

## Process Tree (session 3, 20:18 launch)

```
eve-desktop.exe  PID 21520  (20:18:25)
 └─ python.exe   launcher  (tauri_integration.py)
     └─ python.exe   reloader  PID 17952  (uvicorn --reload, started 20:18:26)
         └─ python.exe   server    PID 6900  (uvicorn worker, started 20:18:26)
```

- 17952 = uvicorn WatchFiles reloader (tracked by launcher's ProcessService)
- 6900 = uvicorn ASGI server child (spawned by reloader, NOT tracked directly)

**Note**: `aios/main.py` always runs with `reload=True` — every backend launch spawns TWO python processes (reloader + server), not one.

---

## Timeline

| Time | Event | Source |
|------|-------|--------|
| 20:18:25 | eve-desktop PID 21520 launched | Process list |
| 20:18:26 | Backend reloader PID 17952 started | backend.log L18910-18911 |
| 20:18:26 | Backend server PID 6900 spawned | backend.log L18912 |
| 20:18:40 | Backend ready in 13.9s | startup_trace.log |
| 20:18:43 | `service down: frontend` logged | launcher.log L12 |
| 20:18:43+ | Health loop continues; backend healthy, frontend down | (no state change → no logs) |
| 20:20:04 | **backend.log stops** — reloader stdout pipe closes | backend.log LastWriteTime |
| 20:20:04–09 | Launcher dies (≤5s, before next health poll) | Absence of `service down: backend` log |
| 20:45+ | All python processes gone; 3 eve-desktop alive | Process list, netstat |

---

## Evidence Table

### 1. Not a crash (no traceback, no WER)

- `backend.log` ends **abruptly mid-traffic** — last line: `GET /api/v1/providers/health/history?limit=60 HTTP/1.1" 200 OK`
- No python traceback, no `SystemExit`, no exception in the log tail
- Windows Application Event Log **empty** for 20:17–20:21 (no Event 1000/1001 crash/stop-working)
- Python crashes produce WER events — none recorded

### 2. Not a graceful shutdown

- uvicorn prints `Shutting down` on SIGINT/SIGTERM before exiting — **not present** anywhere in backend.log for session 3
- Launcher's ShutdownService would log `shutdown requested` → `health monitor stopped` → `backend stopped` → `shutdown complete` — **none present** in launcher.log
- `ProcessService.stop()` (the only Eve-initiated killer, `process_service.py:112` `terminate()`) is only reachable via shutdown/restart paths — all of which log first

### 3. Not an in-code self-termination

- No `os._exit`, no parent-PID watchdog, no job object in backend source (grepped all `*.py` in both installed and source aios)
- Backend's `psutil.terminate_process` tool (`core/windows/adapter.py:192`) is API-exposed — but no POST call appears in the log tail (only GETs)
- Backend's uvicorn WatchFiles reloader would log `Shutting down` + new `Started server process` on a file-change reload — **no reload events** in session 3 (one server start, no shutdowns)

### 4. Process-tree kill signature

- **Launcher** died ≤5s after backend (no `service down: backend` / `restarting backend` log) → launcher + reloader + server died simultaneously
- **All three eve-desktop.exe instances** (14180, 11204, 21520) survived — never exited (no `[8/8] Shutdown complete` in startup.log)
- **All python.exe processes** are gone; **port 8456 not listening**
- Only a python-targeted kill produces this split: python tree dead, eve-desktop alive

### 5. Windows Event Log confirms hard kill

- Application log: **empty** for 20:17:30–20:21:30 (no crash, no WER report)
- System log: **empty** for 20:17:30–20:21:30 (no service events, no shutdown)
- Security log: no process-exit audit records (auditing not enabled)
- Hard-kill (`TerminateProcess` / `taskkill /F`) produces **no event log entry** — matches

---

## Secondary Findings

### A. `uvicorn --reload` creates orphan-prone double process

`aios/main.py:16` always runs with `reload=True`. This creates a reloader (parent) + server (child) process tree. On external kill:

- If reloader killed first → server orphaned (may linger briefly, holds port 8456)
- If server killed first → reloader re-spawns a new server (unexpected restart)
- If tree killed simultaneously → both die (observed behavior)

**Recommendation**: Disable `reload=True` in production (desktop app). The reloader's file-watching is unnecessary when the backend is bundled and immutable.

### B. Rust `eve-backend-watcher` UTF-8 stdout decode failure

`launcher.rs:231` `read_line()` uses `BufRead::read_line` which fails on invalid UTF-8 bytes in the launcher's stdout pipe. This error occurs **every session** within ~0.7s of spawn:

```
[4/8] ERROR: Backend failed: read stdout: stream did not contain valid UTF-8
```

Despite the backend being healthy, the app reports `Backend failed` to the frontend — making the AOC appear stuck. This is the proximate reason a kill-and-relaunch cycle is initiated.

**Recommendation**: Replace `read_line()` with `read_until(b'\n')` + lossy decode, or use `BufReader` with a custom read loop that tolerates non-UTF8 bytes.

### C. No parent-death cleanup / orphan protection

The backend has no mechanism to detect if its parent (launcher) died and clean itself up. When the launcher is hard-killed, the reloader and server orphan and continue running until separately killed. On Windows, orphaned python processes from earlier sessions can linger and hold port 8456, causing bind failures for new sessions.

**Recommendation**: Consider launching the backend in a Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, so the entire process tree is terminated when the launcher exits. Alternatively, have the reloader detect parent death and self-terminate.

### D. Stale installed binary

The installed `eve-desktop.exe` (built 13:32:46) bundles the pre-fix frontend code (Promise.all, not Promise.allSettled). The source dist was rebuilt at 20:12:21 with the fix. The installed binary predates the rebuild by ~7 hours — all Provider tab visibility fixes are absent from the running app.

**Recommendation**: Rebuild and reinstall the desktop app to include the Promise.allSettled fix and other v1.2.2 changes.

---

## Process Kill Pattern

Three launch/kill cycles observed on 2026-08-03:

| Launch | Backend PID | Ready | Last Log | Pattern |
|--------|-------------|-------|----------|---------|
| 18:08:31 | 7528 (reloader) / 25976 (server) | 18:08:46 (12.1s) | 18:08:49 `service down: frontend` | killed before 18:58 |
| 18:58:02 | 2872 (reloader) / 24740 (server) | 18:58:17 (14.1s) | 18:58:20 `service down: frontend` | killed before 20:18 |
| 20:18:25 | 17952 (reloader) / 6900 (server) | 20:18:40 (13.9s) | 20:18:43 `service down: frontend` | killed at 20:20:04 |

**Pattern**: Each session follows the same arc — launch → ready → frontend-down → python tree killed externally. The kills are consistent with a dev workflow of launching the app, observing it, then killing python to free port 8456 before relaunching.

---

## Summary

| Question | Answer |
|----------|--------|
| Did the backend exit normally? | No — no shutdown logs, no uvicorn "Shutting down" |
| Did the backend crash? | No — no traceback, no WER/crash event log entry |
| Was it killed by Eve code? | No — the only Eve killer (ProcessService.stop) logs first; no logs |
| Was it killed externally? | **Yes** — TerminateProcess of the python tree at ~20:20:04 |
| Who killed it? | Cannot be determined from logs (Task Manager, taskkill, script, or cleanup tool) |
| Was the launcher killed too? | Yes — within ≤5s (simultaneous tree kill) |
| Why did the user likely initiate the kill? | The Rust UTF-8 stdout bug causes the app to show "Backend failed" despite a healthy backend, prompting a manual kill-and-relaunch |

---

## Files Referenced

- `E:\Eve_Ai\desktop\src-tauri\src\launcher.rs` — Rust launcher, LauncherProcess kill() on Drop
- `E:\Eve_Ai\desktop\src-tauri\src\lib.rs` — eve_desktop::run(), tray exit → send shutdown + app.exit(0)
- `E:\Eve_Ai\desktop\src-tauri\src\commands.rs` — Tauri IPC commands (shutdown sends "shutdown" + 500ms + exit)
- `C:\Users\swara\AppData\Local\Eve\launcher\services\process_service.py` — ManagedProcess, ProcessService.stop() terminate()
- `C:\Users\swara\AppData\Local\Eve\launcher\services\backend_service.py` — starts `python -m aios.main`
- `C:\Users\swara\AppData\Local\Eve\launcher\services\health_service.py` — health polling loop (no kill capability)
- `C:\Users\swara\AppData\Local\Eve\launcher\services\shutdown_service.py` — ShutdownService.shutdown() (logs first)
- `C:\Users\swara\AppData\Local\Eve\launcher\launcher_service.py` — LauncherService orchestration
- `C:\Users\swara\AppData\Local\Eve\launcher\tauri_integration.py` — stdin/stdout JSON protocol, run_launcher() loop
- `C:\Users\swara\AppData\Local\Eve\backend\aios\main.py` — uvicorn.run(reload=True)
- `C:\Users\swara\.eve\logs\backend.log` — LastWriteTime 20:20:04
- `C:\Users\swara\.eve\logs\launcher.log` — LastWriteTime 20:18:43
- `C:\Users\swara\.eve\logs\startup.log` — UTF-8 errors for all 3 sessions
- `C:\Users\swara\.eve\logs\startup_trace.log` — launcher traces, no exit trace
