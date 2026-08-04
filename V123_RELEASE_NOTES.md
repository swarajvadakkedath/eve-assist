# EVE v1.2.3 — Lifecycle Stability Release

**Release Date**: 2026-08-03
**Version**: 1.2.3
**Type**: Patch (lifecycle hardening)

---

## Highlights

### Lifecycle Stability

- **Production reload=False**: Backend now runs as a single process in production, eliminating the dual-process reloader and halving process count
- **Windows Job Object**: When the desktop app exits, all child Python processes (launcher + backend) are terminated by the kernel — zero orphaned processes
- **Exponential backoff restart**: Backend auto-restarts on crash with configurable backoff (2s → 4s → 8s → 16s → 30s max), preventing infinite restart loops

### Launcher Reliability

- **UTF-8 stdout handling**: Launcher stdout reader now uses lossy UTF-8 decoding — never fails on non-UTF-8 bytes, logs a warning instead
- **Exit diagnostics**: Every backend exit is diagnosed and logged to `~/.eve/logs/backend_exit.log` with exit code, termination type, uptime, restart count, and PIDs
- **Structured exit recording**: `record_exit()` writes JSON lines for debugging production issues

### Backend Management

- **Heartbeat transitions**: Health service emits `HEARTBEAT_TRANSITION` events on every status change (healthy↔down), enabling real-time UI updates
- **Consecutive failure tracking**: Three consecutive missed heartbeats trigger a down state, with per-check `HEARTBEAT_OK`/`HEARTBEAT_MISSED` events
- **Restart exhaustion**: Launcher gives up after max restart attempts to avoid infinite loops

### Process Cleanup

- **Job Object architecture**: Raw Windows API FFI (`CreateJobObjectW` + `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`) — no external crate dependency
- **Kernel-managed cleanup**: Job Object handles all descendants (grandchildren, etc.), not just direct children
- **Survives parent exit**: Job Object handle closes automatically when the Rust process drops

### UTF-8 Robustness

- **Lossy decode**: `String::from_utf8_lossy` replaces invalid bytes with replacement character
- **No more crashes**: The "stream did not contain valid UTF-8" error that caused false "Backend failed" reports is eliminated

---

## Known Limitations

- **Pre-existing test failures**: `test_status_before_initialize` expects version `1.2.1` (stale test), `test_startup_backend_fails` has long timeout, `test_github_models_headers_set` is a pre-existing backend test failure
- **Settings pipeline tests**: 4 tests skipped (require running backend)
- **Cargo warnings**: 4 pre-existing warnings (unused import, variable, constant, function) — not introduced by this release

---

## Files Changed

| File | Change |
|------|--------|
| `src/backend/aios/main.py` | `reload=False` production default via `EVE_ENV` |
| `desktop/src-tauri/src/launcher.rs` | Windows Job Object + lossy UTF-8 decode |
| `launcher/launcher_events.py` | New event types + `record_exit()` |
| `launcher/services/backend_service.py` | Exit diagnostics + restart backoff |
| `launcher/services/health_service.py` | Heartbeat transitions + failure tracking |
| `launcher/launcher_service.py` | Lifecycle event dispatch + recovery |
| `launcher/services/shutdown_service.py` | Lifecycle logging |
| `launcher/tauri_integration.py` | Lifecycle forwarding + `lifecycle` command |
| `launcher/services/process_service.py` | Minor lifecycle fix |
| `src/frontend/src/components/aio/AioStore.ts` | Provider visibility fix |
| `tests/launcher/test_backend_lifecycle_stress.py` | 16 new stress tests |
| 7 version files | `1.2.2` → `1.2.3` |
