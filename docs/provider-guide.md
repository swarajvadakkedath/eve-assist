# Eve AI — Provider Configuration Guide

## Supported Providers

Eve AI supports 16 provider types. Each has known metadata (endpoint, auth style,
model catalog level):

| Type | Name | Auth | Needs Endpoint | Catalog |
|---|---|---|---|---|
| `google` | Google AI Studio | Query param `key` | No | 6 models |
| `openai` | OpenAI | Header `Bearer` | No | 8 models |
| `anthropic` | Anthropic | Header `x-api-key` | No | 4 models |
| `groq` | Groq | Header `Bearer` | No | 7 models |
| `mistral` | Mistral | Header `Bearer` | No | 3 models |
| `cerebras` | Cerebras | Header `Bearer` | No | 2 models |
| `openrouter` | OpenRouter | Header `Bearer` | No | 0 (dynamic) |
| `github_models` | GitHub Models | Header `Bearer` | No | 0 (dynamic) |
| `huggingface` | Hugging Face | Header `Bearer` | No | 0 (dynamic) |
| `ollama` | Ollama | None | No | 8 models |
| `lm_studio` | LM Studio | Header `Bearer` | No | 0 (dynamic) |
| `openai_compatible` | OpenAI Compatible | Header `Bearer` | Yes | 0 (dynamic) |
| `custom` | Custom Provider | Header `Bearer` | Yes | 0 (dynamic) |

### Authentication Methods

1. **Header + Bearer token**: Most providers (OpenAI, Groq, Mistral, OpenRouter,
   Cerebras, GitHub Models, HuggingFace, LM Studio, OpenAI-compatible, Custom).
   API key is sent as `Authorization: Bearer <key>`.

2. **Header + custom prefix**: Anthropic uses `x-api-key: <key>` (no prefix).

3. **Query parameter**: Google AI Studio uses `?key=<key>` appended to every
   request URL.

4. **No auth**: Ollama (local-only, no API key needed).

## Adding a Provider

### Via UI (Manage Providers page)

1. Navigate to **Manage Providers**.
2. Click **Add Provider**.
3. Select a provider type from the dropdown.
4. Enter an API key (required for cloud providers).
5. For `openai_compatible` or `custom` types, enter the endpoint URL.
6. Optionally select specific models to enable initially.
7. Click **Save**.

The provider is created with all known models from the static catalog. Models
are enabled by default unless you specified `models_enabled`.

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/providers \
  -H "Content-Type: application/json" \
  -d '{
    "provider_type": "openai",
    "name": "My OpenAI",
    "api_key": "sk-...",
    "models_enabled": ["gpt-4o", "gpt-4o-mini"]
  }'
```

### Local Providers (Ollama, LM Studio)

1. Start the local server (e.g., `ollama serve` on port 11434).
2. Add the provider via UI or API — no API key needed.
3. Models are discovered from the local instance.
4. The static catalog provides default entries; `refresh_models()` fetches
   actual locally available models.

## Configuring Models

### Model Enable/Disable

Models can be individually enabled or disabled. Disabled models are excluded
from routing.

**Via UI:** Check/uncheck model checkboxes on the provider card.
**Via API:**
```bash
curl -X PUT http://localhost:8000/api/v1/providers/{provider_id}/models \
  -H "Content-Type: application/json" \
  -d '{"model_id": "gpt-3.5-turbo", "enabled": false}'
```

### Model Refresh

The model list is cached for 300 seconds (5 minutes). To force-refresh:

**Via UI:** Click **Refresh Models** on the provider card.
**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/providers/{provider_id}/models/refresh
```

This calls the provider's `/models` endpoint, discovers available model IDs,
merges them with the static catalog (to preserve capability metadata), and
preserves user's enabled/disabled state.

### Model Capabilities

Each model has 20+ capability flags:

| Flag | Type | Description |
|---|---|---|
| `supportsStreaming` | bool | Can stream tokens |
| `supportsVision` | bool | Can analyze images |
| `supportsImageGeneration` | bool | Can generate images |
| `supportsAudio` | bool | Can process audio |
| `supportsReasoning` | bool | Supports chain-of-thought |
| `supportsFunctionCalling` | bool | Can call tools |
| `supportsEmbeddings` | bool | Generates embeddings |
| `supportsThinking` | bool | Extended thinking mode |
| `supportsJSON` | bool | JSON mode / structured output |
| `isFree` | bool | No cost to use |
| `recommended` | bool | Featured/recommended model |
| `speed` | 1-10 | Relative speed rating |
| `quality` | 1-10 | Relative output quality |
| `costPer1kInput` | float | Cost per 1K input tokens (USD) |
| `costPer1kOutput` | float | Cost per 1K output tokens (USD) |
| `contextLength` | int | Max context window (tokens) |
| `maxOutput` | int | Max output tokens |

### Model Filters (Frontend)

The ModelSelector supports these filters:
- **Free** — `isFree === true`
- **Vision** — `supportsVision === true`
- **Reasoning** — `supportsReasoning === true`
- **128K+** — `contextLength >= 131072`
- **Fast** — `speed >= 7`
- **Recommended** — `recommended === true`

## How Routing Works

### Routing Categories

Five categories each with required capabilities:

| Category | Required Capabilities | Typical Use |
|---|---|---|
| `general_chat` | `supports_streaming` | Everyday conversations, Q&A |
| `coding` | `supports_tools`, `supports_function_calling`, `supports_reasoning` | Code generation, debugging |
| `vision` | `supports_vision`, `supports_streaming` | Image analysis |
| `reasoning` | `supports_reasoning`, `supports_thinking` | Complex problem-solving |
| `fallback` | *(none)* | Primary provider fallback |

### Automatic Routing (no manual override)

1. SmartRouter collects all enabled models from all healthy providers.
2. Models are scored against the category's required capabilities.
   - Each matching capability adds 1.0 to the capability fit score.
   - Fit score is normalized: `matching_caps / total_required_caps`.
   - Categories with no required capabilities get a base score of 0.5.

3. Models are ranked by strategy:
   - **PERFORMANCE** (default): `fit * 0.6 + (quality/10) * 0.2 + (speed/10) * 0.2`
   - **COST**: `fit * 0.7 + (1/(input_cost + output_cost + 0.001)) * 0.3`
   - **LATENCY**: `fit * 0.5 + (speed/10) * 0.5`
   - **PRIORITY**: `fit` only (provider order determines tiebreaks)

4. Top-ranked provider is tried first.
5. If it fails (timeout, auth error, etc.), the next ranked provider is tried.
6. If all providers fail, a `RuntimeError` is raised.

### Manual Routing Override

You can pin specific providers/models to categories:

**Via UI:** SmartRoutingPanel — dropdown pairs per category.
**Via API:**
```bash
curl -X PUT http://localhost:8000/api/v1/routing \
  -H "Content-Type: application/json" \
  -d '{
    "routing": [
      {"id": "general_chat", "provider_id": "openai-a1b2c3d4", "model_id": "gpt-4o"},
      {"id": "coding", "provider_id": "anthropic-e5f6g7h8", "model_id": "claude-sonnet-4-20250514"},
      {"id": "vision", "provider_id": null, "model_id": null},
      {"id": "reasoning", "provider_id": null, "model_id": null},
      {"id": "fallback", "provider_id": "groq-m3n4o5p6", "model_id": "llama-3.3-70b-versatile"}
    ]
  }'
```

Setting `provider_id` to `null` reverts to automatic routing for that category.

### Per-Conversation Override

Each conversation stores `provider_id` and `model_id`. When set, these override
both manual routing and automatic routing for that specific conversation:

```
POST /chat/stream
{
  "conversation_id": "abc",
  "content": "Hello",
  "provider_id": "google-i9j0k1l2",
  "model_id": "gemini-2.5-flash"
}
```

The ConversationHeader component in the UI provides dropdowns to switch
provider/model per conversation.

## Troubleshooting

### "No enabled models" / "All providers failed"

1. Verify at least one provider has `status: "connected"`.
2. Verify at least one model is enabled for that provider.
3. Check that the model has the capabilities required by the category.
4. Check HealthMonitor — a rate-limited or invalid-key provider is skipped.

### Connection test fails

| Error | Likely Cause |
|---|---|
| `Invalid API key` | Wrong or expired key |
| `Provider unreachable` | Provider API is down or network blocked |
| `Connection timed out` | Wrong endpoint URL, firewall, or provider slow |
| `Rate limited` | Too many requests, wait or check quotas |
| `Quota exceeded` | Free tier exhausted |

### Model refresh returns no models

- Provider type has an empty catalog *and* the API's `/models` endpoint is
  unreachable or returns empty results.
- Check `has_models_endpoint` in available-types. If `false` (e.g., Anthropic),
  the catalog is the sole source — update the catalog for new models.
- For local providers (Ollama), ensure the service is running.

### Streaming hangs or times out

- Default timeout is 120s per stream.
- Google provider uses 30s timeout to prevent hangs.
- Check `StreamingManager` settings: `default_timeout`, `default_heartbeat`.
- Heartbeat fires every 15s by default. If no tokens arrive within that window,
  a log line `stream.heartbeat` is emitted (not an error).

### API key storage on non-Windows platforms

Windows Credential Manager is used on Windows (requires `pywin32`).
On other platforms, the API key is stored in plaintext in `providers.json`.
Consider setting `HAS_WIN32CRED = False` explicitly or implementing a
platform-specific secure store.

### HealthMonitor background check

- Runs every 60s by default.
- Checks all registered providers concurrently.
- If a provider is unhealthy, SmartRouter skips it.
- Health degrades: 3+ consecutive failures → `UNREACHABLE`.
- Health recovers immediately on next successful check.
