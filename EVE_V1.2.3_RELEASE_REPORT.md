# EVE v1.2.3 Release Report

**Date**: 2026-08-03
**Status**: READY FOR INSTALLATION

---

## Summary

EVE v1.2.3 is a patch release containing production-critical lifecycle hardening. The previous installer (v1.2.2) was built before these changes and does not contain them.

---

## Commits

| Commit | Message |
|--------|---------|
| `831537a` | release: prepare EVE v1.2.3 lifecycle stability |
| `d7e46d1` | release: promote version to v1.2.3 |

---

## Version

| Source | Version |
|--------|---------|
| pyproject.toml | 1.2.3 |
| launcher/__init__.py | 1.2.3 |
| src/backend/aios/__init__.py | 1.2.3 |
| desktop/package.json | 1.2.3 |
| src/frontend/package.json | 1.2.3 |
| desktop/src-tauri/tauri.conf.json | 1.2.3 |
| desktop/src-tauri/Cargo.toml | 1.2.3 |

All 7 surfaces confirmed: **1.2.3**

---

## Installer

| Field | Value |
|-------|-------|
| Filename | `Eve_1.2.3_x64-setup.exe` |
| Size | 130.51 MB (136,852,392 bytes) |
| Built | 2026-08-03 22:13:14 |
| SHA-256 | `305315A611B2C4150AA38C881492092EE98ADDAB33A82218E3631A7A089BB447` |
| Path | `E:\Eve_Ai\desktop\src-tauri\target\release\bundle\nsis\Eve_1.2.3_x64-setup.exe` |

---

## Tests

| Suite | Result |
|-------|--------|
| Provider framework | 279/279 passed |
| Launcher tests | 100/100 passed (4 skipped, 2 deselected pre-existing) |
| Lifecycle stress tests | 16/16 passed |
| TypeScript | Clean |
| Cargo check | Clean (4 pre-existing warnings) |
| **Total** | **395/395 passed** |

---

## Build

| Step | Duration |
|------|----------|
| Frontend build | ~6s |
| Rust compile (release) | ~4m 07s |
| NSIS installer | ~30s |
| **Total** | **~5 minutes** |

---

## Architecture

### Windows Job Object (Phase 4)
- Raw FFI bindings to `CreateJobObjectW`, `SetInformationJobObject`, `AssignProcessToJobObject`
- `JobGuard` struct with `unsafe impl Send + Sync` for thread safety
- `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` flag ensures child processes terminate with parent
- Zero external crate dependency

### Lifecycle Event System
- `LauncherEvent` dataclass with auto-generated ID and timestamp
- 6 new event types: `BACKEND_EXIT`, `BACKEND_RESTART_ATTEMPT`, `BACKEND_RESTART_EXHAUSTED`, `HEARTBEAT_OK`, `HEARTBEAT_MISSED`, `HEARTBEAT_TRANSITION`
- `record_exit()` writes structured JSON to `~/.eve/logs/backend_exit.log`

### Restart Backoff
- Base delay: 2.0s, Max delay: 30.0s
- Exponential: 2s → 4s → 8s → 16s → 30s
- Configurable max attempts (default: 5)

---

## Files Changed

| Category | Files |
|----------|-------|
| Lifecycle hardening | 16 modified + 1 new |
| Version promotion | 7 files |
| **Total** | **24 files** |

---

## Release Recommendation

**Install: `Eve_1.2.3_x64-setup.exe`**

This is the only installer that contains the lifecycle hardening changes. The v1.2.2 installer was built before these changes and is missing:
- Windows Job Object (orphan prevention)
- Production reload=False fix
- Lossy UTF-8 decode
- Exit diagnostics
- Restart backoff
- Heartbeat transitions
- Lifecycle event forwarding

---

## Status

- [x] Changes verified
- [x] Committed
- [x] Version promoted to 1.2.3
- [x] All tests pass (395/395)
- [x] Installer built
- [x] Smoke validation passed
- [x] Release notes generated
- [x] Release report generated
- [ ] NOT pushed
- [ ] NOT tagged
- [ ] NOT created GitHub Release
