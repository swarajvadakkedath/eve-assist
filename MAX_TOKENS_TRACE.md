# MAX_TOKENS TRACE

Tracing the value `8192` from config → parsed → runtime → HTTP payload for the HuggingFace fallback provider.

---

## Executive Summary

**`fallback_providers[].max_tokens: 4096` is dead data.** The config parses it correctly into the fallback chain dict, but `try_activate_fallback()` never reads it. The global `model.max_tokens: 8192` from the primary Gemini config persists as the output cap for ALL fallback providers.

---

## The Trace

### Layer 1: Config File

**File:** `C:\Users\swara\AppData\Local\hermes\profiles\hermes-dev\config.yaml`

```yaml
model:
  default: "gemini-2.5-flash"
  provider: "gemini"
  api_key: "${GOOGLE_API_KEY}"
  base_url: "https://generativelanguage.googleapis.com/v1beta/openai"
  api_mode: "openai"
  max_tokens: 8192          # ← PRIMARY model output cap

fallback_providers:
  - provider: "huggingface"
    model: "Qwen/Qwen2.5-7B-Instruct"
    base_url: "https://router.huggingface.co/v1"
    key_env: "HF_TOKEN"
    max_tokens: 4096         # ← Per-fallback output cap (DEAD — never consumed)
```

### Layer 2: Config Parsing — `model.max_tokens`

**File:** `C:\Users\swara\AppData\Local\hermes\hermes-agent\agent\agent_init.py`
**Lines 2087–2113**

```python
# Read explicit model output-token override from config when the
# caller did not pass one directly.
_model_cfg = _agent_cfg.get("model", {})
if agent.max_tokens is None and isinstance(_model_cfg, dict):
    _config_max_tokens = _model_cfg.get("max_tokens")    # ← reads 8192
    if _config_max_tokens is not None:
        try:
            if isinstance(_config_max_tokens, bool):
                raise ValueError
            _parsed_max_tokens = int(_config_max_tokens)
            if _parsed_max_tokens <= 0:
                raise ValueError
            agent.max_tokens = _parsed_max_tokens         # ← agent.max_tokens = 8192
        except (TypeError, ValueError):
            ...
agent._session_init_model_config["max_tokens"] = agent.max_tokens
```

**Result:** `agent.max_tokens = 8192`

### Layer 3: Config Parsing — `fallback_providers`

**File:** `C:\Users\swara\AppData\Local\hermes\hermes-agent\hermes_cli\fallback_config.py`
**Lines 43–69**

```python
def _iter_fallback_entries(raw: Any) -> list[dict[str, Any]]:
    ...
    for entry in candidates:
        ...
        normalized = dict(entry)       # ← ALL fields preserved, including max_tokens
        normalized["provider"] = provider
        normalized["model"] = model
        ...
        entries.append(normalized)     # ← entry = {"provider":"huggingface", ..., "max_tokens": 4096}
```

**Lines 80–101:**

```python
def get_fallback_chain(config: dict[str, Any] | None) -> list[dict[str, Any]]:
    ...
    for key in ("fallback_providers", "fallback_model"):
        for entry in _iter_fallback_entries(config.get(key)):
            ...
            chain.append(entry)        # ← entry with max_tokens: 4096 goes into chain
    return chain
```

**Result:** `agent._fallback_chain[1]` = `{"provider": "huggingface", "model": "Qwen/...", "max_tokens": 4096, ...}`

The `max_tokens: 4096` is **correctly parsed and stored** in the chain. It is dead data because no consumer reads it.

### Layer 4: Fallback Activation — `try_activate_fallback()`

**File:** `C:\Users\swara\AppData\Local\hermes\hermes-agent\agent\chat_completion_helpers.py`
**Lines 1746–1896**

```python
fb = agent._fallback_chain[agent._fallback_index]   # ← fb = {"provider":"huggingface", ..., "max_tokens": 4096}
agent._fallback_index += 1
...
fb_provider = (fb.get("provider") or "").strip().lower()   # ← reads "huggingface"
fb_model = (fb.get("model") or "").strip()                  # ← reads "Qwen/Qwen2.5-7B-Instruct"
...
# Lines 1882–1893 — the properties that ARE swapped:
old_model = agent.model
old_provider = agent.provider
agent._config_context_length = None
agent.model = fb_model                 # ← SWAPPED
agent.provider = fb_provider           # ← SWAPPED
agent.requested_provider = fb_provider # ← SWAPPED
agent.base_url = fb_base_url           # ← SWAPPED
agent.api_mode = fb_api_mode           # ← SWAPPED

# agent.max_tokens = ???             ← NEVER SET FROM fb.get("max_tokens")
```

**Result:** `agent.max_tokens` remains `8192` after fallback activation.

### Layer 5: Primary Runtime Snapshot — `_primary_runtime`

**File:** `C:\Users\swara\AppData\Local\hermes\hermes-agent\agent\agent_init.py`
**Lines 2775–2794**

```python
agent._primary_runtime = {
    "model": agent.model,
    "provider": agent.provider,
    "requested_provider": agent.requested_provider,
    "base_url": agent.base_url,
    "api_mode": agent.api_mode,
    "api_key": getattr(agent, "api_key", ""),
    "client_kwargs": dict(agent._client_kwargs),
    "use_prompt_caching": agent._use_prompt_caching,
    "use_native_cache_layout": agent._use_native_cache_layout,
    # ... compressor state ...
}
# NO max_tokens field
```

**Result:** `_primary_runtime` does NOT snapshot `max_tokens`.

### Layer 6: Primary Runtime Restoration — `restore_primary_runtime()`

**File:** `C:\Users\swara\AppData\Local\hermes\hermes-agent\agent\agent_runtime_helpers.py`
**Lines 1532–1543**

```python
rt = agent._primary_runtime
agent.model = rt["model"]
agent.provider = rt["provider"]
agent.requested_provider = rt.get("requested_provider", agent.provider)
agent.base_url = rt["base_url"]
agent.api_mode = rt["api_mode"]
agent.api_key = rt["api_key"]
agent._client_kwargs = dict(rt["client_kwargs"])
agent._use_prompt_caching = rt["use_prompt_caching"]
# NO max_tokens restoration
```

**Result:** Even when restoring to the primary provider, `max_tokens` is never touched. (Moot — it was never changed.)

### Layer 7: Request Construction — `_build_kwargs_from_profile()`

**File:** `C:\Users\swara\AppData\Local\hermes\hermes-agent\agent\transports\chat_completions.py`
**Lines 640–657**

```python
# max_tokens resolution — priority: ephemeral > user > profile default
max_tokens_fn = params.get("max_tokens_param_fn")
ephemeral = params.get("ephemeral_max_output_tokens")
user_max = params.get("max_tokens")               # ← this is agent.max_tokens = 8192
anthropic_max = params.get("anthropic_max_output")
profile_max = profile.get_max_tokens(model)        # ← HuggingFace profile returns None

if ephemeral is not None and max_tokens_fn:
    api_kwargs.update(max_tokens_fn(ephemeral))
elif user_max is not None and max_tokens_fn:
    api_kwargs.update(max_tokens_fn(user_max))     # ← HITS THIS: max_tokens_fn(8192)
elif profile_max and max_tokens_fn:
    api_kwargs.update(max_tokens_fn(profile_max))
elif anthropic_max is not None:
    api_kwargs["max_tokens"] = anthropic_max
```

**Result:** `api_kwargs["max_tokens"] = 8192`

### Layer 8: Parameter Name Mapping — `_max_tokens_param()`

**File:** `C:\Users\swara\AppData\Local\hermes\hermes-agent\run_agent.py`
**Lines 1606–1628**

```python
def _max_tokens_param(self, value: int) -> dict:
    if (
        self._is_direct_openai_url()
        or self._is_azure_openai_url()
        or self._is_github_copilot_url()
        or model_forces_max_completion_tokens(self.model)
    ):
        return {"max_completion_tokens": value}
    return {"max_tokens": value}              # ← HuggingFace hits this
```

**Result:** `{"max_tokens": 8192}` in the HTTP request body.

### Layer 9: HTTP Payload

The wire payload sent to `https://router.huggingface.co/v1/chat/completions`:

```json
{
  "model": "Qwen/Qwen2.5-7B-Instruct",
  "messages": [...],
  "max_tokens": 8192
}
```

HuggingFace's TGI backend translates `max_tokens` → `max_new_tokens` internally.

**Result:** Provider sees `inputs=25329 + max_new_tokens=8192 = 33521 > 32768 limit` → error.

---

## Where 8192 First Appears

| Layer | Location | Value |
|-------|----------|-------|
| Config file | `config.yaml:14` | `max_tokens: 8192` (model section) |
| Config parsing | `agent_init.py:2099` | `agent.max_tokens = 8192` |
| Session init | `agent_init.py:2113` | `agent._session_init_model_config["max_tokens"] = 8192` |
| Fallback activation | `chat_completion_helpers.py:1882–1893` | `agent.max_tokens` **NOT updated** (stays 8192) |
| Primary snapshot | `agent_init.py:2775–2794` | `max_tokens` **NOT stored** in `_primary_runtime` |
| Primary restore | `agent_runtime_helpers.py:1532–1543` | `max_tokens` **NOT restored** |
| Request build | `chat_completions.py:643,653` | `user_max = params.get("max_tokens")` → `8192` |
| Wire format | HTTP POST body | `"max_tokens": 8192` |

---

## Root Cause

`try_activate_fallback()` in `agent/chat_completion_helpers.py` (line 1695+) switches `agent.model`, `agent.provider`, `agent.base_url`, `agent.api_mode`, `agent.client`, and `agent.api_key` from the fallback entry, but **never reads or applies `fb.get("max_tokens")`** to `agent.max_tokens`. The global `model.max_tokens: 8192` from `config.yaml` persists as the effective output cap for every fallback provider.

The `fallback_providers[].max_tokens: 4096` field in the config is correctly parsed into the chain entry dict (by `fallback_config.py`), but is dead data — no code path ever consumes it.

---

## Secondary Issue

`_primary_runtime` (the snapshot used to restore the primary provider after fallback) does not store `max_tokens`. `restore_primary_runtime()` does not restore it. This means even if `try_activate_fallback` were fixed to set `agent.max_tokens = fb.get("max_tokens")`, there would be no restoration mechanism for the primary provider's `max_tokens` after fallback deactivation.

---

*Trace complete. All values verified against source code at C:\Users\swara\AppData\Local\hermes\hermes-agent.*
