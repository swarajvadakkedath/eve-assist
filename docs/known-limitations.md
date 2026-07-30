# Eve AI — Known Limitations

## Critical (P0)

None identified at this time.

## High (P1)

### 1. ConversationHeader not wired into ChatWindow

**File:** `src/frontend/src/components/chat/ConversationHeader.tsx`
**Severity:** High
**Impact:** The ConversationHeader component exists but is not rendered in
ChatWindow. Users cannot switch provider/model per conversation from the UI.
**Workaround:** The `POST /chat/stream` endpoint accepts `provider_id` and
`model_id` fields, enabling API-level workaround. The Conversation model already
stores these fields correctly.
**Planned fix:** Wire ConversationHeader into ChatWindow.tsx by passing
`currentProviderId`/`currentModelId` (from conversation state) and
`onProviderChange`/`onModelChange` handlers.

### 2. AddProviderDialog passes `default_model` (no-op)

**File:** `src/frontend/src/components/providers/AddProviderDialog.tsx`
**Severity:** High
**Impact:** The `default_model` parameter is still sent in the POST body when
adding a provider. The backend ignores it (the field no longer exists in the
data model), so there's no functional bug, but it indicates incomplete cleanup.
**Workaround:** None needed — the parameter is silently ignored.
**Planned fix:** Remove `default_model` from AddProviderDialog's request payload.

### 3. ConnectionTester reads deprecated `default_model`

**File:** `src/frontend/src/components/providers/ConnectionTester.tsx`
**Severity:** High
**Impact:** ConnectionTester reads `default_model` from the provider response,
which is now `null` (removed from the data model). This could display incorrect
"default model" information or cause UI glitches.
**Workaround:** None — the test results are unlikely to crash but may show
"null" as the default model.
**Planned fix:** Read the first enabled model from `models[]` instead of
`default_model`.

## Medium (P2)

### 4. CSS classes missing for new components

**Files:**
- `src/frontend/src/components/chat/ConversationHeader.tsx` (`.conversation-header`)
- `ModelSelector.tsx` (`.ms-wrapper`, `.ms-filters`, `.ms-item`)
- `AIProviderCard.tsx` (`.pr-provider-card-models`, `.pr-model-checkbox`)
- `SmartRoutingPanel.tsx` (`.pr-routing-row-controls`)

**Severity:** Medium
**Impact:** New components render with default/browser styling or `className`
references to non-existent CSS classes. The components are functional but
look unstyled, which degrades user experience.
**Workaround:** None for production. Development builds may still be usable.
**Planned fix:** Add CSS rules for `.conversation-header`, `.ms-*`,
`.pr-provider-card-models`, `.pr-model-checkbox`, `.pr-routing-row-controls`
classes in the appropriate stylesheet(s).

### 5. API key stored in plaintext on non-Windows

**Files:** `src/backend/aios/core/provider_manager.py:206-211`, `:226-229`
**Severity:** Medium
**Impact:** On Linux/macOS (or any system without `pywin32`), API keys are
stored in plaintext in `~/.eve/providers.json`. If the file permissions are
permissive, other processes/users could read API keys.
**Workaround:** Set restrictive file permissions on `~/.eve/providers.json`:
`chmod 600 ~/.eve/providers.json`.
**Planned fix:** Implement platform-specific secure storage for Linux
(libsecret/gnome-keyring) and macOS (Keychain).

### 6. No application-level rate limiting

**Files:** Not applicable — feature is absent.
**Severity:** Medium
**Impact:** The backend does not enforce rate limits per user, IP, or API key.
A malicious or buggy client could overwhelm the backend or exhaust provider
API quotas. Provider-level rate limits are detected post-facto (via 429
responses) but not prevented.
**Workaround:** Deploy behind a reverse proxy (nginx, Envoy) with rate limiting.
**Planned fix:** Add FastAPI middleware for token-bucket or sliding-window rate
limiting based on IP or API key.

### 7. OpenRouter/anthropic models not fetched from API

**Files:** `src/backend/aios/core/provider_manager.py:666-706`
**Severity:** Medium
**Impact:** `fetch_models()` calls `adapter.list_models()` to discover models,
then merges with the static catalog. For providers without a `models_endpoint`
(e.g., Anthropic — `models_endpoint: null`), the adapter's `list_models()`
returns an empty list. The model list falls back entirely to the static catalog.
New Anthropic models won't appear until the catalog is updated.
**Workaround:** None — requires a catalog update for new models.
**Planned fix:** Implement model scraping or provider-specific model listing
for providers that don't expose a `/models` endpoint.

### 8. No streaming reconnect for long-lived streams

**Files:** `src/backend/aios/core/streaming_manager.py`
**Severity:** Medium
**Impact:** `StreamingManager` supports abort, timeout, and heartbeat, but
does not automatically reconnect if the stream drops mid-way. The `max_reconnect`
parameter exists but is not yet used in the `stream()` method.
**Workaround:** The frontend can catch the `error` event and re-send the request.
**Planned fix:** Implement automatic reconnect with exponential backoff when a
stream drops with a recoverable error.

### 9. SmartRouter does not skip unhealthy providers in override mode

**Files:** `src/backend/aios/core/smart_router.py:199-211`
**Severity:** Medium
**Impact:** When a routing category has a manual `provider_id` override, the
router uses it unconditionally — it does not check the provider's health state.
If the manually selected provider is unhealthy, the request fails immediately
instead of falling back to automatic routing.
**Workaround:** Remove the manual override to enable automatic routing with
health checking.
**Planned fix:** Add health check before using manual override; if unhealthy,
log a warning and fall through to automatic routing.

## Low (P3)

### 10. No pagination for conversation listing

**Files:** `src/backend/aios/conversation/manager.py:128-131`
**Severity:** Low
**Impact:** `list_conversations()` accepts `limit`/`offset` but operates on
the in-memory dictionary. For users with 10,000+ conversations, this is
inefficient (sorting every request) and may cause UI lag. No database-backed
pagination exists.
**Workaround:** Use filters or delete old conversations.
**Planned fix:** Implement cursor-based pagination and database-level sorting.

### 11. No conversation archiving (delete only)

**Files:** Not applicable — feature is absent.
**Severity:** Low
**Impact:** Conversations can only be deleted, not archived/soft-deleted.
Accidental deletion is permanent.
**Workaround:** Export conversations before deleting (`GET /chat/history/{id}`
or export endpoint) if data retention is needed.
**Planned fix:** Add soft-delete and conversation archiving.

### 12. Model flag `supportsTools` vs `supportsFunctionCalling` inconsistency

**Files:**
- `src/backend/aios/core/model_catalog.py:21` (has `supports_function_calling`)
- `src/backend/aios/core/smart_router.py:37` (references `supports_tools`)
- `ROUTING_CATEGORIES` requires `supports_tools` but `Model` dataclass has
  `supports_function_calling`

**Severity:** Low
**Impact:** The SmartRouter requires `supports_tools` for the `coding` category,
but the `Model` dataclass defines the flag as `supports_function_calling`. This
means capability matching for the `coding` category will always score 0 for the
`supports_tools` requirement, potentially routing coding tasks to suboptimal
models.
**Workaround:** Manually pin a provider/model for the `coding` routing category.
**Planned fix:** Normalize capability flag names: add `supports_tools` as an
alias or rename in `ROUTING_CATEGORIES` to match `Model` field names.

### 13. No health history persistence

**Files:** `src/backend/aios/core/health_monitor.py`
**Severity:** Low
**Impact:** Health history is stored in memory only (100 events per provider).
After restart, the health state resets to `UNKNOWN`. The first request after
startup may attempt to use an unhealthy provider before the background health
check runs.
**Workaround:** Configure a short `check_interval` (default 60s) so health
recovery is quick.
**Planned fix:** Persist health state summary to disk; rehydrate on startup.

### 14. SSE `[DONE]` sentinel for OpenAI only

**Files:** `src/backend/aios/core/streaming_manager.py:172`
**Severity:** Low
**Impact:** The `[DONE]` sentinel check is specific to OpenAI's SSE format.
Other providers (Google, Anthropic) use different stream-termination signals.
The `read_sse_lines()` helper works for all, but the `[DONE]` optimization is
OpenAI-specific.
**Workaround:** None needed — other providers terminate via end-of-iterator
naturally.
**Planned fix:** Make sentinel configurable per adapter.

### 15. Frontend no loading/error states in some components

**Files:** Various frontend components
**Severity:** Low
**Impact:** Several new components (ModelSelector, AIProviderCard,
SmartRoutingPanel) may not have loading spinners or error displays for
all async operations (model refresh, provider test, routing save).
**Workaround:** None — UI may appear to hang during slow operations.
**Planned fix:** Add loading and error states to all async UI operations.
