# EVE v1.2.3 Startup Hang — Root Cause & Fix

## Summary

**Root Cause**: CORS misconfiguration — the Tauri v2 production WebView origin `http://tauri.localhost` was not in the backend's `allow_origins` list.

**Impact**: The frontend's `fetch()` to `/api/v1/desktop/status` received HTTP 200 responses, but the browser blocked JavaScript from reading them (opaque response, `res.status=0`, `res.ok=false`). The `statusStore` never detected `"ready"`, so `useBackendStatus().ready` stayed `false` forever → "Starting EVE..." screen.

**Fix**: Added `"http://tauri.localhost"` to `CORSMiddleware` `allow_origins` in `app.py`.

## Timeline

| Time | Event |
|------|-------|
| 22:20:34 | `eve-desktop.exe` launched (PID 24772) |
| 22:20:35 | Python launcher spawned (PID 27980) |
| 22:20:36 | Backend started (PID 26256), reload=False |
| 22:20:54 | Backend healthy, launcher emits ready signal |
| 22:20:54 | Frontend starts polling `/api/v1/desktop/status` |
| 22:20:57 | Launcher warns: "service down: frontend" |
| 22:20:57+ | Frontend polls 475+ times, all return HTTP 200 |
| — | **App stays stuck on "Starting EVE..."** |
| 22:43 | Investigation identifies CORS as root cause |
| 22:45 | Fix applied, backend reloaded |
| 22:46 | New backend started with fix, frontend reconnects |
| 22:46 | CORS header `Access-Control-Allow-Origin: http://tauri.localhost` confirmed |

## Root Cause Analysis

### The CORS Mismatch

**Tauri v2** with `custom-protocol` feature sets the WebView origin to:
```
http://tauri.localhost
```

The backend's CORS config had:
```python
allow_origins=[
    "http://localhost:5173",      # Vite dev server
    "http://127.0.0.1:5173",     # Vite dev server (IP)
    "tauri://localhost",          # Tauri v1 format (WRONG for v2)
    "https://tauri.localhost",    # HTTPS variant (WRONG: origin is HTTP)
]
```

**Missing**: `http://tauri.localhost` (the actual Tauri v2 production origin)

### How This Broke the App

1. Frontend loads from embedded dist in WebView
2. `statusStore.ts` starts polling `http://127.0.0.1:8456/api/v1/desktop/status`
3. WebView sends request with `Origin: http://tauri.localhost`
4. Backend's CORSMiddleware checks origin → NOT in allow list → **no CORS headers in response**
5. Browser blocks JavaScript from reading the response → **opaque response**
6. `fetch()` resolves, but `res.type === "opaque"`, `res.status === 0`, `res.ok === false`
7. `pollOnce()` code: `if (res.ok) { ... }` → **never executes**
8. `status.ready` stays `false` → `useSyncExternalStore` never triggers re-render
9. App stays on "Starting EVE..." indefinitely

### Why the Backend Logs Were Misleading

The backend DID receive and process all requests (HTTP 200 logged). The CORS issue only affected the **browser's ability to read the response**, not the server-side processing. This made it appear from server logs alone that everything was working.

## Fix

### Source (`src/backend/aios/api/app.py:356`)
```python
# Before
allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "tauri://localhost", "https://tauri.localhost"],

# After
allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "tauri://localhost", "https://tauri.localhost", "http://tauri.localhost"],
```

### Files Changed
- `src/backend/aios/api/app.py` — added `"http://tauri.localhost"` to CORS origins
- `desktop/src-tauri/backend/aios/api/app.py` — mirror copy
- `C:\Users\swara\AppData\Local\Eve\backend\aios\api\app.py` — installed copy

## Verification

```powershell
# Test CORS with Tauri v2 origin
$headers = @{ "Origin" = "http://tauri.localhost" }
$resp = Invoke-WebRequest -Uri "http://127.0.0.1:8456/api/v1/desktop/status" -Headers $headers
$resp.Headers['Access-Control-Allow-Origin']
# Expected: "http://tauri.localhost" ✅
```

## Additional Issues Found During Investigation

1. **`app.py` version string**: Hardcoded `version="1.2.1"` in the FastAPI app constructor, while `__init__.py` is `1.2.3`. The `/api/v1/system/health` endpoint returns the wrong version. Not a functional bug but misleading for diagnostics.

2. **`reload=False` but WatchFiles running**: The backend log showed "Started reloader process [26256] using WatchFiles" even though `main.py` has `reload=False`. This suggests `EVE_ENV` was set to "dev" when the process was first started, or the log entries are from a previous session.

3. **Launcher auto-respawn**: When the backend was killed externally, the launcher (PID 27980) did not auto-respawn it. The backend had to be started manually.

## Lessons Learned

1. **Tauri v2 origin is `http://tauri.localhost`** — not `tauri://localhost` (v1) or `https://tauri.localhost`
2. **CORS issues are invisible in server logs** — the server processes requests normally; only the browser blocks the response
3. **Use `curl -v` or `Invoke-WebRequest -Headers @{Origin=...}`** to test CORS headers during debugging
4. **Add the Tauri v2 origin to CORS config at project setup** — it's easy to miss if you only test in dev mode (localhost:5173)
