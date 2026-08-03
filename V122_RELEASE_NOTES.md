# EVE v1.2.2 Release Notes

**Release Date:** August 3, 2026
**Version:** 1.2.2
**Codename:** Production AI Ecosystem

---

## Highlights

### AI Operations Center

A full workspace for monitoring and managing your AI operations. Press **Ctrl+Shift+A** or select "AI Operations" from the workspace switcher.

- **Dashboard** — stat cards for providers, models, health, and uptime at a glance
- **Provider Dashboard** — cards for all 17 providers with health status, capabilities, and model counts
- **Model Explorer** — browse 66+ free models, per-provider model lists with capability flags
- **Smart Router** — routing configuration, 5 capability categories, fallback graph visualization, diagnostics
- **Health Dashboard** — real-time provider health with recharts graphs, success rates, latency tracking
- **Activity Timeline** — notification history, event feed with filtering
- **Performance Dashboard** — system status, routing diagnostics, CPU/memory metrics
- **Settings** — commercial policy management, routing preferences

### Provider Dashboard

17 providers integrated via the Universal Provider Framework:

| Provider | Type | Key Feature |
|----------|------|-------------|
| OpenAI | Cloud | GPT-4o, o1, o3-mini, function calling |
| Google | Cloud | Gemini 2.5, vision, thinking |
| Groq | Cloud | Ultra-low latency inference |
| OpenRouter | Cloud | Multi-provider aggregation |
| Ollama | Local | Self-hosted models |
| DeepInfra | Cloud | Open-source inference |
| Cloudflare | Cloud | Workers AI, free tier |
| HuggingFace | Cloud | Open models, inference API |
| NVIDIA | Cloud | NIM, GPU inference |

Plus8 more providers via OpenAI-compatible adapters.

### Model Explorer

- **66 free models** across all providers
- Per-provider model discovery with capability extraction
- Support flags: reasoning, tools, function_calling, json, streaming, vision, thinking
- Commercial status: FREE, FREE_TIER, CREDIT_BASED, PAID
- Deprecation detection and warnings

### Health Center

- **Per-provider health tracking** with state machine (healthy/degraded/offline/error)
- **Success rate** calculated from successful/total checks
- **Health score** blending success rate (60%) + uptime recency (40%)
- **Background monitoring** with configurable interval (default 120s)
- **Health history** endpoint for trend analysis

### Smart Router

- **Capability-driven routing** — routes based on what the model can do, not model names
- **5 routing categories**: general_chat, coding, reasoning, vision, tools
- **8-level fallback hierarchy**: preferred → same-model → same-provider → FREE → FREE_TIER → CREDIT → LOCAL → PAID
- **FREE_ONLY default** — safe for all installs, opt into paid models
- **Priority weighting** — configurable per-provider priority scores
- **Commercial policy engine** — FREE_ONLY, ALLOW_PAID, LOCAL_ONLY

---

## Startup Synchronization

The "Failed to create conversation" and "Failed to load settings" errors during startup are resolved.

**How it works:**
1. Backend state machine: `STARTING → INITIALIZING → READY | DEGRADED`
2. Middleware blocks all API routes during initialization (returns 503 with status)
3. Frontend `statusStore` polls `/desktop/status` with a single shared poller
4. `waitForReady()` gates all API calls — no requests fire until backend is ready
5. App.tsx shows splash screen ("Starting EVE...") until ready
6. AIO store awaits readiness before loading data
7. On backend restart, statusStore detects regression and re-arms

**Bypass set** (always available during init):
- `GET /api/v1/system/health`
- `GET /api/v1/system/readiness`
- `GET /api/v1/desktop/status`

---

## Performance Improvements

- **Parallel model discovery** — `refresh_all_models()` fetches from all providers concurrently with semaphore (max 4)
- **Background model refresh** — configurable interval (default 3600s), runs on startup
- **Capability inference** — model capabilities extracted from API responses, ID heuristics, and provider metadata
- **Health scoring** — weighted blend prevents stale health from dominating routing decisions

---

## Bug Fixes

### Critical
- **Split-brain HealthMonitor** — `SmartRouter()` and `ProviderManager()` each created their own health monitor, breaking routing/health API consistency. Fixed: single shared monitor passed to both.
- **`_list_standard_models` undefined** — referenced in `list_models()` but never defined. Fixed: extracted from inline code.
- **`_generic_classify` wrong arity** — called with 2 args but defined with 1. Fixed: added `raw` parameter.
- **Rate-limit serialization** — `to_dict()` called on dict values from `get_all_model_rate_limits()`. Fixed: type-guard.

### High
- **FastAPI route shadowing** — `/api/v1/providers/{provider_id}` declared before literal routes, causing 404s. Fixed: reordered routes.
- **Commercial policy not persisted** — default `ALLOW_PAID` not saved to `routing.json`. Fixed: FREE_ONLY default, proper save/load.
- **Background loops never started** — health check and model refresh loops never started in production lifespan. Fixed: wired in lifespan.

### Medium
- **Desktop version string** — mirror `__init__.py` had `1.2.1` instead of `1.2.2`. Fixed.
- **ModelInfo.from_old_format** — computed `commercial_status` but never passed it to constructor. Fixed.
- **Catalog merge semantics** — `_fetch_and_merge` only filled keys absent from discovery, overriding catalog data. Fixed.
- **RouteCandidate.supports_thinking** — missing field prevented reasoning category from having eligible candidates. Fixed.

---

## Developer Notes

### Version Surfaces (all 1.2.2)
- `tauri.conf.json`
- `desktop/Cargo.toml`
- `desktop/package.json`
- `pyproject.toml`
- `src/backend/aios/__init__.py`
- `launcher/__init__.py`
- `src/frontend/package.json`

### Test Coverage
- Backend: 279 tests (provider framework)
- Frontend: 827 tests (109 files)
- TypeScript: 0 errors
- Build: PASS

### Key Files
- `src/backend/aios/api/app.py` — FastAPI app, middleware, lifespan
- `src/backend/aios/api/providers.py` — Provider/routing endpoints
- `src/backend/aios/core/smart_router.py` — Routing engine
- `src/backend/aios/core/provider_manager.py` — Provider lifecycle
- `src/backend/aios/core/health_monitor.py` — Health tracking
- `src/frontend/src/components/aio/` — AOC workspace (18 components)
- `src/frontend/src/services/statusStore.ts` — Readiness gate
- `desktop/src-tauri/src/lib.rs` — Tauri app setup

---

## Upgrade Notes

### From v1.2.1
1. Run the installer (`Eve_1.2.2_x64-setup.exe`)
2. All existing provider configurations are preserved
3. `routing.json` is automatically migrated (legacy list format → dict with FREE_ONLY)
4. First startup will show "Starting EVE..." splash while backend initializes
5. Background health checks start automatically (120s interval)
6. Background model refresh starts automatically (3600s interval)

### From v1.2.0
Same as above, plus:
- Provider registry expanded to 17 providers
- DeepInfra added as new provider
- Capability extraction now runs on all providers

---

## Known Limitations

1. **Background health checks** — providers show `state=unknown` for ~120s after startup until first background check completes
2. **Voice/OCR** — require hardware (microphone/screen) for manual verification
3. **Global shortcuts** — require keyboard hook registration, manual verification needed
4. **System tray** — requires Windows runtime, manual verification needed
5. **Long-running stability** — 1+ hour soak test recommended before production use
6. **Installer** — NSIS installer, Windows only (no macOS/Linux builds)

---

## Release Assets

| File | Size | SHA-256 |
|------|------|---------|
| `Eve_1.2.2_x64-setup.exe` | 136.8 MB | `71B318C8A333F894B3DE365B4756681D85D412ABCB73D1AD34AFCB93DDE67AF3` |

**Download:** https://github.com/swarajvadakkedath/eve-assist/releases/tag/v1.2.2

---

*EVE v1.2.2 — Production AI Ecosystem*
