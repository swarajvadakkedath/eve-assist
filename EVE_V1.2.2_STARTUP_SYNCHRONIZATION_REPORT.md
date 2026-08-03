# EVE v1.2.2 — Startup Synchronization Report

**Date**: 2026-08-03  
**Status**: IMPLEMENTED — ready for manual validation

---

## Root Cause

The frontend loads and immediately makes API calls (ConversationView calls `GET /chat/conversations`, SettingsPanel calls `GET /desktop/settings`) before the backend's FastAPI lifespan finishes initializing. The lifespan does heavy async work (provider manager, conversation manager, workspace manager, plugin manager, memory system) taking several seconds. During this window, `app.state.conversation_service` doesn't exist → `AttributeError` → raw 500 errors shown to users.

The initial fix (per-call retry, 10×500ms, GET-only) was functional but fragile: it used hardcoded timing, only covered `fetchApi` (not `request<T>`), didn't handle backend restarts, and didn't prevent AioStore from polling before READY.

## Architecture (new)

### Backend state machine

```
STARTING ──► INITIALIZING ──► READY
                                  │
                              DEGRADED (reserved, policy-ready, no emitter yet)
                                  │
                              OFFLINE / ERROR
```

- **STARTING**: process launched, lifespan not yet running.
- **INITIALIZING**: lifespan began, services loading. Set at lifespan entry.
- **READY**: all services available, `app.state` fully populated. Set at lifespan exit.
- **DEGRADED**: defined + included in the frontend's ready-set (policy constant: `READY | DEGRADED`). No emitter in v1.2.2; reserved for future optional-service degradation detection.
- **OFFLINE / ERROR**: post-shutdown or fatal failure.

### Backend: `StartupReadyMiddleware`

Routes in `_BYPASS` (`/system/health`, `/system/readiness`, `/desktop/status`) always pass through — the launcher and frontend poller need these during startup. All other routes return `503 {"detail":"Server initializing","status":"<actual>"}` until `app.state.ready = True`.

### Backend: `/api/v1/system/readiness`

```json
{ "status": "ready", "ready": true }
```

`ready = status in {READY, DEGRADED}`. The frontend's `statusStore` polls this (or `/desktop/status`) for the startup transition. The endpoint bypasses the middleware so it's accessible pre-lifespan.

### Backend: `EVE_STARTUP_DELAY_MS`

Environment variable (default 0, inert in production). Adds an `asyncio.sleep` after `INITIALIZING` is set, before heavy init begins. Used by the stress harness to test various startup windows.

### Frontend: `statusStore.ts`

Singleton `useSyncExternalStore` store with a **single** poller of `/desktop/status` (raw `fetch`, not `fetchApi` — avoids deadlock). Polls every 1s. Exposes:
- `{status, ready}` snapshot via `useBackendStatus()` hook.
- `waitForReady(timeoutMs=30_000)`: shared deferred — all callers share one promise, resolved when `ready` becomes true. Re-arms when status regresses from ready (handles backend restarts).
- `startStatusPolling()` / `stopStatusPolling()`: called at App mount/teardown.
- `subscribeStatusChange()`: used by AioStore for re-ready detection.

### Frontend: `api.ts`

Both `fetchApi` and `request<T>` `await waitForReady()` before fetching. Paths in `BYPASS_PATHS` skip the gate to avoid deadlock. Removed `fetchWithStartupRetry` and its constants.

### Frontend: `StatusIndicator.tsx`

Refactored to consume `useBackendStatus()` — no more duplicate 2s poller. StatusIndicator is always mounted (even during splash) so users see "Starting..." / "Initializing..." / "Ready".

### Frontend: `App.tsx`

- `startStatusPolling()` on mount, `stopStatusPolling()` on teardown.
- While `!ready`: renders splash (header with StatusIndicator + "Starting EVE..." text). WorkspaceRegistry, panels, and AioOperationsCenter are **not mounted** — zero API consumers before READY.
- Once ready: mounts the full workspace as today.

### Frontend: `AioStore.ts`

`start()` awaits `waitForReady()` before `loadAll()` + scheduling its 4 intervals. Subscribes to `statusStore` — when the backend transitions back to ready after a restart, re-runs `loadAll()`. `stop()` clears all intervals and the status subscription.

## Old vs. New Behavior

| Aspect | Old | New |
|--------|-----|-----|
| Frontend gating | Per-call retry 10×500ms, GET-only | Global `waitForReady()` gate, all methods |
| Coverage | `fetchApi` only | `fetchApi` + `request<T>` |
| Status states | `starting` / `ready` | `starting` → `initializing` → `ready` (+ `degraded` reserved) |
| Readiness probe | None | `GET /system/readiness` |
| AioStore | Polls immediately, catches errors | Awaits READY before first poll |
| Backend restart | No re-gate | StatusStore re-arms; AioStore re-runs loadAll |
| Splash screen | None | "Starting EVE..." until READY |
| Duplicate pollers | StatusIndicator (2s) + statusStore (1s) | Single poller in statusStore |
| Test knob | None | `EVE_STARTUP_DELAY_MS` env var |

## Test Results

### Backend
- **279/279 provider_framework tests pass** (269 existing + 10 new startup readiness tests)
- New tests verify: middleware bypass, 503 gating, readiness endpoint, post-lifespan passthrough, delay knob

### Frontend
- **0 TypeScript errors** (`npx tsc --noEmit`)
- **827/827 tests pass** (109 test files)
- **Build PASS** (`npm run build`)
- New `statusStore.test.ts` (8 tests): poller lifecycle, waitForReady resolution, timeout rejection, no duplicate pollers, reset

### Desktop mirror
- `app.py` and `status_service.py` mirrored to `desktop/src-tauri/backend/aios/`
- Byte-identical parity verified via `filecmp.cmp`

## Stress Test

`tools/stress_startup.py` harness:
- Spawns backend with `EVE_STARTUP_DELAY_MS` at 0/1/3/5/10/15s
- Polls `/system/readiness` until `ready: true`, records time
- Verifies bypass endpoints (200) and gated endpoints (200 post-ready)
- Reports per-delay results in a table

Run: `python tools/stress_startup.py`

## Timer Inventory

### Backend
| Timer | Interval | Description |
|-------|----------|-------------|
| health_monitor.background_check | 120s | Provider health polling |
| provider_manager.background_refresh | 3600s | Parallel model discovery |
| EventBus retries | configurable | Event delivery retries |

### Frontend
| Timer | Interval | Description |
|-------|----------|-------------|
| statusStore poller | 1s | `/desktop/status` polling (single, guarded) |
| StatusIndicator | removed | Consumes statusStore (no own timer) |
| AioStore pollHealth | 10s | Provider health (only while AOC mounted) |
| AioStore pollDiagnostics | 15s | Routing diagnostics (only while AOC mounted) |
| AioStore pollProviders | 30s | Provider list (only while AOC mounted) |
| AioStore pollModels | 60s | Free models (only while AOC mounted) |
| voiceService reconnect | exponential | WebSocket reconnection |

**Guards**: statusStore single poller (idempotent `start()`); AioStore `if (intervals.length > 0) return`; `stop()` clears all.

## Restart Behavior

1. **Cold launch**: backend starts → statusStore polls → splash → READY → workspace mounts.
2. **Backend restart mid-session**: StatusService goes STARTING → statusStore detects `ready: false` → gate re-arms → splash shows → backend READY → workspace remounts.
3. **Rapid restart**: statusStore single poller handles rapid status transitions; AioStore's `lastStatusReady` tracker prevents redundant `loadAll()` calls.
4. **Repeated restart (5 cycles)**: Each cycle: statusStore re-arms → splash → READY → AioStore re-runs loadAll. No leaked timers (AioStore stop clears intervals; statusStore stop clears poller).

## Remaining Risks

1. **WebSocket disconnect during startup**: `voiceService.connect()` runs on App mount (WebSocket to `/voice/ws`). The WS may fail if the backend isn't ready — this is handled by the existing reconnect logic and `.catch(() => {})` in App.tsx. Not user-visible.
2. **DEGRADED not emitted**: The status value exists and the frontend policy includes it, but no code path currently sets DEGRADED. Future work: detect optional-service init failures (e.g., vision, voice, plugins) and emit DEGRADED instead of aborting the lifespan.
3. **Timeout path**: If the backend never becomes ready (genuine failure), `waitForReady(30s)` rejects → the splash remains and components see real errors. This is correct behavior for a genuine backend failure — the user sees "Starting EVE..." indefinitely (or until they restart).

## Files Changed

### Backend
| File | Change |
|------|--------|
| `src/backend/aios/desktop/status_service.py` | Added `INITIALIZING`, `DEGRADED` to `AppStatus`; added `is_ready` property |
| `src/backend/aios/api/app.py` | Status-aware middleware, `EVE_STARTUP_DELAY_MS`, lifespan `INITIALIZING→READY`, `/system/readiness` endpoint |
| `tests/provider_framework/test_startup_readiness.py` | New: 10 tests for middleware, readiness, delay knob |

### Frontend
| File | Change |
|------|--------|
| `src/frontend/src/services/statusStore.ts` | New: readiness gate, poller, `waitForReady`, re-arm |
| `src/frontend/src/services/statusStore.test.ts` | New: 8 tests for store lifecycle |
| `src/frontend/src/services/api.ts` | Gated `fetchApi`+`request`, removed retry constants |
| `src/frontend/src/components/desktop/StatusIndicator.tsx` | Consumes statusStore, removed own poller |
| `src/frontend/src/App.tsx` | Splash gate, status store start/stop |
| `src/frontend/src/components/aio/AioStore.ts` | Await ready, re-ready reload, status subscription |
| `src/frontend/src/App.test.tsx` | Added statusStore mock |

### Tools / Docs
| File | Change |
|------|--------|
| `tools/stress_startup.py` | New: startup stress harness |
| `EVE_V1.2.2_STARTUP_SYNCHRONIZATION_REPORT.md` | This report |
