# EVE v2.0 — Phase A Architecture

**Status:** In implementation
**Depends on:** `EVE_V2.0_VISION.md` (approved v2.0 vision)
**Scope:** Phase A — Agent Runtime abstraction + EVE Agent Adapter + OpenAI-wire surface + Hermes integration plan + desktop mirror findings + diagrams.

---

## 1. Goal

Hermes (and any future agent engine) uses EVE as its model provider. EVE becomes
the routing/recovery/health layer under *any* agent engine. EVE Core has **zero**
Hermes dependencies.

**Smart Router Rule:** every inference request passes
Smart Router → Provider Manager → Health Monitor → Credential Pools → Commercial Policy → Recovery.
Hermes never talks to providers directly.

**Voice Rule:** the Voice Pipeline is EVE-owned; the voice path forwards
intent/requests to the agent layer through the same Smart Router. Hermes has its
own real-time voice (Telegram/Discord/CLI) that is *not* merged into EVE's voice
pipeline — EVE's voice stays the desktop-first interface.

---

## 2. Layers

```
      User
       │
 Voice / Chat / Overlay / ACP            (EVE-owned desktop surface)
       │
 Hermes Agent Engine                       (agent planning, skills, subagents, MCP)
       │  OpenAI-wire:  base_url=http://127.0.0.1:8456/v1   model=eve:*
       ▼
┌──────────────────────────────────────────────┐
│  EVE Agent Adapter  (aios/agent/adapter.py)   │
│  resolve_model_alias -> AgentTurnRequest      │
└──────────────────────────────────────────────┘
       │
 ┌──────────────────────────────┐
 │  AgentRuntime (ABC)          │   aios/agent/runtime.py
 │  HermesRuntime | Native...   │   aios/agent/hermes_runtime.py
 └──────────────────────────────┘
       │
 Smart Router → Provider Manager → Health Monitor → Credential Pools → Commercial Policy
       │
 AI Error Intelligence → Recovery Center
```

- **AgentRuntime** — the interface (framework-agnostic).
- **HermesRuntime** — the first implementation (all Hermes-specific code isolated).
- **EveAgentAdapter** — the only bridge between a runtime and EVE Core.
- **OpenAI-wire `/v1`** — the public surface that lets OpenAI-wire clients (Hermes,
  OpenCode, SDKs) treat EVE as a model provider.

---

## 3. Deliverable 1 — AgentRuntime interface

File: `src/backend/aios/agent/runtime.py`

Pure-Python abstraction; no Hermes/framework imports anywhere in the file.

### Domain models

| Type | Purpose |
|---|---|
| `AgentRuntimeStatus` | IDLE / THINKING / PLANNING / EXECUTING / OBSERVING / WAITING / CANCELLING / SHUTDOWN / ERROR |
| `AgentContext` | session id, objective, messages, tools, context map |
| `AgentTurnRequest` | model (alias or exact id), stream, max_tokens, temperature, top_p, stop, tools, tool_choice |
| `AgentEvent` | type (token / tool_call / event / error), content, metadata |
| `AgentResult` | output, tool_calls, finish_reason, model, provider, error, trace, latency_ms |
| `AgentHealth` | runtime_id, status, available, details |
| `AgentMetadata` | runtime_id, display_name, version, capabilities, provider_aware, requires_config |

### Abstract methods

| Method | Returns |
|---|---|
| `start()` / `shutdown()` | lifecycle |
| `think(request)` | `AsyncIterator[AgentEvent]` |
| `plan(request)` | `AgentResult` |
| `execute(request)` | `AsyncIterator[AgentEvent]` |
| `observe(request)` | `dict` |
| `cancel()` | control |
| `health()` | `AgentHealth` |
| `metadata()` | `AgentMetadata` |
| `run_turn(request)` | concrete helper draining events → `AgentResult` |

New runtimes (OpenAI Agents SDK, CrewAI, LangGraph, OpenHands, AutoGen, native EVE
planner) implement this ABC without touching EVE Core.

---

## 4. Deliverable 2 — EVE Agent Adapter

File: `src/backend/aios/agent/adapter.py`

Bridges `AgentTurnRequest` → EVE `ChatRequest` → `SmartRouter`; exposes
`route()` / `route_stream()` / `execute_tool()` / `list_models()` /
`list_capability_aliases()` / `health_snapshot()`.

### Capability aliases

| Alias | Routing category | Commercial override |
|---|---|---|
| `eve:general` / `eve:chat` | general_chat | — |
| `eve:reasoning` | reasoning | — |
| `eve:coding` | coding | — |
| `eve:vision` | vision | — |
| `eve:fast` | general_chat (low latency) | — |
| `eve:free` | general_chat | FREE_ONLY |
| `eve:json` | structured_output | — |
| `eve:tool` | tool_calling | — |

Exact model ids (`openai/gpt-4o`) pass through as preferred routes.

---

## 5. Deliverable 3 — OpenAI-compatible endpoint

File: `src/backend/aios/api/openai_compat.py` — router registered (no `/api/v1`
prefix) in `aios/api/app.py:register_routes`.

| Endpoint | Notes |
|---|---|
| `GET /v1/models` | aggregated dedup'd model list (ProviderManager) + capability aliases |
| `POST /v1/chat/completions` | non-streaming + SSE streaming |
| Auth | bearer token enforced via shared `verify_auth` dependency |

Request translation: OpenAI messages/tools → `AgentTurnRequest` → adapter →
Smart Router. Response translation: `AgentResult` → OpenAI wire format, with an
`eve` envelope (provider, model, trace) for observability.

Registered in `app.py`:

```python
from aios.api.openai_compat import router as openai_compat_router
app.include_router(openai_compat_router)          # no /api/v1 prefix
```

Adapter wiring in `app.py` lifespan:

```python
from aios.agent.adapter import EveAgentAdapter
agent_adapter = EveAgentAdapter(
    smart_router=smart_router,
    provider_manager=provider_manager,
    health_monitor=health_monitor,
    tool_manager=tool_manager,
)
app.state.agent_adapter = agent_adapter
```

---

## 6. Deliverable 4 — HermesRuntime (first implementation)

File: `src/backend/aios/agent/hermes_runtime.py`

- Implements `AgentRuntime`; `runtime_id="hermes"`.
- **Isolation rule:** this is the *only* file allowed to import `hermes_*`.
- Guarded import — if `hermes-agent` isn't installed, EVE Core still imports
  cleanly; `health()` reports `available=False`.
- Model addressing is deferred: EVE registers as Hermes' provider, so Hermes
  itself never needs to know EVE's model ids — it sends `eve:*` aliases.

Integration (later milestone): configure Hermes as an EVE provider, wire the
engine, then delete the `_initialize_hermes_engine` stub.

---

## 7. Deliverable 5 — Hermes provider configuration

Hermes supports OpenAI-wire custom providers via `config.yaml`
`providers.<id>` with `base_url` + `api_key`. EVE registers itself:

```yaml
# ~/.hermes/config.yaml
providers:
  eve:
    api_mode: chat_completions
    api_key: <EVE_BEARER_TOKEN>          # from GET /api/v1/auth/token (loopback only)
    base_url: http://127.0.0.1:8456/v1
    models:
      - eve:general
      - eve:reasoning
      - eve:coding
      - eve:vision
      - eve:fast
      - eve:free
```

Requirements before this can run:
- `GET /v1/models` returns aliases (implemented).
- `POST /v1/chat/completions` streaming + tool-call format matches Hermes'
  expected OpenAI wire shape (implemented; verify against real Hermes).
- Bearer token reachable on loopback (existing `AuthManager`).

---

## 8. Deliverable 6 — Desktop mirror investigation (result)

Question: is `desktop/src-tauri/backend/aios/` (the committed mirror) consumed at
build or runtime?

**Result: No.** The build and runtime read `src/backend` directly:

| Component | Evidence |
|---|---|
| `desktop/scripts/bundle-python.ps1` | line 16 copies from `src/backend` |
| `desktop/src-tauri/tauri.conf.json` | line 43 resources map `"../../src/backend": "backend"` |
| `desktop/src-tauri/launcher/services/process_service.py` | `_resolve_backend_dir` prefers `src/backend/aios` in dev, falls back to bundled `backend/aios` |

The committed mirror is a **tracked duplicate** not consumed by the build.
276 tracked files each side; parity currently clean (0 diff via
`git diff --no-index`).

**Recommendation (single-source):** drop the committed mirror and generate it
only when needed (dev parity checks or bundling from `src/backend`). Keeping it
in-sync is mechanical (copy + `git diff --no-index`); the pragmatic path for this
release is to continue mirroring new files for parity while planning the cleanup.

---

## 9. Deliverable 7 — Updated architecture diagrams

**Before (v1.x):** UI → backend `/api/v1` → SmartRouter → providers. Agent
reasoning was implicit inside `ConversationManager` + `ExecutionEngine`.

**After (v2.0 Phase A):**

```
Voice/UI/Overlay/ACP ──► EVE backend /api/v1        (EVE-owned surface)
                                  │
                  ┌───────────────┴──────────────┐
                  │                              │
        EVE-native conversation               OpenAI-wire /v1
        (chat, voice, execution)               (Hermes, SDKs, OpenCode)
                  │                              │
                  └──────────┬───────────────────┘
                             ▼
                 EVE Agent Adapter  (aios/agent/)
                 AgentRuntime  ← HermesRuntime
                             │
                             ▼
             Smart Router → Provider Manager → Health Monitor
                        → Credential Pools → Commercial Policy
                             │
               AI Error Intelligence → Recovery Center
                             │
                   Windows • Browser • Files • Memory
```

- Provider/agent choice becomes invisible to the user.
- Hermes remains the intelligence layer; EVE remains the operating layer.
- All inference (native or via Hermes) passes the Smart Router + Error Intelligence.

---

## 10. Files added/changed (Phase A so far)

| File | Change |
|---|---|
| `src/backend/aios/agent/__init__.py` | new — package public surface |
| `src/backend/aios/agent/runtime.py` | new — AgentRuntime ABC + domain models |
| `src/backend/aios/agent/adapter.py` | new — EveAgentAdapter + CAPABILITY_ALIASES |
| `src/backend/aios/agent/hermes_runtime.py` | new — HermesRuntime (first impl) |
| `src/backend/aios/api/openai_compat.py` | new — /v1/models + /v1/chat/completions |
| `src/backend/aios/api/app.py` | modified — wire agent_adapter + register router |

---

## 11. Acceptance criteria (Phase A)

1. `from aios.agent import AgentRuntime, EveAgentAdapter, HermesRuntime` imports
   cleanly with and without `hermes-agent` installed.
2. `GET /v1/models` returns aggregated models + `eve:*` aliases (bearer auth).
3. `POST /v1/chat/completions` (stream + non-stream) routes through SmartRouter
   via the adapter; response includes provider + trace.
4. A Hermes conversation streams responses served by EVE's Smart Router from the
   best available provider.
5. Provider failover + error capture flow into EVE's Recovery Center.
6. Desktop mirror stays byte-identical; provider_framework + backend regression
   green.
