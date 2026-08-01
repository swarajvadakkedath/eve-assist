## Eve v1.2.1 — Post-Release Launcher Deadlock Remediation

**Release Date:** 2026-08-02 03:04 UTC
**Tag:** v1.2.1
**Commit:** 936a118
**Installer:** Eve_1.2.1_x64-setup.exe
**SHA-256:** 95AFA30FC2A6B4FCBF14A87EC2F866DBFC76DBF092CC1581EB8494066BAA6FA7

### Summary

Eve v1.2.1 is a post-release stabilization release that fixes a **critical launcher deadlock bug** discovered after the v1.2.0 release. The bug caused the launcher's IPC stdin listener to block the async event loop, starving backend stdout pipe readers, filling the OS pipe buffer, and freezing the entire backend.

### Root Cause

The launcher's 	auri_integration.py used a **synchronous** sys.stdin.readline() call inside an async IPC listener. This blocked the event loop thread, preventing ProcessService._read_stream() from draining the backend's stdout pipe. Once the pipe buffer filled (~64 KB), the backend's uvicorn/structlog sys.stdout.write() also blocked, freezing the entire backend process tree.

**Affected feature:** Settings panel ("Failed to load settings") and potentially all backend-dependent features.

### Fix

- **One-line fix:** Changed line = read_line() to line = await asyncio.to_thread(read_line) in launcher/tauri_integration.py
- The stdin read now runs in a thread pool, keeping the event loop free for pipe draining
- No IPC protocol changes; Rust-side code unaffected

### Regression Tests Added

7 new deterministic regression tests in 	ests/launcher/test_stdin_nonblocking.py:
1. Sustained output drain + heartbeat verification
2. IPC responsive during sustained output
3. OLD blocking pattern freeze proof (proves old code is broken)
4. stdin EOF clean exit
5. Shutdown command clean exit
6. Rapid launch/close cycles
7. Full launcher-level regression test

### Verification

- Backend baseline: **364/364 tests PASS**
- Launcher regression: **7/7 tests PASS**
- Existing launcher tests: **91/91 PASS**
- Fix verified in bundled installer payload
