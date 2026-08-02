# Provider Framework

## Quick Start: Adding a New Provider

**If your provider uses an OpenAI-compatible API** (e.g. `/v1/chat/completions`), you only need to add one entry to `src/backend/aios/core/provider_registry.py`:

```python
from aios.core.provider_registry import register, ProviderDefinition

register(ProviderDefinition(
    provider_type="my_provider",          # unique ID
    display_name="My Provider",           # display name
    default_endpoint="https://api.my.com/v1",
    adapter_class="OpenAICompatibleAdapter",
    openai_compatible=True,
    commercial_policy="free_tier",        # or "generic", "local", "openrouter", etc.
    discovery_strategy="openai_v1",       # or "lmstudio", "static", "native"
    api_key_required=True,
    needs_endpoint=False,
    icon="rocket",
))
```

That's it. No changes to ProviderManager, SmartRouter, or frontend code needed.

**If your provider has a native API** (like Anthropic or Google), you also need to write an adapter class and add a builder to `provider_factory.py`.

---

## Architecture

```
┌─────────────────────┐     ┌─────────────────────┐
│   ProviderRegistry  │     │   ProviderFactory    │
│  (ProviderDefinition│────▶│  (create_adapter())  │
│   per provider type)│     │                      │
└─────────────────────┘     └─────────┬───────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │
              ┌─────▼─────┐   ┌──────▼──────┐   ┌──────▼──────┐
              │ Native     │   │ OpenAI      │   │ Onboarding  │
              │ Adapters   │   │ Compatible  │   │ Service     │
              │ (google,   │   │ Adapter     │   │ (API field  │
              │  openai,   │   │ (config-    │   │  rendering) │
              │  anthropic,│   │  driven)    │   │             │
              │  ollama,   │   │             │   │             │
              │  cohere,   │   └─────────────┘   └─────────────┘
              │  groq)     │
              └────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **ProviderRegistry** | `core/provider_registry.py` | Single source of truth for all provider metadata |
| **ProviderFactory** | `core/provider_factory.py` | Creates adapter instances from registry definitions |
| **OpenAICompatibleAdapter** | `core/adapters/openai_compatible_adapter.py` | Config-driven adapter for OpenAI-compatible APIs |
| **OnboardingService** | `core/onboarding.py` | Resolves which fields a provider needs for setup |
| **API Endpoint** | `api/providers.py` | `POST /providers/onboard` + enriched `available-types` |

### Data Flow

```
1. ProviderDefinition registered in registry
2. User calls POST /providers/onboard with {provider_type, api_key}
3. OnboardingService checks registry for required fields
4. ProviderManager.add_provider() stores provider config
5. ProviderFactory.create_adapter() looks up definition → instantiates correct adapter
6. Adapter gets extra_headers, commercial_policy, discovery_strategy from metadata
7. Frontend reads available-types → renders dynamic form fields
```

---

## Adding a Native Adapter

If your provider has a non-OpenAI API:

1. **Write the adapter** in `core/adapters/my_adapter.py`:
   ```python
   class MyAdapter(AIProviderAdapter):
       def __init__(self, api_key="", base_url="", timeout_config=None, streaming_manager=None):
           ...
       async def connect(self) -> ProviderStatus: ...
       async def list_models(self) -> list[ModelInfo]: ...
       async def chat(self, request: ChatRequest) -> ChatResponse: ...
       async def stream(self, request: ChatRequest) -> AsyncIterator[str]: ...
       async def health(self) -> ProviderStatus: ...
   ```

2. **Register in registry** with `adapter_class="MyAdapter"`

3. **Add builder to factory** in `provider_factory.py`:
   ```python
   def _create_my(*, definition, api_key, base_url, ...):
       from aios.core.adapters.my_adapter import MyAdapter
       return MyAdapter(api_key=api_key, base_url=base_url, ...)

   native_map["MyAdapter"] = _create_my
   ```

---

## Configuration Reference

### ProviderDefinition Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider_type` | str | required | Unique identifier |
| `display_name` | str | required | Human-readable name |
| `default_endpoint` | str | `""` | Default API base URL |
| `adapter_class` | str | `"OpenAICompatibleAdapter"` | Adapter class name |
| `openai_compatible` | bool | `True` | Whether the API is OpenAI-compatible |
| `api_key_required` | bool | `True` | Whether an API key is needed |
| `needs_endpoint` | bool | `False` | Whether endpoint URL must be user-provided |
| `supports_organization` | bool | `False` | Whether org ID field should be shown |
| `discovery_strategy` | str | `"openai_v1"` | Model discovery method |
| `commercial_policy` | str | `"generic"` | How to classify model pricing |
| `extra_headers` | dict | `{}` | Extra HTTP headers for API calls |
| `icon` | str \| None | `None` | Frontend icon key |

### Commercial Policies

| Policy | Behavior |
|--------|----------|
| `generic` | Check pricing fields for zero-cost |
| `openrouter` | OpenRouter-specific pricing + `:free` suffix |
| `local` | Always LOCAL + free |
| `free_tier` | Always FREE_TIER + free |
| `mistral` | Check pricing, fallback to PAID |
| `cerebras` | Always PAID |
| `credit_based` | Always CREDIT_BASED |
| `paid` | Always PAID |

### Discovery Strategies

| Strategy | Behavior |
|----------|----------|
| `openai_v1` | Standard `GET /models` endpoint |
| `lmstudio` | LM Studio native `/api/v1/models` + fallback |
| `static` | No API discovery, use catalog only |
| `native` | Provider-specific discovery logic |

---

## API Endpoints

### `GET /api/v1/providers/available-types`
Returns all registered provider types with metadata (needs_endpoint, icon, etc.).

### `POST /api/v1/providers/onboard`
Add a new provider instance using minimal input:
```json
{
  "provider_type": "openai",
  "api_key": "sk-...",
  "name": "My OpenAI"
}
```

---

## Test Framework

Tests are in `tests/provider_framework/`:

- `test_registry.py` — Registry CRUD and builtin verification
- `test_factory.py` — Factory creates correct adapter classes
- `test_onboarding.py` — Onboarding field resolution
- `test_contract_suite.py` — 96 tests verifying every adapter satisfies `AIProviderAdapter`
- `fake_adapter.py` — Reusable `FakeAdapter` for unit tests

Run all: `pytest tests/provider_framework/ -v`
