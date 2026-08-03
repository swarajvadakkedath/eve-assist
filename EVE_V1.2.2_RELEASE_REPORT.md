# EVE v1.2.2 — Release Report

**Release Date:** 2026-08-03
**Release Status:** READY

---

## Release Artifacts

| Artifact | Value |
|----------|-------|
| **Commit** | `d146ab9` (release: EVE v1.2.2) |
| **Tag** | `v1.2.2` (annotated) |
| **Branch** | `main` |
| **Installer** | `Eve_1.2.2_x64-setup.exe` (136.8 MB) |
| **SHA-256** | `71B318C8A333F894B3DE365B4756681D85D412ABCB73D1AD34AFCB93DDE67AF3` |
| **GitHub Release** | https://github.com/swarajvadakkedath/eve-assist/releases/tag/v1.2.2 |

---

## Acceptance Summary

| Suite | Result |
|-------|--------|
| Web Acceptance (API-level) | 47/47 PASS |
| Desktop Acceptance (structural) | 14/14 PASS |
| Backend Tests (provider framework) | 279/279 PASS |
| Frontend Tests (vitest) | 827/827 PASS |
| TypeScript Compilation | 0 errors |
| Production Build (vite) | PASS |
| Cargo Check (Tauri) | PASS |
| Desktop Mirror Parity | 267/267 files |

---

## Regression Summary

### Backend (279 tests)
- `test_registry.py`: 29 tests (17 providers)
- `test_factory.py`: 18 tests (adapter creation)
- `test_onboarding.py`: 7 tests (onboard endpoint)
- `test_contract_suite.py`: 96 tests (adapter contract)
- `test_capability_extraction.py`: 25 tests (capability flags)
- `test_commercial_policy.py`: 6 tests (FREE_ONLY)
- `test_routing_enhancements.py`: 9 tests (context window, priority, dedup)
- `test_health_score.py`: 11 tests (success_rate, health_score)
- `test_routing_categories.py`: 7 tests (categories endpoint)
- `test_model_refresh.py`: 6 tests (parallel refresh)
- `test_fallback_chain.py`: 12 tests (8-level fallback)
- `test_startup_readiness.py`: 10 tests (middleware, readiness)
- `test_w2_regression.py`: 29 tests (tri-state, merge, digit-boundary)
- `test_health_history.py`: 5 tests (health history endpoint)
- Other: 32 tests (quota, policy, etc.)

### Frontend (827 tests)
- 109 test files across components, services, hooks
- AOC components: DashboardView, ProvidersView, ModelsView, HealthView, etc.
- Conversation: ConversationView, ConversationTimeline, MarkdownRenderer
- Desktop: StatusIndicator, SettingsPanel, StatusStore
- Provider: AIProviderCard, AddProviderDialog, ProviderConfigurationDialog
- Memory: MemoryWorkspace, MemoryExplorer, MemoryInspector
- Command: CommandPalette, CommandRegistry, CommandResults
- Execution: ExecutionPanel, ExecutionSessionStore
- Layout: ResizableLayout, SplitPane, Workspace

---

## Known Limitations

1. **Background health checks** require ~120s to transition from `unknown` to actual provider state
2. **Voice/OCR** require hardware (microphone/screen) — manual verification needed
3. **Global shortcuts** require keyboard hook registration — manual verification needed
4. **System tray** requires Windows runtime — manual verification needed
5. **Long-running stability** (1h+) requires manual soak test

---

## Release Assets

| File | Size | SHA-256 |
|------|------|---------|
| `Eve_1.2.2_x64-setup.exe` | 136.8 MB | `71B318C8A333F894B3DE365B4756681D85D412ABCB73D1AD34AFCB93DDE67AF3` |

---

## Architecture Highlights

### Provider Framework
- **17 builtin providers**: openai, google, groq, openrouter, ollama, deepinfra, cloudflare, huggingface, nvidia + 8 more
- **Universal adapter**: OpenAICompatibleAdapter with config-driven discovery
- **Capability extraction**: reasoning, tools, function_calling, json, streaming, vision, thinking
- **Commercial policy**: FREE_ONLY (default), ALLOW_PAID, LOCAL_ONLY

### SmartRouter
- **Capability-driven routing**: 6 flags (vision, reasoning, tools, function_calling, json, streaming)
- **Fallback hierarchy**: 8 levels (preferred → same-model → same-provider → FREE → FREE_TIER → CREDIT → LOCAL → PAID)
- **Priority weighting**: configurable per-provider priority
- **MAX_CANDIDATE_ATTEMPTS**: 20 (prevents infinite evaluation)

### Health Engine
- **Metrics**: latency, failures, timeouts, rate-limits, quota
- **Scoring**: success_rate (60%) + uptime recency (40%)
- **Background monitoring**: configurable interval (default 120s)

### Startup Synchronization
- **State machine**: STARTING → INITIALIZING → READY | DEGRADED
- **Middleware**: blocks all routes except bypass set during init
- **Frontend gate**: statusStore with single poller, waitForReady() shared deferred
- **Recovery**: re-arms on backend restart (status regression detection)

---

## Provider Summary

| Provider | Type | Models | Health |
|----------|------|--------|--------|
| openai | cloud | dynamic | healthy |
| google | cloud | dynamic | healthy |
| groq | cloud | dynamic | healthy |
| openrouter | cloud | dynamic | healthy |
| ollama | local | dynamic | healthy |
| deepinfra | cloud | dynamic | healthy |
| cloudflare | cloud | 5 | healthy |
| huggingface | cloud | dynamic | healthy |
| nvidia | cloud | dynamic | healthy |

---

## AI Operations Center Summary

18 components providing:
- **Dashboard**: stat cards, quick actions, provider overview
- **Providers**: cards with health, capabilities, model counts
- **Models**: free models list, per-provider model explorer
- **Smart Router**: routing config, categories, fallback graph, diagnostics
- **Health**: provider health with recharts visualization
- **Activity**: notification history, event timeline
- **Performance**: system status, routing diagnostics
- **Settings**: commercial policy, routing preferences

---

## Startup Synchronization Summary

| Layer | Implementation |
|-------|---------------|
| Backend state | `AppStatus` enum: STARTING, INITIALIZING, READY, DEGRADED, OFFLINE, ERROR |
| Middleware | `StartupReadyMiddleware`: blocks non-bypass routes, returns 503 with actual status |
| Readiness | `GET /api/v1/system/readiness`: returns `{"ready": true}` |
| Frontend gate | `statusStore.ts`: single poller, `waitForReady(30_000)`, re-arm on regression |
| API calls | `fetchApi()` and `request()` await `waitForReady()` before fetching |
| App shell | `App.tsx`: splash gate while `!ready`, StatusIndicator + "Starting EVE..." |
| AOC | `AioStore.ts`: awaits ready before `loadAll()`, subscribes to statusStore |
| Desktop | Rust background thread: `wait_for_ready(60)`, emits `eve:backend-ready` |

---

*Generated by EVE v1.2.2 release process*
