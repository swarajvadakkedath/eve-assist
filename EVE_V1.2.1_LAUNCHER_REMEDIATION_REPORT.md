# Eve v1.2.1 — Post-Release Launcher Deadlock Remediation Report

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm UTC')
**Agent:** opencode/mimo-v2-pro-free (plan mode + execution)
**Branch:** v1.2.0/agent-core

---

## 1. Executive Summary

Eve v1.2.1 is a post-release stabilization release addressing a **critical launcher deadlock bug** discovered after the v1.2.0 release. The bug caused the launcher's IPC stdin listener to block the async event loop, starving backend stdout pipe readers, filling the OS pipe buffer, and freezing the entire backend process tree.

**Impact of original bug:** Settings panel "Failed to load settings" error; potential freeze of all backend-dependent features.

**Fix:** One-line change from synchronous `sys.stdin.readline()` to `await asyncio.to_thread(read_line)`.

**Verification:** 364/364 backend tests + 7/7 new regression tests + 91/91 existing launcher tests — all PASS.

---

## 2. Timeline

| Phase | Status | Commit |
|-------|--------|--------|
| v1.2.0 Release | Complete | `7279244` (tag `v1.2.0`) |
| Root Cause Diagnosis | Complete | — |
| Fix Implementation | Complete | `7893426` |
| Regression Tests | Complete | 7 new tests |
| Version Promotion | Complete | `936a118` |
| Build | Complete | `Eve_1.2.1_x64-setup.exe` (136.7 MB) |
| Tag | Complete | `v1.2.1` on `936a118` |
| GitHub Release | Complete | Live at v1.2.1 |

---

## 3. Root Cause

### 3.1 The Bug

`launcher/tauri_integration.py:96` — synchronous `sys.stdin.readline()` inside an async IPC listener.

```python
# BEFORE (broken):
line = read_line()  # blocks event loop

# AFTER (fixed):
line = await asyncio.to_thread(read_line)  # non-blocking
```

### 3.2 Failure Chain

1. Launcher starts IPC listener reading stdin from Rust Tauri host
2. `read_line()` blocks the asyncio event loop thread
3. `ProcessService._read_stream()` (draining backend stdout) cannot run — starved
4. Backend stdout pipe buffer fills (~64 KB)
5. Backend uvicorn/structlog `sys.stdout.write()` blocks on full pipe
6. Backend event loop freezes
7. HTTP requests hang → "Failed to load settings"

### 3.3 Process Tree

```
34724 (launcher.tauri_integration)
  └─ 34428 (python -m aios.main, reloader parent, port 8456)
       └─ 6464 (multiprocessing fork worker, actual uvicorn server)
```

---

## 4. Fix Details

- **File:** `launcher/tauri_integration.py` (line 96)
- **Change:** `line = read_line()` → `line = await asyncio.to_thread(read_line)`
- **Scope:** Single line change; no IPC protocol changes; Rust-side code unaffected
- **Risk:** Minimal — `asyncio.to_thread` is the standard pattern for blocking I/O in async contexts

---

## 5. Regression Tests

7 new deterministic tests in `tests/launcher/test_stdin_nonblocking.py`:

| # | Test | Purpose |
|---|------|---------|
| 1 | `test_fixed_pattern_drains_sustained_output_keeps_heartbeat` | Verifies >512KB sustained output doesn't block event loop |
| 2 | `test_fixed_pattern_ipc_responsive_during_sustained_output` | IPC commands processed within 2s during heavy output |
| 3 | `test_old_blocking_pattern_freezes_event_loop` | Proves old synchronous pattern IS broken (positive proof) |
| 4 | `test_stdin_eof_clean_exit` | EOF on stdin triggers clean shutdown |
| 5 | `test_shutdown_command_clean_exit` | `{"command":"shutdown"}` triggers clean exit |
| 6 | `test_rapid_launch_close_cycles` | 3 rapid cycles complete without hang |
| 7 | `test_sustained_output_with_ipc_round_trip` | Full end-to-end: output + IPC + heartbeat |

**All 7 tests PASS** in ~9 seconds.

---

## 6. Test Results

### 6.1 Backend Baseline (pre-existing)
```
pytest src/backend/aios/tests/ → 364/364 PASS (41.32s)
```

### 6.2 New Regression Tests
```
pytest tests/launcher/test_stdin_nonblocking.py → 7/7 PASS (8.92s)
```

### 6.3 Existing Launcher Tests
```
pytest tests/launcher/ (excluding new) → 91/91 PASS
```

### 6.4 Total
```
All tests: 364 + 7 + 91 = 462 PASS, 0 FAIL
```

---

## 7. Build & Artifact

| Property | Value |
|----------|-------|
| Installer | `Eve_1.2.1_x64-setup.exe` |
| Size | 136,737,221 bytes (130.4 MB) |
| SHA-256 | `95AFA30FC2A6B4FCBF14A87EC2F866DBFC76DBF092CC1581EB8494066BAA6FA7` |
| NSIS Output | `desktop/src-tauri/target/release/bundle/nsis/` |
| Binary | `desktop/src-tauri/target/release/eve-desktop.exe` |
| Build Time | ~6 minutes |

### 7.1 Fix Verification in Payload
- `asyncio.to_thread(read_line)` — **PRESENT** in bundled `launcher/tauri_integration.py`
- Old blocking pattern — **ABSENT**

---

## 8. Version Promotion

| Surface | Old | New |
|---------|-----|-----|
| pyproject.toml | 1.2.0 | 1.2.1 |
| src/backend/aios/__init__.py | 1.2.0 | 1.2.1 |
| launcher/__init__.py | 1.2.0-rc.2 | 1.2.1 |
| desktop/src-tauri/tauri.conf.json | 1.2.0 | 1.2.1 |
| desktop/src-tauri/Cargo.toml | 1.2.0 | 1.2.1 |
| desktop/src-tauri/Cargo.lock | 1.2.0-rc.1 | 1.2.1 |
| desktop/package.json | 1.2.0 | 1.2.1 |
| src/frontend/package.json | 1.2.0 | 1.2.1 |
| 8 backend mirrors | 1.2.0 | 1.2.1 |
| launcher mirror | 1.2.0-rc.2 | 1.2.1 |
| 7 test files | 1.2.0 | 1.2.1 |

---

## 9. Git History

```
936a118 (HEAD, tag: v1.2.1) release: prepare Eve v1.2.1
7893426 fix(launcher): prevent stdin IPC from blocking event loop
7279244 (tag: v1.2.0) release: Eve v1.2.0 — Stable Release
```

---

## 10. Known Limitations

1. **Windows-only:** NSIS installer; no macOS/Linux builds
2. **Sandbox constraint:** Full backend/app could not be started from within the tool; live-runtime testing deferred to user
3. **package-lock.json:** Large diff (4353 lines) from PowerShell normalization — cosmetic only, no functional impact

---

## 11. Recommendations

1. **Immediate:** Install `Eve_1.2.1_x64-setup.exe` and verify Settings panel loads correctly
2. **Short-term:** Add `asyncio.to_thread` lint rule to prevent future blocking-in-async patterns
3. **Medium-term:** Consider pipe buffer monitoring/alerting for early detection of stdout starvation
4. **Long-term:** Implement structured IPC health checks with automatic pipe drain recovery

---

## 12. Artifacts

| Artifact | Location |
|----------|----------|
| Installer | `desktop/src-tauri/target/release/bundle/nsis/Eve_1.2.1_x64-setup.exe` |
| Release Notes | `V121_RELEASE_NOTES.md` |
| This Report | `EVE_V1.2.1_LAUNCHER_REMEDIATION_REPORT.md` |
| Regression Tests | `tests/launcher/test_stdin_nonblocking.py` |
| GitHub Release | https://github.com/swarajvadakkedath/eve-assist/releases/tag/v1.2.1 |
