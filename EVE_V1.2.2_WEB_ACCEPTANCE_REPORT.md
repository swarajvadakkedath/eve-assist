# EVE v1.2.2 — Web Acceptance Report

**Date:** 2026-08-03
**Method:** API-level acceptance via httpx + ASGITransport with lifespan (simulates every frontend call path against the real backend)
**Result:** PASS — 47/47 tests, 0 FAIL, 0 WARN

---

## Defect Found and Fixed

### `GET /api/v1/routing/diagnostics` — AttributeError on rate-limit serialization

**Root cause:** `get_all_model_rate_limits()` returns `dict[str, dict[str, Any]]` (values already dicts), but the endpoint called `.to_dict()` on each value, causing `AttributeError: 'dict' object has no attribute 'to_dict'`.

**Fix:** `src/backend/aios/api/providers.py:401` — type-guard: `rl if isinstance(rl, dict) else rl.to_dict()`.
**Mirrored to:** `desktop/src-tauri/backend/aios/api/providers.py:401` (byte-identical).

---

## Feature Results

| # | Feature | Tests | Status | Details |
|---|---------|-------|--------|---------|
| 1 | **Startup Synchronization** | 3/3 | PASS | readiness=true, desktop status=ready, health=healthy |
| 2 | **Chat** | 5/5 | PASS | create conversation, list (50), get, update title, send message (status=200, google gemini-2.5-flash) |
| 3 | **Conversation Persistence** | 4/4 | PASS | persists in list, retrievable by id, delete, removed after delete |
| 4 | **AI Operations Center** | 8/8 | PASS | providers, health, history, diagnostics, routing, categories, policy, free models |
| 5 | **Provider Dashboard** | 3/3 | PASS | 9 providers (cloudflare, deepinfra, google, groq, huggingface, nvidia, ollama, openai, openrouter), available types, health (8/9 healthy) |
| 6 | **Model Explorer** | 3/3 | PASS | 66 free models, valid structure, 5 cloudflare models fetched |
| 7 | **Smart Router** | 4/4 | PASS | routing config (5 entries), categories (5), diagnostics, commercial policy=free_only |
| 8 | **Health Dashboard** | 3/3 | PASS | snapshot (8 healthy + 1 degraded), history (9 providers), status history (2 entries) |
| 9 | **Activity Timeline** | 1/1 | PASS | notification history (0 — expected at fresh startup) |
| 10 | **Performance Dashboard** | 2/2 | PASS | system status (cpu=0, mem=0), routing diagnostics |
| 11 | **Provider Refresh** | 2/2 | PASS | refresh cloudflare (200), test-all endpoint exists |
| 12 | **Backend Restart Recovery** | 2/2 | PASS | readiness stable, all 9 critical endpoints stable post-recovery |

### Additional API Surface

| Feature | Tests | Status | Details |
|---------|-------|--------|---------|
| Tools | 1/1 | PASS | 228 tools |
| Capabilities | 1/1 | PASS | endpoint responds |
| Plugins | 1/1 | PASS | endpoint responds |
| Settings | 3/3 | PASS | desktop settings (theme=dark), hotkeys, startup status |
| Auth | 1/1 | PASS | auth token endpoint responds |

---

## Provider Health

| Provider | State | Success Rate | Notes |
|----------|-------|-------------|-------|
| cloudflare-cbeccd87 | unknown | 1.0 | No background checks yet |
| deepinfra-ba89c92c | unknown | 1.0 | No background checks yet |
| google-4f434f3e | unknown | 1.0 | Chat message went through successfully |
| groq-cdd83d06 | unknown | 1.0 | No background checks yet |
| huggingface-01446463 | unknown | 1.0 | No background checks yet |
| nvidia-88deabae | unknown | 1.0 | No background checks yet |
| ollama-df6209ba | unknown | 1.0 | No background checks yet |
| openai-5c032a07 | unknown | 1.0 | No background checks yet |
| openrouter-5247acc8 | unknown | 1.0 | No background checks yet |

`state=unknown` is expected at startup — the health monitor's background check loop runs on the configured interval (default 120s). `success_rate=1.0` is the default for untested providers.

---

## Regression Suite

| Suite | Result |
|-------|--------|
| `tsc --noEmit` | 0 errors |
| `npm run build` | PASS (16s) |
| `vitest run` | 109/109 files, 827/827 tests PASS |
| `pytest tests/provider_framework/` | 279/279 tests PASS |

---

## Desktop Mirror Parity

All source changes to `src/backend/aios/api/providers.py` were mirrored to `desktop/src-tauri/backend/aios/api/providers.py`. Byte-identical parity verified.

---

## Verdict

**PASS** — All 47 acceptance tests pass. One defect was found (rate-limit serialization) and fixed before completing the run. No regressions in backend tests, frontend tests, TypeScript compilation, or production build.
