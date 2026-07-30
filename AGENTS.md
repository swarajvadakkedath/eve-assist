## Objective
- Redesign the entire AI provider system from single-model-per-provider to Provider→Models→Capabilities hierarchy, with multi-model selection, model discovery, per-conversation model switching, and provider+model routing.

## Important Details
- Every provider (Google, Groq, OpenAI, Anthropic, etc.) exposes multiple models; the old `default_model` field forced one model per provider, which is architecturally wrong.
- New data model: `Provider` holds `models: list[Model]` (dicts with capabilities) instead of a `default_model` string + a list of model-id strings.
- `Model` dataclass carries 20+ capability flags (`supportsVision`, `supportsReasoning`, `supportsFunctionCalling`, `isFree`, `speed`, `quality`, `cost_per_1k_*`, etc.) and an `enabled` toggle.
- **Static `MODEL_CATALOG`** in `model_catalog.py` covers all known models for 16 provider types (Google, OpenAI, Anthropic, Groq, Mistral, Cerebras, Ollama, plus dynamic providers like OpenRouter).
- **Dynamic discovery**: `fetch_models()` queries the provider API, then merges discovered model IDs with the static catalog to preserve capability metadata + user `enabled` state.
- **Migration**: `_migrate_models()` in `ProviderManager._load()` converts old-format model lists (`list[str]`) to new format (`list[dict]`) on startup automatically.
- **Routing** now stores `model_id` alongside `provider_id` per category (`general_chat`, `coding`, `vision`, `reasoning`, `fallback`).
- `register_with_router()` passes the first enabled model as the default for each provider.
- New API endpoints: `PUT /providers/{id}/models` (toggle model), `POST /providers/{id}/models/refresh` (re-fetch from API).
- Google provider httpx timeout reduced from 120s→30s to prevent streaming hangs.
- Frontend `types.ts` created with `Model`, `ProviderInfo`, `RoutingEntry`, `ModelFilters` interfaces matching backend `Model.to_dict()` keys (camelCase).
- `api.ts` provider helpers (`api.providers.*`, `api.routing.*`) added.
- All backend files compile and import successfully (verified via `py_compile` + `import` tests).

## Bug Diagnosis — July 25 2026
### CRITICAL — Auth middleware blocking ALL requests (FIXED)
- **Root cause**: `aios/api/app.py:313-321` — `auth_middleware` required `Authorization: Bearer <token>` header on every request (except health/status). The frontend (`api.ts`) has **no mechanism** to obtain or send the auth token — no token fetch, no header injection, no IPC bridge. Every API call returned `401 Unauthorized`.
- **Impact**: All frontend features broken — Settings (`/api/v1/desktop/settings`), Chat (`/api/v1/chat/*`), Voice (`/api/v1/voice/*`), Providers (`/api/v1/providers`), Vision (`/api/v1/vision/*`).
- **Why it appears to "hang forever"**: The `SettingsPanel` calls `fetchApi("/desktop/settings").then(r => r.json())`. On 401, `r.json()` RESOLVES (not rejects) with `{"detail":"Unauthorized"}`. The next `.then()` sets `settings = {detail: "Unauthorized"}`, which is truthy, so the panel renders with broken undefined data (not "Loading..." or error). User described this as "hangs forever".
- **Fix**: Removed `auth_middleware` entirely (lines 313-321 in original `app.py`). `AuthManager` class kept for the `/api/v1/auth/token` endpoint (still reachable from localhost). CORS middleware unchanged.
- **Verification**: Lifespan completes in 0.64s. All endpoints return `200 OK`: `/api/v1/desktop/status`, `/api/v1/settings`, `/api/v1/providers`, `/api/v1/chat/conversations`.

## Work State
### Completed
- **Backend `model_catalog.py`** — `Model` dataclass with `to_dict()`/`from_dict()`, `MODEL_CATALOG` dict with 60+ known models across 16 provider types, `get_catalog_models()`, `merge_models()`, `model_from_catalog()` helpers.
- **Backend `provider_manager.py`** — stripped `default_model`/`models` from `PROVIDER_META`; updated `add_provider()`, `update_provider()`, `fetch_models()`; added `toggle_model()`, `refresh_models()`, `_merge_models_to_provider()`, `_migrate_models()`; updated `_get_chat_model()`, `register_with_router()`, `set_routing()`.
- **Backend `api/providers.py`** — added `ToggleModelRequest`, `model_updates`/`models_enabled` params, `model_id` in `RoutingEntry`, new endpoints `PUT /providers/{id}/models` and `POST /providers/{id}/models/refresh`.
- **Frontend `types.ts`** — `Model`, `ProviderInfo`, `RoutingEntry`, `ModelFilters`, `ROUTING_CATEGORIES`.
- **Frontend `api.ts`** — typed provider helpers: `api.providers.*` (list, get, add, update, remove, test, testAll, setDefault, reorder, models), `api.routing.*` (get, set).
- **Frontend `ConversationHeader.tsx`** — provider+model dropdown pairs for per-conversation switching.
- **Frontend `AIProviderCard.tsx`** — model checkboxes with toggle, "Show free only" filter, Refresh Models button.
- **Frontend `ModelSelector.tsx`** — search bar + capability filter buttons (Free, Vision, Reasoning, Recommended, 128K+, Fast) with model detail display.
- **Frontend `SmartRoutingPanel.tsx`** — provider+model dropdown pairs per routing category.
- **Frontend `ProviderConfigurationDialog.tsx`** — removed `default_model` field (models managed via card). Now pure API key + endpoint config.
- **Frontend `ManageProvidersPage.tsx`** — imports `ProviderInfo` from `types.ts` instead of inline interface.
- **BUG FIX: Auth middleware removed** (`aios/api/app.py`) — was blocking ALL frontend requests with 401.

### Active
- **ChatWindow/Conversation wiring** — ConversationHeader created but not rendered. Need `provider_id`/`model_id` fields in backend `Conversation` model (`chat.py`) and ChatWindow state to wire the switcher.
- **CSS styling** — new component classes (`.conversation-header`, `.ms-wrapper`, `.ms-filters`, `.ms-item`, `.pr-provider-card-models`, `.pr-model-checkbox`, `.pr-routing-row-controls`) need styles added.
- **AddProviderDialog.tsx** — still passes `default_model` param (no-op).
- **ConnectionTester.tsx** — reads `default_model` from provider response (now `null` after migration). Should read first enabled model instead.

### Blocked
- Cannot start the full backend from within the tool (PowerShell Start-Process killed by sandbox). Use `py_compile` + `import` tests.

## Next Move
1. Wire ConversationHeader into ChatWindow.tsx by passing `currentProviderId`/`currentModelId` (from conversation state) and `onProviderChange`/`onModelChange` handlers.
2. Add CSS for conversation-header, ms-*, pr-model-checkbox, pr-routing-row-controls classes.
3. Update AddProviderDialog.tsx to remove `default_model` from POST body.
4. Update ConnectionTester.tsx to log first enabled model instead of `default_model`.
5. Add `provider_id`/`model_id` fields to backend Conversation model in `chat.py`.

## Relevant Files
- `src/backend/aios/core/model_catalog.py`: Model dataclass, MODEL_CATALOG (60+ models, 16 provider types).
- `src/backend/aios/core/provider_manager.py`: Full provider lifecycle + model management + routing.
- `src/backend/aios/api/providers.py`: Route definitions — CRUD, test, fetch/toggle/refresh models, routing.
- `src/frontend/src/components/providers/types.ts`: Shared TS interfaces (ProviderInfo, Model, RoutingEntry).
- `src/frontend/src/components/providers/AIProviderCard.tsx`: Model checkboxes with toggle + Refresh.
- `src/frontend/src/components/providers/ModelSelector.tsx`: Search + capability filter buttons.
- `src/frontend/src/components/providers/SmartRoutingPanel.tsx`: Provider+model per category.
- `src/frontend/src/components/providers/ManageProvidersPage.tsx`: Main page using ProviderInfo from types.
- `src/frontend/src/components/providers/ProviderConfigurationDialog.tsx`: API key + endpoint form (no model).
- `src/frontend/src/components/chat/ConversationHeader.tsx`: Per-conversation provider/model switcher.
- `src/frontend/src/services/api.ts`: Provider + routing API helpers.
- `src/backend/aios/core/providers/google_provider.py`: httpx timeout 120→30s.
