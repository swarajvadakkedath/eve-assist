# Context Budget Clamp — Fix Report

## Summary
Added a runtime safeguard that clamps `max_tokens` to the remaining context window before sending any request to a provider. This prevents the `input_tokens + max_tokens > context_limit` failure that was occurring on HuggingFace and other small-context providers.

## Root Cause (Bug 3)
When Hermes sends a request, `max_tokens` is set from the user's config (e.g. `model.max_tokens: 8192`). However, no code checked whether `input_tokens + max_tokens` would exceed the provider's context limit. On HuggingFace (16,384 context), a large conversation could consume ~12,000 input tokens, and with `max_tokens: 8192`, the total would be ~20,192 — exceeding the 16,384 limit. The provider returns a 400 error.

## Fix
**Location:** `agent/transports/chat_completions.py` — `_build_kwargs_from_profile()` (profile path, line ~660) and legacy path (line ~447).

After `max_tokens` is resolved (from ephemeral > user > profile default > anthropic), a new block computes:

```python
remaining = context_length - approx_input_tokens - SAFETY_MARGIN  # margin=256
if remaining < 512:
    raise ValueError("Insufficient context budget for response: ...")
if resolved_max_tokens > remaining:
    resolved_max_tokens = remaining
```

**Data flow:** `build_api_kwargs()` in `chat_completion_helpers.py` now computes `context_length` (from `agent.context_compressor.context_length`) and `approx_input_tokens` (from `estimate_messages_tokens_rough()`), then passes both as params to the transport.

**Key design decisions:**
- 256-token safety margin accounts for tokenizer variance
- Raises `ValueError` when remaining < 512 (provider would reject anyway, but now with a clear error message)
- Clamping only activates when both `context_length` and `approx_input_tokens` are available (backward-compatible)
- Same logic applied to both profile and legacy paths

## Files Changed
| File | Change |
|------|--------|
| `agent/transports/chat_completions.py` | Added context-budget clamping in both `_build_kwargs_from_profile` and legacy path |
| `agent/chat_completion_helpers.py` | Compute `context_length` and `approx_input_tokens`, pass as params to transport |
| `tests/run_agent/test_primary_runtime_restore.py` | +4 tests in `TestContextBudgetClamp` |

## Tests (4 new, 36 total)
| Test | Validates |
|------|-----------|
| `test_small_prompt_not_clamped` | Small input → max_tokens passes through unchanged |
| `test_large_prompt_clamped` | Large input → max_tokens reduced to `context_limit - input - 256` |
| `test_insufficient_budget_raises` | Remaining < 512 → `ValueError` with diagnostic message |
| `test_no_context_length_skips_clamp` | Without context_length param → clamping skipped (backward-compat) |

**Results:** 42/42 pass (36 primary_runtime_restore + 5 context_token_tracking + 1 compressor_fallback_update).

## Verification
```bash
python -m pytest tests/run_agent/test_primary_runtime_restore.py -v
# 36 passed

python -m pytest tests/run_agent/test_primary_runtime_restore.py tests/run_agent/test_context_token_tracking.py tests/run_agent/test_compressor_fallback_update.py -v
# 42 passed
```

## All Three Bugs Now Fixed
| Bug | Symptom | Root Cause | Fix |
|-----|---------|------------|-----|
| Bug 1 | HTTP 400 on Gemini | Wrong `base_url` (`/v1beta` not `/v1beta/openai`) | Config fix |
| Bug 2 | HuggingFace token overflow | Fallback `max_tokens` not applied | `try_activate_fallback()` + `_primary_runtime` snapshot |
| Bug 3 | `input + max > context_limit` | No runtime budget check | Context-budget clamp in transport |
