# Eve AI — Pre-Release Checklist

## 1. Code Completeness

### Backend
- [ ] All provider adapters implement `chat()`, `stream()`, `health()`,
      `list_models()`, `get_model()`, `connect()`, `disconnect()`, `validate_api_key()`.
- [ ] ProviderManager CRUD operations work for all 16 provider types.
- [ ] Model migration (`_migrate_models`) handles empty, old-format, and new-format input.
- [ ] Routing migration (`_migrate_routing`) creates all 5 categories if missing.
- [ ] API key storage works on Windows (Credential Manager) and non-Windows (plaintext fallback).
- [ ] HealthMonitor background check runs without errors.
- [ ] ModelCache handles freshness, staleness, and offline scenarios.
- [ ] SmartRouter fallback chain works when primary provider fails.

### Frontend
- [ ] ManageProvidersPage loads and displays all providers.
- [ ] AddProviderDialog creates providers without `default_model` parameter.
- [ ] AIProviderCard shows model checkboxes, free filter toggles enable/disable.
- [ ] ModelSelector renders with search + all filter buttons.
- [ ] SmartRoutingPanel displays all 5 categories with dropdown pairs.
- [ ] ConversationHeader shows provider+model dropdowns per conversation.
- [ ] ProviderConfigurationDialog contains only API key + endpoint fields.
- [ ] ConnectionTester reads first enabled model (not `default_model`).
- [ ] CSS classes: `.conversation-header`, `.ms-*`, `.pr-model-checkbox`,
      `.pr-routing-row-controls` are defined.

### Conversation/Wiring
- [ ] Conversation model includes `provider_id` and `model_id` fields.
      *(Checked: yes — `conversation/models.py` lines 148-149)*
- [ ] ConversationHeader wired into ChatWindow with state and handlers.
- [ ] `POST /chat/stream` supports `provider_id`/`model_id` override.
- [ ] Per-conversation provider/model overrides take effect on next message.

## 2. Test Scenarios

### Basic Functionality
- [ ] **Add OpenAI provider** — POST /api/v1/providers with valid API key.
      Expected: 200, status changes to "connected" after connection test.
- [ ] **Add Anthropic provider** — verify x-api-key auth works.
- [ ] **Add Google provider** — verify query-param auth works.
- [ ] **Add Ollama provider** — no API key required, local models discovered.
- [ ] **Add OpenAI-compatible provider** — verify custom endpoint works.
- [ ] **Test connection** — POST /api/v1/providers/{id}/test returns success/failure.
- [ ] **Test all connections** — GET /api/v1/providers/test-all returns per-provider results.
- [ ] **Update provider** — change name, endpoint, API key, model enabled state.
- [ ] **Delete provider** — removes config, API key, clears routing references.
- [ ] **List providers** — returns all configured providers without API keys.

### Model Management
- [ ] **Toggle model** — PUT /api/v1/providers/{id}/models with enabled:false.
      Verify SmartRouter excludes disabled model from routing.
- [ ] **Refresh models** — POST /api/v1/providers/{id}/models/refresh.
      Verify cache invalidated, new models appear.
- [ ] **Fetch models** — GET /api/v1/providers/{id}/models returns merged list.
- [ ] **Dynamic discovery** — OpenRouter provider returns real model list from API.
- [ ] **Empty catalog** — openai_compatible provider starts with empty list,
      refresh populates from API.

### Routing
- [ ] **Default routing** — No overrides set. Send general chat → best match routed.
- [ ] **Manual routing** — Set provider+model per category. Verify override applied.
- [ ] **Fallback chain** — Disable primary provider's models. Request routes to
      next best match.
- [ ] **All providers fail** — Disable all models. Verify meaningful error.
- [ ] **Performance strategy** — High-quality, fast models ranked first.
- [ ] **Cost strategy** — Cheapest models ranked first.
- [ ] **Latency strategy** — Fastest models ranked first.
- [ ] **Unhealthy providers skipped** — Set invalid key → provider unreachable →
      router skips it automatically.

### Streaming
- [ ] **Basic stream** — POST /chat/stream returns SSE events.
- [ ] **Stream abort** — Cancel mid-stream. Verify no tokens after abort.
- [ ] **Stream timeout** — Set 1s timeout. Verify timeout error.
- [ ] **Stream heartbeat** — Very slow stream (1 token/30s). Verify heartbeat logs.
- [ ] **Tool events** — Intent triggers tool. Verify tool_requested → tool_running →
      tool_completed → final_response sequence.
- [ ] **Non-streaming fallback** — Stream errors should recover gracefully or
      display partial content.

### Conversations
- [ ] **Create conversation** — POST /chat/conversation returns full object.
- [ ] **List conversations** — GET /chat/conversations returns paginated list.
- [ ] **Rename conversation** — PUT /chat/conversation/{id} updates title.
- [ ] **Delete conversation** — DELETE /chat/conversation/{id} removes it.
- [ ] **Send message** — POST /chat/message returns response with tokens_used.
- [ ] **Get history** — GET /chat/history/{id} returns messages in order.
- [ ] **Clear history** — DELETE /chat/history/{id} empties messages.
- [ ] **Branching** — Create branch from message, verify independent history.
- [ ] **Edit message** — Edit user message, verify response regenerated.
- [ ] **Auto-title** — Send message without custom title. Verify title generated.

### Health Monitoring
- [ ] **Background check** — HealthMonitor runs every 60s, updates health states.
- [ ] **Consecutive failures** — 3+ failures triggers `UNREACHABLE` state.
- [ ] **Recovery** — Failed provider becomes healthy again after successful check.
- [ ] **Isolation** — One provider's failure doesn't affect others' health.
- [ ] **Rate limit detection** — 429 response correctly marked.

### Error Handling
- [ ] **Invalid API key** — Returns 401-compatible status, doesn't crash.
- [ ] **Provider timeout** — Returns timeout status, fallback activates.
- [ ] **Rate limited** — Returns rate-limited status, provider skipped.
- [ ] **Network error** — Graceful error, no unhandled exceptions.
- [ ] **Invalid model_id** — Request returns error (not crash).
- [ ] **All provider errors exhausted** — 503 with descriptive message.

## 3. Performance Benchmarks

### Latency Targets
- [ ] **Connection test** — < 5s per provider (network-dependent).
- [ ] **Model fetch** (cached) — < 100ms.
- [ ] **Model fetch** (API call) — < 10s.
- [ ] **Non-streaming chat** — First token < 3s.
- [ ] **Streaming first token** — < 2s.
- [ ] **Routing decision** — < 50ms (no API calls needed).
- [ ] **Health check** — < 10s per provider.
- [ ] **Concurrent health checks** — All providers in parallel.

### Resource Targets
- [ ] **Memory idle** — < 200MB RSS.
- [ ] **Memory under load** (10 concurrent streams) — < 500MB RSS.
- [ ] **CPU idle** — < 5%.
- [ ] **CPU under load** (10 concurrent streams) — < 50% (single core).
- [ ] **Startup time** — < 3s (includes provider config load + migration).
- [ ] **providers.json size** — < 100KB with 10 providers (no API key bloat).

### Stress Tests
- [ ] **10 concurrent streaming conversations** — No timeouts, no memory leak.
- [ ] **100 rapid model toggles** — No state corruption.
- [ ] **Add + remove 50 providers** — No file corruption, no orphaned adapters.
- [ ] **Continuous 24h run** — No memory leak, health history capped at 100 entries.

## 4. Security Checks

### API Key Handling
- [ ] API keys never returned in `GET /api/v1/providers` response.
- [ ] API keys stored in Windows Credential Manager (Windows) with `CRED_PERSIST_LOCAL_MACHINE`.
- [ ] Keys encrypted at rest via OS mechanisms (Credential Manager).
- [ ] Non-Windows fallback stores in plaintext — documented limitation.
- [ ] Key deletion on provider removal (`_delete_api_key`).

### Input Validation
- [ ] Provider type validated against `PROVIDER_META` + `openai_compatible`/`custom`.
- [ ] Routing IDs validated against `ROUTING_CATEGORIES`.
- [ ] Model IDs validated against provider's model list before toggle.
- [ ] All user inputs length-checked (no unbounded strings).

### Network Security
- [ ] Default endpoints use HTTPS (except localhost Ollama/LM Studio).
- [ ] httpx timeouts configured (chat: configurable, streaming: 120s, health: 10s, test: 15s).
- [ ] No hardcoded credentials or tokens in source code.
- [ ] No secret exposure in logs (keys redacted by structlog).

### Dependency Security
- [ ] All Python dependencies audited for known CVEs.
- [ ] All npm packages audited for known CVEs.
- [ ] `npm audit` — zero critical vulnerabilities.
- [ ] Python `pip audit` — zero critical vulnerabilities.

## 5. Rollback Plan

### Rollback triggers
- Critical bug in model migration corrupts user data.
- All providers fail to connect after upgrade (migration regression).
- HealthMonitor false-positive marks all providers as unhealthy.
- Streaming regression: aborts, hangs, or corrupts output.
- Frontend cannot load (CSS/JS bundle, API path mismatch).

### Rollback steps
1. **Identify severity** — Is this blocking all users? Partial? Cosmetic?
2. **Toggle feature flag** — If the issue is scoped to a new feature, disable
   via environment variable (assuming feature flag exists).
3. **Code revert** — `git revert <merge-commit>` or deploy previous artifact.
4. **Config restore** — If migration corrupted `providers.json`:
   ```bash
   cp ~/.eve/providers.json.backup ~/.eve/providers.json
   cp ~/.eve/routing.json.backup ~/.eve/routing.json
   ```
5. **Verify rollback** — Run test scenarios (1-3) against rolled-back version.
6. **Communicate** — Notify affected users, provide ETA for fix.

### Rollback test (pre-release)
- [ ] Backup current config.
- [ ] Upgrade to release version (simulate migration).
- [ ] Revert to old version with restored config.
- [ ] Verify old version works correctly with old-format config.
- [ ] Check no data loss in conversations or provider configurations.

## 6. Monitoring Setup

### Logging
- [ ] structlog configured for structured JSON output.
- [ ] Key events logged at appropriate levels:
  - `INFO`: Provider added/removed, model toggled, routing changed.
  - `WARN`: Provider timeout, rate limited, fetch models failed, stale cache served.
  - `ERROR`: Adapter creation failed, credential store failed, stream failed.
- [ ] Logs include `provider_id` for correlation.
- [ ] No plaintext API keys in any log output.

### Metrics (to implement if not present)
- [ ] Request latency (p50, p95, p99) per endpoint.
- [ ] Provider connection status count (healthy / degraded / unreachable).
- [ ] Routing fallback count (how often primary fails → fallback used).
- [ ] Model refresh success/failure count.
- [ ] Streaming abort count.
- [ ] Health check duration per provider.

### Alerts (recommended)
- [ ] All providers unreachable — p0, immediate notification.
- [ ] >50% of providers unreachable — p0.
- [ ] Repeated rate limiting on any provider — p2.
- [ ] Model fetch failure rate >10% — p2.
- [ ] Streaming timeout rate >5% — p2.
- [ ] Health check duration >30s for any provider — p3.

## 7. Final Verification

- [ ] All backend unit tests pass.
- [ ] All frontend unit tests pass.
- [ ] E2E test suite passes (if exists).
- [ ] Static type checking passes (`mypy` / `pyright` for Python, `tsc` for TypeScript).
- [ ] `py_compile` passes for all Python modules.
- [ ] Linting passes (`ruff` for Python, `eslint` for TypeScript).
- [ ] CSS does not break existing component layouts.
- [ ] No hardcoded model IDs or provider names in frontend that reference
      removed `default_model` field.
- [ ] Build artifacts reproducible.
- [ ] Docker image (if used) builds without warnings.
