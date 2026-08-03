# EVE AI Ecosystem Report — v1.2.2 "Production AI Ecosystem"

**Version:** 1.2.2
**Status:** Implementation complete (W0–W10) + W2 live-validation remediation
**Generated:** 2026-08-03

---

## 1. Executive Summary

EVE v1.2.2 turns the provider layer into a production-grade AI ecosystem. All 9
configured providers plus the full universal framework are integrated through the
already-built Universal Provider Framework (used as-is, not redesigned). The release
adds DeepInfra, dynamic model/capability discovery, a commercial policy engine
(defaulting to FREE_ONLY), capability-driven SmartRouter routing, health scoring,
parallel background refresh, multi-account failover, and a comprehensive regression
suite.

**Headline numbers:**

| Metric | Value |
|--------|-------|
| Registered provider types | 17 |
| Configurable providers (configured in product) | 9 (openai, google, groq, openrouter, ollama, deepinfra, cloudflare, huggingface, nvidia) |
| Catalog-enriched models | 63 across 11 providers (deepinfra: 10) |
| Routing categories (capability-derived) | 5 |
| Capability flags per model (ModelInfo) | 20+ |
| Default commercial policy | `FREE_ONLY` (persisted) |
| Provider framework tests | **258/258 pass** |
| Legacy backend tests (`src/backend/aios/tests`) | **363/364 pass** (1 pre-existing failure) |
| Desktop mirror parity | byte-identical |

---

## 2. Provider Registry (17 builtin definitions)

All providers are declared in `core/provider_registry.py` and instantiated by
`core/provider_factory.py` (config-driven `OpenAICompatibleAdapter` + native_map
for dedicated adapters).

| Provider | Adapter | Discovery | Notes |
|----------|---------|-----------|-------|
| google | GoogleAdapter | native | dedicated |
| openai | OpenAIAdapter | native | dedicated |
| anthropic | AnthropicAdapter | static | dedicated |
| ollama | OllamaAdapter | native | dedicated (local) |
| groq | GroqAdapter | native | dedicated |
| cohere | CohereAdapter | static | dedicated |
| cloudflare | CloudflareAdapter | static | dedicated |
| mistral | OpenAICompatibleAdapter | openai_v1 | config-driven |
| **deepinfra** | OpenAICompatibleAdapter | openai_v1 | **new in W1** |
| cerebras | OpenAICompatibleAdapter | openai_v1 | config-driven |
| openrouter | OpenAICompatibleAdapter | openai_v1 | config-driven |
| github_models | OpenAICompatibleAdapter | openai_v1 | config-driven |
| huggingface | OpenAICompatibleAdapter | openai_v1 | config-driven |
| lm_studio | OpenAICompatibleAdapter | lmstudio | config-driven |
| nvidia | OpenAICompatibleAdapter | openai_v1 | config-driven |
| openai_compatible | OpenAICompatibleAdapter | openai_v1 | generic |
| custom | OpenAICompatibleAdapter | openai_v1 | generic |

### 2.1 DeepInfra (W1)

DeepInfra was entirely absent from the codebase. Integrated end-to-end:

- **Endpoint:** `https://api.deepinfra.com/v1/openai` (OpenAI-compatible, Bearer auth)
- **Discovery:** `GET /models` + native `/models/list`; namespaced model IDs
- **Classifier:** `_classify_deepinfra` reads `input_cost_per_token` /
  `output_cost_per_token` / `per_token_costs`, falls back to `_generic_classify`
- **Catalog:** 10 models including Llama 3.3 70B Turbo, DeepSeek V3/R1,
  Qwen 2.5 72B, Llama 3.1 70B/8B, Mixtral 8x7B, Mistral 7B,
  Phind CodeLlama 34B, and GTE Large (embeddings, `isEmbeddingModel`)

---

## 3. Capability Extraction & Dynamic Discovery (W2)

Capability inference is centralized in `core/capability_inference.py`
(`infer_capabilities` / `bool_from_inference` / `merge_into_modelinfo`). Every
adapter (google, openai, groq, ollama, openai_compatible) delegates to it instead
of scattering heuristics locally. Tri-state results (True/False/None) are promoted
into `ModelInfo`; explicit provider metadata and official metadata (OpenRouter
`architecture.modality`, HF `inference.chat_completion.tags` / `pipeline_tag`)
out-rank ID heuristics, and explicit `False` is never overwritten.

- **Priority:** explicit provider metadata → official metadata → ID heuristics → unknown.
- **Promote-only heuristics:** family markers (o1/o3/r1, gemini-2.5, deepseek-r1,
  kimi-k2, qwq, gpt-, qwen, etc.) only ever set True, never False.
- **Excluded families** (embedding/audio/image/video) assert `supports_tools=False`.
- **Digit-boundary token matching:** `qwen` matches `qwen2.5-coder:7b`; `deepseek-coder`
  is in the tool family — fixes `supports_tools` for version-suffixed models.
- Deprecation captured via `_extract_deprecation(raw)` (`status` +
  `deprecation`/`deprecated` → deprecated/removed/preview/experimental).

Embeddings (confirmed decision): models are exposed with a capability summary
only — no dedicated embeddings routing subsystem.

### 3.1 W2 Live-Validation Remediation (root-cause fixes)

Live routing validation surfaced three production bugs, all fixed and regression-tested:

| Bug | Impact | Fix |
|-----|--------|-----|
| `ModelInfo.from_old_format` computed `cs` but never passed `commercial_status` / `is_free` / `pricing` into the constructor | every stored model reloaded as `UNKNOWN`; `FREE_ONLY` (persisted default) rejected **all** routes → `NoEligibleRouteError` | pass computed `commercial_status`, `is_free`, `pricing` and preserve modern `commercialStatus` key, `speed/quality/latency`, `recommended/deprecated/experimental/enabled`, `discovery_source`, `provider_type/instance` |
| `_fetch_and_merge` only filled catalog keys **absent** from the discovered dict | `gemini-2.5-flash` catalog `isFree: true` never applied (discovered default `isFree: false`) → still unroutable under FREE_ONLY | catalog now fills `commercialStatus`/`isFree` when discovery reports non-informative `unknown` |
| `RouteCandidate` lacked `supports_thinking`; `_build_candidates` didn't copy it | reasoning category requires `supports_reasoning` **and** `supports_thinking` → reasoning category had zero eligible candidates | add `supports_thinking` to `RouteCandidate` + populate in `_build_candidates` |

**Live validation (tools/validate_w2_capabilities.py, real 9-provider install):**
- 966 live models refreshed (openrouter 337, deepinfra 186, HF 129, openai 122,
  nvidia 102, google 52, groq 20, ollama 13, cloudflare 5), 0 duplicates.
- reasoning+thinking: 106 models; tools: 643; function_calling: 652.
- Reasoning spot-checks: o1/o3-mini, deepseek-r1, gemini-2.5-flash/pro, kimi-k2,
  qwq → `reasoning=True thinking=True`.
- Coding spot-checks: gpt-4o, llama-3.3-70b, deepseek-chat-v3.1, `qwen2.5-coder:7b`
  → `tools=True fc=True` (qwen coder fixed via digit-boundary matching).
- SmartRouter AUTO/FREE_ONLY resolves all three live categories:
  `reasoning → google/gemini-2.5-flash`, `coding → google/gemini-2.5-flash`,
  `general_chat → google/gemini-2.5-flash` (all FREE, all flags True).
- Tri-state sanity: explicit `False` preserved; unknown IDs stay `None`.

---

## 4. Commercial Policy Engine (W3)

| Policy | Allows | Notes |
|--------|--------|-------|
| `FREE_ONLY` | FREE, LOCAL | **Default for all installs** (persisted) |
| `NO_DIRECT_PAID` | FREE, FREE_TIER, CREDIT_BASED, LOCAL | opt-in |
| `ALLOW_PAID` | everything | opt-in |

- `SmartRouter` default is `CommercialPolicy.FREE_ONLY`.
- `_save_routing()` writes `{"commercial_policy": ..., "routing": [...]}`.
- `_load()` migrates legacy list format → dict with FREE_ONLY.
- Manager exposes `get_commercial_policy()` / `set_commercial_policy()`; API
  `GET`/`PUT /routing/commercial-policy` route through the manager (persistence works).
- Existing installs get the safe default and can opt into paid.

---

## 5. SmartRouter Capability Routing (W4, W6, W8)

Routing is capability-first (vision/reasoning/tools/function_calling/json/streaming)
plus latency, health, commercial policy, priority, and context-window tie-breakers.
No model-name routing.

- **RouteCandidate** now carries `context_window`; ranking adds a `PRIORITY`
  strategy with priority/context tie-breakers.
- **MAX_CANDIDATE_ATTEMPTS** (20) caps candidate evaluation in `_resolve_auto`.
- **Capability maps deduped:** `routing_types.CATEGORY_CAPABILITIES` is the single
  source of truth; `CAPABILITY_MAP` is aliased; `smart_router.ROUTING_CATEGORIES`
  derives from it; the API exposes `GET /routing/categories` (W6).
- **Fallback hierarchy (W8, verified end-to-end):**

| Level | Reason | Example |
|-------|--------|---------|
| 0 | preferred eligible | primary account |
| 1 | same model, alternate instance | multi-account |
| 2 | same provider type, alternate model | sibling model |
| 3 | FREE cross-provider | free fallback |
| 4 | FREE_TIER cross-provider | free-tier fallback |
| 5 | CREDIT_BASED cross-provider | included-credit fallback |
| 6 | LOCAL cross-provider | Ollama/LM Studio |
| 7 | PAID / unknown | only under `ALLOW_PAID`, else `PaidRoutingDisabledError` |

- `STRICT` never silently falls back (raises `RouteUnavailableError` when the
  exact route is unavailable).

---

## 6. Health Engine (W5)

`HealthMonitor.ProviderHealth` now tracks:

- `total_checks` / `successful_checks` / `success_rate` (0.0–1.0)
- `health_score` (0–100): success-rate (60%) + uptime recency (40%), zeroed for
  INVALID_KEY / QUOTA_EXCEEDED / UNREACHABLE, capped low for RATE_LIMITED
- Full state machine: HEALTHY / DEGRADED / RATE_LIMITED / QUOTA_EXCEEDED /
  INVALID_KEY / UNREACHABLE / UNKNOWN
- `to_dict()` exposes all new fields to `GET /providers/health`

The split-brain bug was fixed (W0): a single shared `HealthMonitor` is passed to
both `SmartRouter` and `ProviderManager`, and the background check loop is started
in the app lifespan.

---

## 7. Background Model Refresh & Parallel Discovery (W7)

- `ProviderManager.refresh_all_models(concurrency_limit=4)` invalidates each
  provider's model cache and re-fetches concurrently (`asyncio.gather` + semaphore),
  tolerating per-provider failures.
- `start_background_refresh(interval)` / `stop_background_refresh()` /
  `is_background_refresh_running()`; the task is cancelled in `shutdown()`.
- `AiosSettings` gains `provider_health_interval` (120s) and
  `model_refresh_interval` (3600s); `app.py` starts both loops in the lifespan.

---

## 8. Multi-Account & Failover (W4/W8)

Multi-account already worked as multiple provider instances with independent
adapters, keys, and health state. W8 adds a dedicated regression suite proving
the failover chain works from level 0 through level 7, including the paid-route
guard under FREE_ONLY and STRICT no-fallback semantics.

---

## 9. Audit Fixes (W0)

| Bug | Fix |
|-----|-----|
| Split-brain HealthMonitor (two instances) | single shared monitor passed to SmartRouter + ProviderManager |
| `_list_standard_models` never defined | extracted method; `list_models()` delegates by strategy |
| `_generic_classify(raw)` wrong arity | `_generic_classify(mid, raw)` |
| FastAPI route shadowing | literal routes registered before `/providers/{provider_id}` |
| Background health/refresh loops never started | both started in app lifespan |

---

## 10. Desktop Mirror Parity (W9)

All backend changes are mirrored to `desktop/src-tauri/backend/aios/` and verified
byte-identical via `git diff --no-index`. The desktop copy compiles and imports
cleanly (17 providers, deepinfra, FREE_ONLY, categories, settings intervals).

---

## 11. Test Summary & Regression

| Suite | Result |
|-------|--------|
| `tests/provider_framework/` (registry, factory, onboarding, contract, capability extraction, commercial policy, routing enhancements, health score, routing categories, model refresh, fallback chain, W2 regression) | **258/258 pass** |
| `src/backend/aios/tests/` (legacy backend suite) | **363/364 pass** — only `test_github_models_headers_set` fails (pre-existing, confirmed broken at HEAD, unrelated to this work) |
| `tests/unit/` provider/routing/model/health files | all pass individually |

New test files added:

- `test_capability_extraction.py` (25)
- `test_commercial_policy.py` (6)
- `test_routing_enhancements.py` (9)
- `test_health_score.py` (11)
- `test_routing_categories.py` (7)
- `test_model_refresh.py` (6)
- `test_fallback_chain.py` (12)
- `test_w2_regression.py` (29 — tri-state inference, metadata priority,
  merge semantics, RouteCandidate `supports_thinking`, digit-boundary token
  matching, `from_old_format` commercial-status round-trip)

Legacy tests `test_quota_aware_routing.py` / `test_routing_policy.py` were updated
for the W3 FREE_ONLY default (model helpers now default to
`commercial_status=CommercialStatus.FREE`; two FREE_TIER failover tests use an
explicit `NO_DIRECT_PAID` policy).

---

## 12. Known Limitations / Notes

- Full `pytest tests/` aggregate run is blocked by a pre-existing
  `bestrelpath` INTERNALERROR on this machine (Python 3.14 + pytest 9.1.1);
  run test files individually or `tests/provider_framework` as a group.
- `test_github_models_headers_set` fails at HEAD and is unrelated to this work.
- Embeddings are exposed as models + capability summary only (confirmed decision).
- No per-conversation manual provider switching (confirmed out of scope).

---

## 13. Key Files

| Component | Path |
|-----------|------|
| Provider registry | `src/backend/aios/core/provider_registry.py` |
| Provider factory | `src/backend/aios/core/provider_factory.py` |
| Capability inference (centralized, W2) | `src/backend/aios/core/capability_inference.py` |
| OpenAI-compatible adapter | `src/backend/aios/core/adapters/openai_compatible_adapter.py` |
| Smart router | `src/backend/aios/core/smart_router.py` |
| Routing types (categories, candidates, errors) | `src/backend/aios/core/routing_types.py` |
| Provider manager | `src/backend/aios/core/provider_manager.py` |
| Health monitor | `src/backend/aios/core/health_monitor.py` |
| Model catalog | `src/backend/aios/core/model_catalog.py` |
| Model info (canonical) | `src/backend/aios/core/model_info.py` |
| API (providers + routing) | `src/backend/aios/api/providers.py` |
| App wiring (shared monitor + background loops) | `src/backend/aios/api/app.py` |
| Settings | `src/backend/aios/config/settings.py` |
| Frontend providers components | `src/frontend/src/components/providers/` |
| Framework docs | `PROVIDER_FRAMEWORK.md` |
