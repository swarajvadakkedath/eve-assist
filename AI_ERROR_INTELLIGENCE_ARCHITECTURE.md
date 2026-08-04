# AI Error Intelligence Architecture

## Overview
Centralized error capture → classification (21 categories) → human explanation → recovery suggestions → safe auto-recovery → immediate provider-health feed → diagnostics logging → Recovery Center tab.

## Error Categories (21)
| Category | Description | Auto-Recovery |
|----------|-------------|---------------|
| `PROVIDER_DOWN` | Provider unreachable / 5xx | RETRY_OR_SWITCH |
| `PROVIDER_TIMEOUT` | Request timed out | RETRY |
| `RATE_LIMITED` | 429 rate limit hit | COOLDOWN |
| `INVALID_API_KEY` | 401 authentication failed | SUGGEST_ONLY |
| `QUOTA_EXCEEDED` | 402/403 quota exhausted | SUGGEST_ONLY |
| `MODEL_NOT_FOUND` | 404 model not available | REFRESH_MODELS |
| `MODEL_UNAVAILABLE` | Model temporarily offline | SWITCH_PROVIDER |
| `EMPTY_RESPONSE` | Provider returned empty/malformed | RETRY |
| `CONTEXT_LENGTH_EXCEEDED` | Prompt too long for model | SUGGEST_ONLY |
| `CONTENT_FILTER` | Content policy violation | SUGGEST_ONLY |
| `STREAM_ERROR` | Streaming connection broken | RETRY |
| `NETWORK_ERROR` | DNS/TLS/connection failure | RETRY_OR_SWITCH |
| `TOOL_FAILURE` | Tool execution failed | SUGGEST_ONLY |
| `VISION_FAILURE` | Screen capture/analysis failed | RETRY |
| `VOICE_FAILURE` | STT/TTS failed | RETRY |
| `MEMORY_FAILURE` | Memory store/retrieve failed | RETRY |
| `WORKSPACE_FAILURE` | Workspace init/operation failed | SUGGEST_ONLY |
| `PLUGIN_FAILURE` | Plugin load/execution failed | SUGGEST_ONLY |
| `CONFIGURATION` | Config missing/invalid | SUGGEST_ONLY |
| `TIMEOUT` | General timeout | RETRY |
| `UNKNOWN` | Unclassified error | SUGGEST_ONLY |

## Classification Pipeline
`classify_error(exc_or_event, context)` runs 7 priority-ordered steps:
1. **Route metadata** — `RouteError.error_type` field → `PROVIDER_DOWN`
2. **Provider status** — `ProviderStatus` enum → exact category
3. **HTTP status** — status code rules (401→INVALID_API_KEY, 429→RATE_LIMITED, etc.)
4. **Exception type** — `ProviderTimeoutError`→TIMEOUT, `PluginLoadError`→PLUGIN_FAILURE, etc.
5. **Message heuristics** — regex pattern matching against `_MESSAGE_HINTS` table
6. **Module tag** — `context.module` → domain-specific fallback
7. **UNKNOWN** — catch-all fallback

## Self-Healing Chains
`RecoveryEngine.attempt_recovery(event, classification, request)`:
- **RETRY** — retry same request (only when zero tokens emitted)
- **SWITCH_PROVIDER** — pick alternate provider via SmartRouter
- **REFRESH_MODELS** — invalidate model cache + re-discover
- **COOLDOWN** — 60s per-model rate-limit backoff
- **RETRY_OR_SWITCH** — retry first, switch if retry fails
- **REFRESH_AND_RETRY** — refresh models then retry
- **SUGGEST_ONLY** — no auto-action, show suggestions to user

All recovery attempts are recorded via `error_intelligence.record_recovery_result()`.

## Provider Health Feed
`SmartRouter.route_stream()` now records health per-attempt:
- `_record_provider_failure` → `HealthMonitor.record_failure(provider_id, error, timeout_seconds=...)`
- `_record_provider_success` → `HealthMonitor.record_provider_success(provider_id)`
- Zero-token empty stream → captured as `EMPTY_RESPONSE` error event
- Stream retry excludes providers in OPEN_CIRCUIT/UNREACHABLE states

## Diagnostics Export
Three formats available via `GET /api/v1/errors/{id}/report?format=`:
- **Markdown** — human-readable report with metadata, cause, suggestions, context, stack
- **JSON** — full structured event data for programmatic use
- **Plain text** — minimal copy-paste friendly

Frontend supports one-click copy via Copy button on error detail cards.

## Persistence
- Bounded ring: `~/.eve/errors.json`, max 1000 events (configurable)
- Atomic writes: write to `.tmp` + `os.replace` (no partial reads)
- Thread-safe via `threading.Lock`
- Stats computed on demand from event list (no denormalized counters)

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/errors` | List events (supports `?category=&severity=&limit=`) |
| GET | `/api/v1/errors/stats` | Category/severity counts + recovery rate |
| GET | `/api/v1/errors/timeline` | Last 50 events for timeline view |
| GET | `/api/v1/errors/recoveries` | Recent recovery attempts |
| GET | `/api/v1/errors/{error_id}` | Single event detail |
| GET | `/api/v1/errors/{error_id}/report?format=` | Export as markdown/json/plain |
| POST | `/api/v1/errors/clear` | Purge all events |

## Frontend: Recovery Center
New "Recovery" tab in AI Operations Center (icon: 🔧):
- Stats grid: total errors, errors today, recovery rate, top category
- Category/severity filter dropdowns
- Scrollable error list with color-coded severity dots
- Detail panel: likely cause, recovery suggestions, tech details (metadata grid), stack trace
- Copy buttons: Markdown / JSON / Plain
- Error timeline with colored dots per category

## Capture Points
All capture calls are wrapped in `try/except` so failures in error intelligence never affect the calling path:
- `smart_router.py` — stream retry failures + empty stream
- `conversation/manager.py` — message errors + stream errors + empty response
- `tool_manager.py` — timeout + generic exception
- `voice/stt.py` — STT request errors
- `vision/engine.py` — screen capture/analysis failures
- `memory_system.py` — store failures
- `workspace/manager.py` — workspace init failures
- `plugins/loader.py` — plugin load failures
- `api/app.py` — 500 exception handler (record-only, no response modification)
