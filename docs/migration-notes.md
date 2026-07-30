# Eve AI — Migration Notes

**Version:** Production Release (post-architecture-redesign)
**Previous version:** Single-model-per-provider architecture

## Overview

This release completely redesigns the AI provider system. The old architecture
had one `default_model` per provider and stored models as a flat list of strings.
The new architecture uses a Provider→Models→Capabilities hierarchy with:

- Multi-model selection (per provider)
- Model discovery (static catalog + dynamic API fetch)
- Per-conversation model switching
- Capability-based routing (SmartRouter)
- Centralized streaming (StreamingManager)

## What Changed

### Data Model Changes

| Old | New |
|---|---|
| `provider.default_model: str` | Removed entirely |
| `provider.models: list[str]` | `provider.models: list[dict]` (rich model objects) |
| Model IDs as bare strings | Model dicts with 20+ capability flags |
| Fixed `provider_id` → category routing | `provider_id` + `model_id` per category |
| One adapter per type, hardcoded | Adapter factory creates per-instance adapters |
| No model cache | `ModelCache` with 300s TTL + background refresh |
| No health isolation | `HealthMonitor` with per-provider tracking |
| Streaming logic per adapter | `StreamingManager` — single centralized source |

### File Changes

- `src/backend/aios/core/model_catalog.py` — **New file.** `Model` dataclass,
  `MODEL_CATALOG` with 60+ models across 16 provider types.
- `src/backend/aios/core/provider_manager.py` — **Rewritten.** No `default_model`.
  No `models` in `PROVIDER_META`. Added `fetch_models()`, `toggle_model()`,
  `refresh_models()`, `_migrate_models()`, adapter factory.
- `src/backend/aios/core/smart_router.py` — **New file.** Capability-based routing
  with 4 strategies and fallback chain.
- `src/backend/aios/core/streaming_manager.py` — **New file.** Abort controller,
  heartbeat, timeout, reconnect, SSE helpers.
- `src/backend/aios/core/health_monitor.py` — **New file.** Per-provider health
  with isolated tracking.
- `src/backend/aios/core/adapters/base.py` — **Rewritten.** `ChatRequest`/`ChatResponse`
  dataclasses, `AIProviderAdapter` abstract base with full method set.
- `src/backend/aios/core/cache.py` — **New file.** `ModelCache` with stale-while-revalidate.
- `src/backend/aios/conversation/models.py` — **Updated.** `Conversation` gains
  `provider_id`, `model_id`, `temperature`, `top_p`, `top_k`, `max_tokens`,
  `system_prompt`, `thinking_mode` fields.
- `src/backend/aios/api/providers.py` — **Rewritten.** All CRUD + test + fetch +
  toggle + refresh + routing endpoints.
- `src/backend/aios/api/chat.py` — **Updated.** `POST /chat/stream` supports
  `provider_id`/`model_id` override. Conversation model fields exposed.

### Frontend Changes

- `src/frontend/src/components/providers/types.ts` — **New file.** `Model`,
  `ProviderInfo`, `RoutingEntry`, `ModelFilters` interfaces.
- `src/frontend/src/components/providers/AIProviderCard.tsx` — **New file.**
  Model checkboxes, free filter, Refresh button.
- `src/frontend/src/components/providers/ModelSelector.tsx` — **New file.**
  Search + capability filter buttons + model detail display.
- `src/frontend/src/components/providers/SmartRoutingPanel.tsx` — **New file.**
  Provider+model dropdown pairs per routing category.
- `src/frontend/src/components/providers/ProviderConfigurationDialog.tsx` —
  **Updated.** `default_model` field removed. Only API key + endpoint.
- `src/frontend/src/components/providers/ManageProvidersPage.tsx` — **Updated.**
  Uses `ProviderInfo` from types.ts.
- `src/frontend/src/components/chat/ConversationHeader.tsx` — **New file.**
  Provider+model switcher per conversation.
- `src/frontend/src/services/api.ts` — **Updated.** Typed `api.providers.*` and
  `api.routing.*` helpers.

## What to Expect on Upgrade

### Automatic Model Migration

On first startup, `ProviderManager._load()` detects old-format model lists and
runs `_migrate_models()`:

1. Detects if `models[0]` is a `str` (old format) vs `dict` (new format).
2. For each old-format model ID, looks it up in the static catalog.
   - **Found:** Uses catalog entry (rich metadata + enabled=true).
   - **Not found:** Creates minimal entry with `{id, displayName, provider, enabled: true}`.
3. If a provider has no models at all, populates them from the catalog.
4. Saves migrated `providers.json`.

**Result:** All existing providers continue to work. Models that were implicitly
"default" are now all enabled. You may want to disable models you don't use.

### Routing Migration

On first startup, `_migrate_routing()` ensures all 5 routing categories exist
in `routing.json`:

1. Reads existing routing config (may be empty in old installs).
2. Adds any missing categories with `provider_id: null, model_id: null`.
3. Saves `routing.json`.

**Result:** Routing starts in automatic mode for all categories. Old manual
overrides (if any) are preserved.

### API Key Storage

If upgrading from a version that stored keys in plaintext `providers.json`:
- Keys remain accessible via the `_api_key` fallback field.
- On Windows with `win32cred` available, keys are migrated to Windows
  Credential Manager on next `add_provider()` or `update_provider()`.
- No automatic migration of existing keys — re-save the provider to upgrade
  credential storage.

## Breaking Changes

### API Changes

| Old Endpoint | New Endpoint | Change |
|---|---|---|
| `POST /providers` | `POST /api/v1/providers` | Prefix added. Body field `default_model` removed. Added `models_enabled`. |
| `GET /providers` | `GET /api/v1/providers` | Prefix added. Response model objects changed. |
| `PUT /providers/{id}` | `PUT /api/v1/providers/{id}` | Prefix added. `model_updates` replaces `default_model`. |
| `GET /routing` | `GET /api/v1/routing` | Prefix added. Response includes `model_id`. |
| `PUT /routing` | `PUT /api/v1/routing` | Prefix added. Request body includes `model_id`. |
| *(new)* | `PUT /api/v1/providers/{id}/models` | Model toggle endpoint. |
| *(new)* | `POST /api/v1/providers/{id}/models/refresh` | Force-refresh models. |
| *(new)* | `GET /api/v1/providers/available-types` | List supported provider types. |

### Response Shape Changes

The `Provider` object returned by all provider endpoints has changed:

- **Removed:** `default_model` (no longer exists).
- **Removed:** `api_key` (never returned; use `has_api_key` boolean).
- **Changed:** `models` is now `list[dict]` instead of `list[str]`.
- **Added:** `latency_ms`, `last_checked`, `created_at`, `updated_at`.

### Frontend Breaking Changes

- `ProviderConfigurationDialog` no longer has a `default_model` field.
  Model management happens on provider cards.
- `manageProvidersPage` used to define its own `ProviderInfo` interface —
  now imports from `types.ts`. Custom local interfaces will conflict.
- `api.ts` provider helpers are now namespaced under `api.providers.*`
  and `api.routing.*`. Old flat function names (`addProvider()`) removed.

### Configuration Files

`~/.eve/providers.json` format changed:
```diff
- "models": ["gpt-4o", "gpt-4o-mini"],
+ "models": [
+   {"id": "gpt-4o", "displayName": "GPT-4o", "supportsVision": true, "enabled": true, ...},
+   {"id": "gpt-4o-mini", "displayName": "GPT-4o Mini", "supportsVision": true, "enabled": true, ...}
+ ],
- "default_model": "gpt-4o"
```

`~/.eve/routing.json` format changed:
```diff
- {"id": "general_chat", "provider_id": "openai-a1b2c3d4"}
+ {"id": "general_chat", "provider_id": "openai-a1b2c3d4", "model_id": "gpt-4o"}
```

**Migration is automatic** — old files are converted in-place on first load.

## Rollback Instructions

To revert to the previous version:

### 1. Backup current configs
```bash
cp ~/.eve/providers.json ~/.eve/providers.json.backup
cp ~/.eve/routing.json ~/.eve/routing.json.backup
```

### 2. Roll back code
```bash
git revert HEAD  # or checkout previous tag
```

### 3. Restore old config format (if needed)
The old binary expects old-format JSON. The migration created new-format files.
You have two options:

**Option A:** Manually reformat `providers.json`:
```python
import json
with open("providers.json") as f:
    data = json.load(f)
for p in data:
    p["models"] = [m["id"] for m in p.get("models", [])]
    p["default_model"] = (p["models"] or [None])[0]
with open("providers.json", "w") as f:
    json.dump(data, f, indent=2)
```

**Option B:** Remove migrated files and let old version create fresh defaults:
```bash
rm ~/.eve/providers.json ~/.eve/routing.json
```

### 4. Verify rollback
```bash
# Start the application and check provider status
```

## Recommended Upgrade Sequence

1. **Take a backup** — `~/.eve/providers.json` and `~/.eve/routing.json`.
2. **Deploy new version** — Replace backend and frontend artifacts.
3. **Verify startup logs** — Expect `_migrate_models` log lines.
4. **Check provider status** — All providers should show their previous status.
   Test connections if uncertain.
5. **Review enabled models** — Navigate to Manage Providers → check which
   models are enabled. Disable unnecessary models.
6. **Review routing** — Verify routing categories have appropriate providers.
7. **Test a conversation** — Send a message, verify it routes correctly.
8. **Test streaming** — Send a message with `stream: true`.
9. **Test model switching** — Change provider/model mid-conversation.
