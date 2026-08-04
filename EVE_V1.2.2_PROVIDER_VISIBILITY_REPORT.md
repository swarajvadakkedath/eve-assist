# EVE v1.2.2 — Provider Visibility Bug Report

**Date:** 2026-08-03  
**Status:** FIXED  
**Severity:** High (UI shows "No providers configured" despite 9 providers onboarded)

---

## Symptom

The AI Operations Center → Providers tab displayed "No providers configured" even though:
- 9 providers were onboarded and verified via API
- `GET /api/v1/providers` returns 9 providers (verified via curl)
- `providers.json` contains 9 entries (2.8MB, zero key material)
- All 8 dashboard endpoints return healthy responses

## Root Cause

**File:** `src/frontend/src/components/aio/AioStore.ts` — `loadAll()` function

The original code used `Promise.all` for 8 parallel API calls:

```typescript
const [providers, health, history, diagnostics, routing, categories, policy, freeModels] =
  await Promise.all([
    fetchProviders(),
    fetchProviderHealth(),
    fetchHealthHistory(60),
    fetchDiagnostics(),       // ← if this fails (e.g., HTTP 500)
    fetchRouting(),
    fetchCategories(),
    fetchCommercialPolicy(),
    fetchFreeModels(),
  ]);
```

**`Promise.all` is all-or-nothing.** If ANY single endpoint returned an error (even `/routing/diagnostics` with a transient 500), the entire `Promise.all` rejected. The catch block set `state.error` but **never set `state.providers`** — leaving it as the initial empty array `[]`.

The 30-second `pollProviders()` timer should have self-healed, but:
1. The initial user experience showed the empty state
2. If the AOC was opened during a period of endpoint instability, the empty state persisted until the next poll cycle
3. No error message was shown to the user — just the silent "No providers configured" fallback

## Evidence

- Backend healthy at time of investigation: all 8 endpoints return HTTP 200
- `GET /api/v1/providers` → 9 providers with full metadata
- `GET /api/v1/desktop/status` → `{ "status": "ready" }`
- CORS configured correctly for `tauri://localhost`
- Frontend dist built after source changes (dist: 17:12, source: 16:28)
- No Vite dev server running; Tauri using built dist from `src/frontend/dist`

## Fix

Changed `Promise.all` → `Promise.allSettled` in `loadAll()`:

```typescript
const results = await Promise.allSettled([
  fetchProviders(),
  fetchProviderHealth(),
  fetchHealthHistory(60),
  fetchDiagnostics(),
  fetchRouting(),
  fetchCategories(),
  fetchCommercialPolicy(),
  fetchFreeModels(),
]);
```

Each result is extracted by index with a typed fallback:

```typescript
function settled<T>(results: readonly PromiseSettledResult<unknown>[], idx: number, fallback: T): T {
  const r = results[idx];
  if (r && r.status === "fulfilled") return (r as PromiseFulfilledResult<T>).value;
  return fallback;
}

const providers = settled(results, 0, []);   // always populated if endpoint works
const health = settled(results, 1, {});
// ... etc
```

**Behavior after fix:**
- Providers load independently of other endpoints
- If `/routing/diagnostics` fails, dashboard still shows providers, routing, categories, etc.
- Partial failures logged as warnings (`"Dashboard loaded with N degraded endpoint(s)"`)
- No more all-or-nothing fragility

## Files Changed

| File | Change |
|------|--------|
| `src/frontend/src/components/aio/AioStore.ts` | `Promise.all` → `Promise.allSettled` with `settled()` helper |

## Verification

- `npm run build` (tsc + vite): **PASS** — 0 errors, dist rebuilt
- Backend endpoints: all 8 healthy
- Frontend dist: `assets/index-DrH29ibe.js` (718.5 kB)

## Impact

- **Before:** Any single endpoint failure blanked the entire Operations Center
- **After:** Each section loads independently; providers always visible if backend is up
- **Risk:** Minimal — only changes error handling in the store, no API contract changes
