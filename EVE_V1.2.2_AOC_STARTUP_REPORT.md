# EVE v1.2.2 — AOC Startup Investigation Report

**Date:** 2026-08-03 20:25 UTC  
**Status:** ROOT CAUSE IDENTIFIED  
**Symptoms:** AOC opens, Providers tab empty, Last refresh "never", Status "Starting..."

---

## Executive Summary

**The Python backend process is dead.** Port 8456 is not listening. No python process exists. The frontend's statusStore polls `/desktop/status` every 1 second — every poll fails silently (catch block swallows errors). `status.ready` never becomes `true`. The `waitForReady()` gate never opens. `loadAll()` never executes. The AOC never performs its first refresh.

**Compounding factor:** The installed `eve-desktop.exe` (built 13:32:46) bundles the OLD frontend dist (before `Promise.allSettled` fix). The source dist was rebuilt at 20:12:21 with the fix, but the installed binary was not rebuilt.

---

## Investigation Results

### 1. Is GET /system/readiness returning READY?

**NO.** Backend is dead.

```
GET http://127.0.0.1:8456/api/v1/system/readiness → "Unable to connect to the remote server"
GET http://127.0.0.1:8456/api/v1/desktop/status    → "Unable to connect to the remote server"
GET http://127.0.0.1:8456/api/v1/system/health      → "Unable to connect to the remote server"
```

**Evidence:**
- No python process running (`Get-Process python` → empty)
- Port 8456 not LISTENING (only TIME_WAIT connections from frontend retrying)
- Backend log last written: `2026-08-03 20:20:04` (1.5 min ago)
- Backend PID 17952 no longer exists (`Get-CimInstance Win32_Process` → empty)

### 2. Is statusStore receiving READY?

**NO.** Every poll fails silently.

**Code path** (`statusStore.ts:83-116`):

```typescript
async function pollOnce() {
  try {
    const res = await fetch(`${STATUS_BASE}/desktop/status`);  // ← FAILS (connection refused)
    // ... never reached
  } catch {
    // Network error during poll — status stays as-is; next poll will retry.
    // ← SWALLOWS THE ERROR. status.ready stays false.
  }
}
```

**State transitions:**
- Initial: `{ status: "starting", ready: false }`
- Every poll: catches connection error → status unchanged → `{ status: "starting", ready: false }`
- `status.ready` = `false` forever

### 3. Is AioStore.start() called?

**NO.** The AOC never mounts because `ready` is `false`.

**Code path** (`App.tsx:192-198`):

```tsx
{!ready ? (
  <div style={{ ... }}>Starting EVE...</div>     // ← SHOWN (ready=false)
) : (
  <>
    <WorkspaceRegistry ... />                     // ← NEVER REACHED
    ...
  </>
)}
```

**Chain:**
1. `App.tsx` line 39: `const { ready } = useBackendStatus()` → `false`
2. `App.tsx` line 192: `{!ready ? ...}` → renders "Starting EVE..."
3. `WorkspaceRegistry` never mounts
4. `AIOperationsCenter` never mounts
5. `aioStore.start()` never called

### 4. Does loadAll() execute?

**NO.** Never called. `start()` never called. `waitForReady()` never called.

**Full dead path:**
```
Backend dead
  → pollOnce() fails, swallows error
    → status.ready = false
      → ready = false (in App.tsx)
        → WorkspaceRegistry not rendered
          → AIOperationsCenter not mounted
            → aioStore.start() not called
              → waitForReady() not called
                → loadAll() not called
                  → providers = []
                  → lastRefresh = 0 ("never")
```

### 5. Is waitForReady() still pending?

**Not applicable** — never called in this scenario. But if it were called:

```typescript
export function waitForReady(timeoutMs = 30_000): Promise<void> {
  if (status.ready) return Promise.resolve();  // ← false, so falls through
  return createReadyPromise(timeoutMs);         // ← creates 30s timeout promise
}
```

It would create a promise that:
- Resolves when `status.ready` becomes `true` (never, backend dead)
- Times out after 30 seconds with error: `"Backend not ready after 30000ms — status: starting"`
- `start()` would throw → intervals never set up → `loadAll()` never runs

### 6. Frontend dist hash vs loaded bundle

| Item | Value |
|------|-------|
| **Source dist JS** | `index-DrH29ibe.js` (718.5 kB) |
| **Source dist built** | 2026-08-03 20:12:21 |
| **Source dist MD5** | `7F320225A2E3FF05B8149CCA2B5C7766` |
| **Installed exe build** | 2026-08-03 13:32:46 |
| **Vite dev server** | NOT RUNNING (port 5173 not listening) |

### 7. Is Promise.allSettled fix in the installed bundle?

**NO.** The installed binary was built BEFORE the fix.

| Location | Promise.allSettled? | Build time |
|----------|-------------------|------------|
| Source dist (`src/frontend/dist/`) | **YES** | 20:12:21 |
| Installed binary (`AppData\Local\Eve\eve-desktop.exe`) | **NO** | 13:32:46 |

**Evidence:** The old bundle hash `index-Cq5I0eN6.js` no longer exists (overwritten by rebuild). The new bundle `index-DrH29ibe.js` contains `allSettled`. But the installed exe was built at 13:32:46, which is 6 hours before the fix was applied.

In Tauri v2, `frontendDist` files are embedded into the binary at `tauri build` time. The binary at runtime serves the embedded files — it does NOT read from `src/frontend/dist` on disk.

### 8. Is the installed app serving the rebuilt dist?

**NO.** The installed app serves the dist that was bundled at build time (13:32:46). The source dist rebuild (20:12:21) has no effect on the installed binary.

**Tauri v2 embedding flow:**
```
tauri build
  → beforeBuildCommand: "npm run build:frontend" (builds dist)
  → bundles frontendDist/* into eve-desktop.exe
  → binary serves embedded files via custom protocol (tauri://localhost)
```

At runtime, the exe does NOT read from `../../src/frontend/dist`. It serves from its embedded resources.

---

## Execution Timeline

| Time | Event |
|------|-------|
| 18:08:31 | eve-desktop.exe started (PID 14180) |
| 18:08:34 | Backend started (PID 7528), ready in 12.1s |
| 18:58:02 | eve-desktop.exe started (PID 11204) |
| 18:58:03 | Backend started (PID 2872), ready in 14.1s |
| 20:18:25 | eve-desktop.exe started (PID 21520) |
| 20:18:26 | Backend started (PID 17952), ready in 13.9s |
| 20:18:40 | Backend ready (startup_trace) |
| 20:18:43 | Launcher: "service down: frontend" |
| 20:20:04 | **Backend log last written** |
| ~20:20:05 | **Backend process dies** (PID 17952 gone) |
| 20:21:38 | Investigation begins — backend dead, port not listening |

---

## Root Cause

**Primary:** The Python backend process (PID 17952) crashed or was killed at approximately 20:20:05. No crash trace found in `backend.log` — last entry is a normal API response. The process simply vanished.

**Secondary:** The installed `eve-desktop.exe` was built at 13:32:46, before the `Promise.allSettled` fix was applied at 20:12:21. Even if the backend were alive, the old `Promise.all` code would blank the AOC if any single endpoint returned an error.

**First point where startup stops:** `statusStore.ts:113-114` — the `catch` block in `pollOnce()` swallows the connection error. `status.ready` stays `false`. The entire frontend is gated on this flag.

---

## Minimal Fix

### Fix 1: Restart the backend

The backend process is dead. Restart it:

```powershell
# From the install directory
& "C:\Users\swara\AppData\Local\Eve\python\python.exe" -m aios.main
```

Or restart the eve-desktop app (which auto-starts the backend via the launcher).

### Fix 2: Rebuild and reinstall the binary

The installed exe has the old frontend code. To apply the `Promise.allSettled` fix:

```bash
cd desktop/src-tauri
cargo tauri build
# Then run the new installer
```

Or for development, use `cargo tauri dev` which loads from the Vite dev server and picks up source changes live.

### Fix 3: Make statusStore resilient (optional)

The `catch` block in `pollOnce()` silently swallows errors. Consider:

```typescript
} catch (e) {
  // After N consecutive failures, set status to "offline" or "error"
  // so the UI shows a meaningful message instead of "Starting..."
}
```

---

## Files Referenced

| File | Role |
|------|------|
| `src/frontend/src/services/statusStore.ts` | Polls `/desktop/status`, gates `waitForReady()` |
| `src/frontend/src/components/aio/AioStore.ts` | `loadAll()` with `Promise.allSettled` (fixed in source) |
| `src/frontend/src/App.tsx:192` | Renders "Starting EVE..." when `!ready` |
| `src/frontend/src/components/aio/AIOperationsCenter.tsx:42` | Calls `aioStore.start()` on mount |
| `C:\Users\swara\.eve\logs\backend.log` | Last entry 20:20:04, no crash trace |
| `C:\Users\swara\.eve\logs\startup.log` | UTF-8 stdout parse error (non-blocking) |
| `C:\Users\swara\.eve\logs\launcher.log` | "service down: frontend" at 20:18:43 |
| `C:\Users\swara\AppData\Local\Eve\eve-desktop.exe` | Built 13:32:46, bundles OLD dist |
