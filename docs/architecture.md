# Eve AI — System Architecture

## Overview

Eve AI is a multi-provider AI orchestration platform with capability-based routing,
centralized streaming, per-provider health isolation, and a modular adapter pattern.
The system supports 16 provider types (OpenAI, Anthropic, Google, Groq, Mistral,
Cerebras, Ollama, OpenRouter, and more) with 60+ known models in a static catalog.

```
┌──────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/TS)                   │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐          │
│  │ChatWindow│  │ManageProviders│  │SmartRouting   │          │
│  │          │  │Page          │  │Panel          │          │
│  └────┬─────┘  └──────┬───────┘  └──────┬────────┘          │
│       │               │                 │                    │
│       └───────────────┼─────────────────┘                    │
│                       │ HTTP/SSE                             │
└───────────────────────┼──────────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────────┐
│              BACKEND (FastAPI / Python)                       │
│                       │                                       │
│  ┌────────────────────┼──────────────────────────────┐       │
│  │                    │                               │       │
│  │         ┌──────────▼──────────┐                    │       │
│  │         │ ConversationManager │                    │       │
│  │         │  (chat.py routes)   │                    │       │
│  │         └──────────┬──────────┘                    │       │
│  │                    │                               │       │
│  │         ┌──────────▼──────────┐                    │       │
│  │         │   ProviderManager   │                    │       │
│  │         │  ┌────────────────┐ │                    │       │
│  │         │  │  ModelCache    │ │  ┌─────────────┐  │       │
│  │         │  │  HealthMonitor │ │  │ ModelCatalog│  │       │
│  │         │  └───────┬────────┘ │  │ (static)    │  │       │
│  │         └──────────┼──────────┘  └─────────────┘  │       │
│  │                    │                               │       │
│  │         ┌──────────▼──────────┐                    │       │
│  │         │    SmartRouter      │                    │       │
│  │         │  (capability-based) │                    │       │
│  │         └──────────┬──────────┘                    │       │
│  │                    │                               │       │
│  │         ┌──────────▼──────────┐                    │       │
│  │         │ StreamingManager   │                    │       │
│  │         │ (abort/heartbeat/  │                    │       │
│  │         │  timeout/reconnect)│                    │       │
│  │         └──────────┬──────────┘                    │       │
│  │                    │                               │       │
│  │         ┌──────────▼──────────┐                    │       │
│  │         │   AIProviderAdapter │◄─── OpenAIAdapter  │       │
│  │         │   (abstract base)   │◄─── AnthropicAdapter│      │
│  │         │                    │◄─── GoogleAdapter   │       │
│  │         │                    │◄─── OllamaAdapter   │       │
│  │         │                    │◄─── GroqAdapter     │       │
│  │         │                    │◄─── OpenAICompatible│       │
│  │         └────────────────────┘                     │       │
│  │                                                    │       │
│  │  ┌──────────────────┐   ┌──────────────────┐       │       │
│  │  │  HealthMonitor   │   │  TimeoutRetry    │       │       │
│  │  │  (isolated per   │   │  (call_with_     │       │       │
│  │  │   provider)      │   │   timeout/retry) │       │       │
│  │  └──────────────────┘   └──────────────────┘       │       │
│  └────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

## Component Relationships

### ProviderManager
- **Role**: Central lifecycle manager for all providers.
- **Owns**: Provider configs, adapter instances, ModelCache, HealthMonitor.
- **Key methods**: `add_provider()`, `update_provider()`, `remove_provider()`,
  `fetch_models()`, `toggle_model()`, `refresh_models()`, `register_all_adapters()`.
- **Persistence**: `~/.eve/providers.json` (configs + model state + enabled flags),
  `~/.eve/routing.json` (routing overrides), Windows Credential Manager (API keys).

### SmartRouter
- **Role**: Capability-based request routing across providers/models.
- **Strategy options**: `PERFORMANCE`, `COST`, `LATENCY`, `PRIORITY`.
- **Capability matching**: Required capabilities per category scored against
  model capability flags. Ranking formula weights vary by strategy.
- **Fallback chain**: If ranked provider fails, tries next. All-providers-exhausted
  raises `RuntimeError`.
- **Routing categories**: `general_chat`, `coding`, `vision`, `reasoning`, `fallback`.
- **User overrides**: Each category stores `provider_id` + `model_id` for manual routing.

### StreamingManager
- **Role**: Single source of truth for all streaming across adapters.
- **Features**: Per-stream abort controller (`cancel()`), heartbeat (keep-alive
  during slow streams), configurable reconnect (max 2 attempts), timeout wrapping,
  progress callbacks (`on_token`, `on_error`, `on_done`).
- **HTTP helpers**: `read_sse_lines()` for SSE parsing, `extract_openai_chunk()`,
  `extract_google_chunk()` for token extraction.
- **Architecture decision**: Adapters delegate their `stream()` to
  `StreamingManager.stream()` instead of duplicating streaming logic.

### AIProviderAdapter (abstract base)
- **Role**: Contract interface every provider must implement.
- **Required methods**: `chat()`, `stream()`, `health()`, `list_models()`,
  `get_model()`, `connect()`, `disconnect()`, `validate_api_key()`.
- **Optional methods**: `vision()`, `image_generation()`, `speech_to_text()`,
  `text_to_speech()`, `embeddings()`, `rerank()`, `moderation()`. Raise
  `NotImplementedError` if unsupported.
- **ChatRequest/ChatResponse dataclasses**: Strongly typed request/response with
  model, tokens, tools, streaming flag, cost, latency.
- **Adapter implementations**: `OpenAIAdapter`, `AnthropicAdapter`,
  `GoogleAdapter`, `OllamaAdapter`, `GroqAdapter`, `OpenAICompatibleAdapter`
  (covers OpenRouter, Mistral, Cerebras, GitHub Models, HuggingFace, LM Studio,
  custom providers).

### ModelCatalog
- **Role**: Static catalog of 60+ known models across 16 provider types.
- **Model dataclass fields**: `id`, `display_name`, `provider`, `context_length`,
  `max_output`, 11 capability booleans (vision, reasoning, function_calling, etc.),
  3 quality/speed ratings (1-10), 2 cost fields.
- **Helpers**: `get_catalog_models()`, `model_from_catalog()`, `merge_models()`.
- **Dynamic providers** (OpenRouter, GitHub Models, HuggingFace, LM Studio,
  OpenAI-compatible, custom): have empty catalogs — models discovered at runtime
  via `fetch_models()` then merged with user's enabled state.

### ConversationManager
- **Role**: Single entry point for all conversation CRUD and messaging.
- **Sub-managers**: `StreamManager`, `SessionManager`, `HistoryManager`,
  `TitleGenerator`, `ConversationSearch`, `BranchManager`, `AnalyticsTracker`,
  `ConversationExporter`.
- **Streaming**: `stream_message()` yields typed SSE events (`token`, `done`,
  `error`, `tool_call`, `status`, `planner_started`, etc.) via `StreamEventType`.
- **Conversation model**: Already includes `provider_id`, `model_id` fields
  (lines 148-149 of `conversation/models.py`) for per-conversation model switching.

### HealthMonitor
- **Role**: Per-provider isolated health tracking.
- **States**: `UNKNOWN`, `HEALTHY`, `DEGRADED`, `UNREACHABLE`, `INVALID_KEY`,
  `RATE_LIMITED`, `QUOTA_EXCEEDED`.
- **Features**: Consecutive failure tracking, history (last 100 events),
  background periodic checks (default 60s), concurrent batch check.
- **Isolation guarantee**: `check_all()` uses `asyncio.create_task()` per provider —
  one failure never cascades.

### ModelCache
- **Role**: TTL-based model list cache with stale-while-revalidate.
- **Parameters**: Default TTL 300s, stale TTL 86400s (24h), refresh interval 600s.
- **Behavior**: Returns cached data instantly, triggers background refresh on stale,
  serves stale data when offline, supports ETag-based conditional requests.

## Data Flow — Chat Request

```
User types message
       │
       ▼
ChatWindow (React) ──POST /chat/stream──→ ConversationManager.stream_message()
       │                                        │
       │                                   Detect intent
       │                                   Gather context
       │                                   Retrieve memories
       │                                   Build context window
       │                                        │
       │                                   ┌────▼────┐
       │                                   │ Planner  │ (if actionable intent)
       │                                   │ Execute  │ (if execution needed)
       │                                   └────┬────┘
       │                                        │
       │                                   Build LLM messages
       │                                   (system + memory + tools)─┐
       │                                        │                    │
       │                                   ┌────▼──────────────┐    │
       │                                   │ SmartRouter.route │    │
       │                                   │ or .route_stream  │    │
       │                                   │                   │    │
       │                                   │ 1. Resolve routing│    │
       │                                   │    overrides      │    │
       │                                   │    (user manual   │    │
       │                                   │     provider/model│    │
       │                                   │     per category) │    │
       │                                   │ 2. Get enabled    │    │
       │                                   │    models         │    │
       │                                   │ 3. Score by       │    │
       │                                   │    capabilities   │    │
       │                                   │ 4. Rank by        │    │
       │                                   │    strategy       │    │
       │                                   │    (PERFORMANCE/  │    │
       │                                   │     COST/LATENCY) │    │
       │                                   │ 5. Fallback chain │    │
       │                                   │    if provider    │    │
       │                                   │    fails          │    │
       │                                   └────┬──────────────┘    │
       │                                        │                    │
       │                                   ┌────▼──────────────┐    │
       │                                   │ AIProviderAdapter  │    │
       │                                   │ .chat() or        │    │
       │                                   │ .stream()         │    │
       │                                   │        │           │    │
       │                                   │  ┌─────▼──────┐   │    │
       │                                   │  │Streaming   │   │    │
       │                                   │  │Manager     │   │    │
       │                                   │  │(heartbeat, │   │    │
       │                                   │  │ timeout,   │   │    │
       │                                   │  │ abort)     │   │    │
       │                                   │  └─────┬──────┘   │    │
       │                                   └────┬──────────────┘    │
       │                                        │                    │
       │                                   ┌────▼──────────────┐   │
       │                                   │ Provider SDK /    │    │
       │                                   │ REST API          │    │
       │                                   │ (OpenAI, Anthropic│    │
       │                                   │  Google, etc.)    │    │
       │                                   └───────────────────┘    │
       │                                        │                    │
       │◄────── SSE events stream ──────────────┘                    │
       │  (token, done, error, tool_call,                             │
       │   status, planner_started, etc.)                              │
       │                                        ┌────────────────┐   │
       │                                        │ HealthMonitor  │   │
       │                                        │ records success│   │
       │                                        │ or failure     │   │
       │                                        └────────────────┘   │
       │                                        ┌────────────────┐   │
       │                                        │ Conversation   │   │
       │                                        │ Saved + title  │   │
       │                                        │ auto-generated │   │
       │                                        └────────────────┘   │
       │
       ▼
User sees streamed response in ChatWindow
```

## Key Design Decisions

### 1. Adapter Pattern (AIProviderAdapter base class)
- **Why**: Every provider has different auth, model listing, streaming format,
  and error semantics. The adapter interface abstracts all differences behind
  uniform `chat()`, `stream()`, `list_models()`, `health()` methods.
- **Benefit**: Adding a new provider = creating one `Adapter` subclass.
  Zero changes to ProviderManager, SmartRouter, or ConversationManager.
- **Trade-off**: Some provider-specific capabilities (e.g., Anthropic thinking
  blocks) must either be expressed through the generic interface or special-cased.

### 2. Centralized StreamingManager
- **Why**: Every adapter previously had duplicated streaming logic (timeout
  loops, heartbeat checks, error handling). A single manager eliminates
  duplication, ensures consistent abort/retry behavior, and provides
  uniform SSE parsing helpers.
- **Benefit**: `extract_openai_chunk()` and `extract_google_chunk()` static
  methods isolate token extraction differences in one place.
- **Trade-off**: All streaming must go through `StreamingManager.stream()`.
  Adapters that use custom streaming protocols (e.g., WebSocket) need to
  wrap their generator before delegating.

### 3. Capability-Based Routing (SmartRouter)
- **Why**: Hardcoded `provider → category` mappings were inflexible. A
  vision task should use any model with `supports_vision=true`, not just
  the one manually assigned. Capability scoring + strategy-based ranking
  automates best-model selection.
- **Benefit**: Users can add a new model, toggle it on, and routing
  automatically considers it. Multiple strategies (performance, cost,
  latency) suit different use cases.
- **Trade-off**: Capability flags must be accurate. An incorrectly tagged
  model could be routed to tasks it cannot handle. The static catalog
  mitigates this but dynamic models rely on API metadata quality.

### 4. Static Catalog + Dynamic Discovery
- **Why**: A static `MODEL_CATALOG` provides capability metadata (speed,
  quality, cost, isFree, etc.) that most provider APIs do not return.
  Dynamic `fetch_models()` discovers actual available model IDs.
  The merge preserves catalog metadata + user enabled state + discovered IDs.
- **Benefit**: Users see rich model info (including free tiers) without
  API calls. Discovery fills in models the catalog doesn't know about
  (e.g., new OpenRouter models).
- **Trade-off**: Catalog must be updated periodically. Empty catalog
  entries for dynamic providers rely entirely on the API.

### 5. Per-Provider Health Isolation
- **Why**: A rate-limited or offline provider should never block requests
  to other providers. HealthMonitor tracks each provider independently
  and SmartRouter skips unhealthy providers during routing.
- **Benefit**: Graceful degradation — if Google is rate-limited, Anthropic
  handles general chat seamlessly.

### 6. SSE-Based Streaming Protocol
- **Why**: Server-Sent Events are simpler than WebSockets, work through
  standard HTTP proxies, and are natively supported by `EventSource` in
  browsers. The `data: ` prefix + `\n\n` delimiter is universally understood.
- **Benefit**: The `POST /chat/stream` endpoint yields events that the
  frontend can consume with or without a library. Event types are
  extensible (just add a new `StreamEventType`).
