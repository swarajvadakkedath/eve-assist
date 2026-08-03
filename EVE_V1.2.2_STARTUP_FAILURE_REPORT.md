# EVE v1.2.2 Startup Failure Report

**Date**: 2026-08-03  
**Status**: FIXED

## Symptom

After installing v1.2.2 and launching, the frontend immediately showed:
- `Failed to create conversation`
- `Failed to load settings`

The backend status indicator eventually reached "Ready", but by then the errors were already displayed.

## Root Cause

**Race condition between frontend API calls and backend lifespan initialization.**

The backend's FastAPI lifespan performs heavy async initialization (event bus, provider manager, conversation manager, workspace manager, plugin manager, memory system, etc.) taking several seconds. During this window, `app.state` is partially populated — critical attributes like `conversation_service` and `provider_manager` are not yet set.

Meanwhile, the frontend loads and immediately makes API calls:
1. `ConversationView` calls `GET /chat/conversations` on mount via `useEffect` → hits `req.app.state.conversation_service` → `AttributeError: 'State' object has no attribute 'conversation_service'` → 500
2. User opens settings → `SettingsPanel` calls `GET /desktop/settings` → fails during initialization window → 500

Without a startup gate, the backend threw raw `AttributeError` exceptions instead of clean HTTP responses, and the frontend had no retry logic for transient startup failures.

## Fix (Two-Part)

### 1. Backend: `StartupReadyMiddleware` (`src/backend/aios/api/app.py`)

Added a Starlette `BaseHTTPMiddleware` that:
- Sets `app.state.ready = False` at lifespan start
- Sets `app.state.ready = True` after full initialization (before yield)
- Returns clean `503 {"detail":"Server starting","status":"starting"}` for all endpoints during startup
- **Always allows** `/api/v1/system/health` and `/api/v1/desktop/status` through so the `StatusIndicator` can track the startup→ready transition

```python
class StartupReadyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in ("/api/v1/system/health", "/api/v1/desktop/status"):
            return await call_next(request)
        if not getattr(request.app.state, "ready", False):
            return JSONResponse({"detail": "Server starting", "status": "starting"}, status_code=503)
        return await call_next(request)
```

### 2. Frontend: Startup retry in `fetchApi` (`src/frontend/src/services/api.ts`)

Modified `fetchApi` to transparently retry GET requests that receive a 503 with `{"status":"starting"}`:
- Up to 10 retries, 500ms apart (5 seconds total)
- Only retries GET requests (POST/PUT/DELETE are not retried to avoid duplicate mutations)
- Clones the response body to check for `{"status":"starting"}` without consuming it

This means `ConversationView.fetchConversations()` and `SettingsPanel.loadSettings()` automatically wait for the backend to finish initializing.

## Verification

| Test | Result |
|------|--------|
| Backend without lifespan (pre-init) | Health 200, Status 200, all other endpoints 503 `{"status":"starting"}` |
| Backend with lifespan (post-init) | All endpoints 200 |
| Provider framework tests | 269/269 pass |
| Frontend TypeScript | 0 errors |
| Frontend test suite | 108 files, 819 tests pass |
| Frontend build | PASS |
| Desktop mirror parity | Byte-identical |

## Affected Files

| File | Change |
|------|--------|
| `src/backend/aios/api/app.py` | Added `StartupReadyMiddleware`, `app.state.ready` flag |
| `src/frontend/src/services/api.ts` | Added `fetchWithStartupRetry` with 503 startup detection |
| `desktop/src-tauri/backend/aios/api/app.py` | Mirrored from above |
