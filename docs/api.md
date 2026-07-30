# Eve AI — API Reference

## Base URL

All API endpoints are served from the FastAPI application root.

```
http://localhost:8000
```

## Provider Management

### `GET /api/v1/providers`

List all configured providers.

**Response 200:**
```json
{
  "providers": [
    {
      "id": "openai-a1b2c3d4",
      "type": "openai",
      "name": "OpenAI",
      "endpoint_url": "https://api.openai.com/v1",
      "organization": null,
      "temperature": null,
      "max_tokens": null,
      "streaming_enabled": true,
      "is_default": true,
      "has_api_key": true,
      "status": "connected",
      "latency_ms": 342,
      "last_checked": "2026-07-23T10:00:00+00:00",
      "models": [
        {
          "id": "gpt-4o",
          "displayName": "GPT-4o",
          "provider": "openai",
          "contextLength": 128000,
          "maxOutput": 16384,
          "supportsStreaming": true,
          "supportsVision": true,
          "supportsImageGeneration": false,
          "supportsAudio": true,
          "supportsReasoning": false,
          "supportsFunctionCalling": true,
          "supportsEmbeddings": false,
          "supportsThinking": false,
          "supportsJSON": true,
          "enabled": true,
          "isFree": false,
          "recommended": true,
          "deprecated": false,
          "speed": 7,
          "quality": 9,
          "costPer1kInput": 0.00250,
          "costPer1kOutput": 0.01000
        }
      ],
      "created_at": "2026-07-23T10:00:00+00:00",
      "updated_at": "2026-07-23T10:00:00+00:00"
    }
  ]
}
```

### `GET /api/v1/providers/available-types`

List all supported provider types.

**Response 200:**
```json
{
  "types": [
    {
      "id": "google",
      "name": "Google AI Studio",
      "needs_endpoint": false,
      "default_endpoint": "https://generativelanguage.googleapis.com/v1beta",
      "has_models_endpoint": true
    },
    {
      "id": "groq",
      "name": "Groq",
      "needs_endpoint": false,
      "default_endpoint": "https://api.groq.com/openai/v1",
      "has_models_endpoint": true
    },
    {
      "id": "openai_compatible",
      "name": "OpenAI Compatible",
      "needs_endpoint": true,
      "default_endpoint": "",
      "has_models_endpoint": true
    }
  ]
}
```

### `POST /api/v1/providers`

Add a new provider.

**Request body:**
```json
{
  "provider_type": "openai",
  "name": "My OpenAI",
  "endpoint_url": null,
  "api_key": "sk-...",
  "organization": null,
  "temperature": null,
  "max_tokens": null,
  "streaming_enabled": true,
  "models_enabled": ["gpt-4o", "gpt-4o-mini"]
}
```

**Response 200:** Full provider object (same as GET /api/v1/providers entry).

**Errors:**
- `400` — Unknown provider type.

### `GET /api/v1/providers/{provider_id}`

Get a single provider with all details.

**Response 200:** Provider object.
**Response 404:** `{"detail": "Provider not found"}`

### `PUT /api/v1/providers/{provider_id}`

Update provider configuration.

**Request body:**
```json
{
  "name": "Renamed Provider",
  "endpoint_url": "https://custom.endpoint.com/v1",
  "api_key": "new-sk-...",
  "organization": "org-123",
  "temperature": 0.5,
  "max_tokens": 8192,
  "streaming_enabled": true,
  "model_updates": [
    {"id": "gpt-4o", "enabled": true},
    {"id": "gpt-3.5-turbo", "enabled": false}
  ]
}
```

All fields optional. Only provided fields are updated.

**Response 200:** Updated provider object.
**Response 404:** `{"detail": "Provider not found"}`

### `DELETE /api/v1/providers/{provider_id}`

Remove a provider and its stored API key.

**Response 200:** `{"status": "ok"}`
**Response 404:** `{"detail": "Provider not found"}`

### `PUT /api/v1/providers/{provider_id}/default`

Set a provider as the default.

**Response 200:** The provider object with `is_default: true`.
**Response 404:** `{"detail": "Provider not found"}`

### `PUT /api/v1/providers/reorder`

Reorder providers (influences routing priority).

**Request body:**
```json
{
  "provider_ids": ["openai-a1b2c3d4", "anthropic-e5f6g7h8", "google-i9j0k1l2"]
}
```

**Response 200:** `{"status": "ok"}`

### `POST /api/v1/providers/{provider_id}/test`

Test connection to a provider.

**Response 200:**
```json
{
  "success": true,
  "status": "connected",
  "latency_ms": 342
}
```

**Error response:**
```json
{
  "success": false,
  "error": "Invalid API key",
  "status": "invalid_key"
}
```

### `GET /api/v1/providers/test-all`

Test all configured providers concurrently.

**Response 200:**
```json
{
  "results": [
    {
      "provider_id": "openai-a1b2c3d4",
      "success": true,
      "status": "connected",
      "latency_ms": 342
    },
    {
      "provider_id": "anthropic-e5f6g7h8",
      "success": false,
      "error": "Invalid API key",
      "status": "invalid_key"
    }
  ]
}
```

## Model Management

### `GET /api/v1/providers/{provider_id}/models`

Fetch models from the provider API (with caching + catalog merge).

**Response 200:**
```json
{
  "models": [
    {
      "id": "gpt-4o",
      "displayName": "GPT-4o",
      "provider": "openai",
      "contextLength": 128000,
      "maxOutput": 16384,
      "supportsStreaming": true,
      "supportsVision": true,
      "enabled": true,
      ...
    }
  ]
}
```

### `PUT /api/v1/providers/{provider_id}/models`

Toggle a model's enabled state.

**Request body:**
```json
{
  "model_id": "gpt-3.5-turbo",
  "enabled": false
}
```

**Response 200:** Full provider object with updated models.
**Response 404:** `{"detail": "Provider not found"}`

### `POST /api/v1/providers/{provider_id}/models/refresh`

Force-refresh models from the provider API (bypasses cache).

**Response 200:**
```json
{
  "models": [...]
}
```

**Response 404:** `{"detail": "Provider not found"}`

## Routing

### `GET /api/v1/routing`

Get current routing configuration.

**Response 200:**
```json
{
  "routing": [
    {
      "id": "general_chat",
      "label": "General Chat",
      "provider_id": "openai-a1b2c3d4",
      "model_id": "gpt-4o"
    },
    {
      "id": "coding",
      "label": "Coding",
      "provider_id": "anthropic-e5f6g7h8",
      "model_id": "claude-sonnet-4-20250514"
    },
    {
      "id": "vision",
      "label": "Vision",
      "provider_id": "google-i9j0k1l2",
      "model_id": "gemini-2.5-flash"
    },
    {
      "id": "reasoning",
      "label": "Reasoning",
      "provider_id": "openai-a1b2c3d4",
      "model_id": "o3-mini"
    },
    {
      "id": "fallback",
      "label": "Fallback",
      "provider_id": "groq-m3n4o5p6",
      "model_id": "llama-3.3-70b-versatile"
    }
  ]
}
```

### `PUT /api/v1/routing`

Update routing configuration.

**Request body:**
```json
{
  "routing": [
    {
      "id": "general_chat",
      "label": "General Chat",
      "provider_id": "openai-a1b2c3d4",
      "model_id": "gpt-4o"
    },
    {
      "id": "coding",
      "label": "Coding",
      "provider_id": null,
      "model_id": null
    }
  ]
}
```

Setting `provider_id` to `null` enables automatic capability-based routing
for that category.

**Response 200:** Updated routing array.

## Chat / Conversations

### `POST /chat/conversation`

Create a new conversation.

**Query parameters:**
- `title` (optional) — Initial title.
- `project` (optional) — Active project context.

**Response 200:**
```json
{
  "id": "abc123def456",
  "title": "New Conversation",
  "created_at": "2026-07-23T10:00:00+00:00",
  "updated_at": "2026-07-23T10:00:00+00:00",
  "active_project": null,
  "is_active": true,
  "mode": "chat",
  "message_count": 0,
  "parent_id": null,
  "branch_point_message_id": null,
  "provider_id": null,
  "model_id": null,
  "temperature": null,
  "top_p": null,
  "top_k": null,
  "max_tokens": null,
  "system_prompt": null,
  "thinking_mode": false,
  "streaming_enabled": true
}
```

### `GET /chat/conversations`

List conversations.

**Query parameters:**
- `limit` (default: 50) — Max results.
- `offset` (default: 0) — Pagination offset.

**Response 200:**
```json
{
  "conversations": [...]
}
```

### `GET /chat/conversation/{conversation_id}`

Get a single conversation.

**Response 200:** Conversation object.
**Response 404:** `{"error": "Conversation not found"}`

### `PUT /chat/conversation/{conversation_id}`

Rename a conversation.

**Query parameters:**
- `title` (required) — New title.

**Response 200:** Updated conversation object.
**Response 404:** `{"error": "Conversation not found"}`

### `DELETE /chat/conversation/{conversation_id}`

Delete a conversation.

**Response 200:** `{"status": "deleted"}`
**Response 404:** `{"error": "Conversation not found"}`

### `POST /chat/message`

Send a non-streaming message.

**Request body:**
```json
{
  "conversation_id": null,
  "content": "Hello!",
  "stream": false
}
```

If `conversation_id` is null, a new conversation is created automatically.

**Response 200:**
```json
{
  "conversation_id": "abc123def456",
  "message_id": "msg789ghi012",
  "content": "Hello! How can I help you today?",
  "role": "assistant",
  "timestamp": "2026-07-23T10:00:00+00:00",
  "tokens_used": 12
}
```

**Errors:**
- `404` — Conversation not found.
- `503` — AI provider error.

### `POST /chat/stream`

Send a message and receive a streaming response via SSE.

**Request body:**
```json
{
  "conversation_id": "abc123def456",
  "content": "Explain quantum computing",
  "provider_id": "openai-a1b2c3d4",
  "model_id": "gpt-4o"
}
```

`provider_id` and `model_id` are optional. If provided, they override the
conversation's provider/model for this request.

**Response:** SSE stream with `data: {event}\n\n` format.

**Event types:**

| Event Type | Data Shape | Description |
|---|---|---|
| `token` | `{"token": "quantum"}` | Content token |
| `done` | `{}` | Stream completed |
| `error` | `{"error": "...", "recoverable": true}` | Stream error |
| `status` | `{"message": "Detected intent: question"}` | Status update |
| `tool_call` | `{"tool": "web_search"}` | Tool call requested |
| `tool_result` | `{"tool": "web_search", "result": ...}` | Tool call result |
| `planner_started` | `{"query": "..."}` | Planning begins |
| `planner_completed` | `{"steps": 3}` | Planning completed |
| `tool_requested` | `{"tool": "browser"}` | Tool execution begins |
| `tool_running` | `{"tool": "browser"}` | Tool in progress |
| `tool_completed` | `{"tool": "browser", "success": true, "duration_ms": 1200}` | Tool finished |
| `final_response` | `{}` | AI response begins |
| `memory_retrieval` | `{"count": 5}` | Memory retrieval |
| `context_loaded` | `{"app": "...", "file": "..."}` | Context loaded |
| `title_generated` | `{"title": "Quantum Computing"}` | Title generated |

### `GET /chat/history/{conversation_id}`

Get message history for a conversation.

**Query parameters:**
- `limit` (default: 100) — Max messages.
- `offset` (default: 0) — Pagination offset.

**Response 200:**
```json
{
  "messages": [
    {
      "id": "...",
      "conversation_id": "...",
      "role": "user",
      "content": "Hello",
      "timestamp": "...",
      "tokens_used": 3,
      "latency_ms": 0,
      "tool_calls": [],
      "metadata": {}
    }
  ]
}
```

**Response 404:** `{"error": "Conversation not found"}`

### `DELETE /chat/history/{conversation_id}`

Clear all messages in a conversation.

**Response 200:** `{"status": "cleared"}`
**Response 404:** `{"error": "Conversation not found"}`

## SSS / Streaming Protocol

Streaming uses standard Server-Sent Events (SSE):

```
POST /chat/stream
Content-Type: application/json

{"conversation_id": "abc", "content": "Hello"}
```

Response:
```
data: {"type": "status", "data": {"message": "Detected intent: conversation"}}

data: {"type": "final_response", "data": {}}

data: {"type": "status", "data": {"message": "Generating response..."}}

data: {"type": "token", "data": {"token": "Hello"}}

data: {"type": "token", "data": {"token": "!"}}

data: {"type": "done", "data": {}}
```

**Headers:**
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no` (disables Nginx buffering)

**Error recovery:** Non-fatal errors include `"recoverable": true`. The
frontend can continue streaming or display partial output. Fatal errors
close the stream.

## Error Codes

| HTTP Status | Meaning | Typical Cause |
|---|---|---|
| 400 | Bad Request | Unknown provider type, invalid model_id |
| 404 | Not Found | Provider or conversation doesn't exist |
| 503 | Service Unavailable | AI provider failed, all fallbacks exhausted |
| 500 | Internal Error | Unexpected backend exception |

**SSE-level errors** (not HTTP-level):
- `error` event with `recoverable: true` — provider stream failed but
  fallback may handle it.
- `error` event with `recoverable: false` — fatal, stream terminated.

## Rate Limiting

Rate limiting is currently **not enforced at the application level**.

Provider-level rate limits are detected by HealthMonitor:
- `429` response → `ProviderStatus.RATE_LIMITED`
- Health state transitions to `RATE_LIMITED`
- SmartRouter skips rate-limited providers

Quota exhaustion (`402` / `quota` keyword) → `ProviderStatus.QUOTA_EXCEEDED`
→ same skip behavior.
