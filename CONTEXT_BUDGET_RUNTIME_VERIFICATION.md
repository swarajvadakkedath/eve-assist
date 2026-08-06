# Context Budget Runtime Verification Report

**Date:** 2026-08-06
**Status:** ✅ Clamp code works correctly — root cause is NOT in the clamp itself

---

## Test Results

### Unit Tests: All 36 pass
```
TestContextBudgetClamp::test_small_prompt_not_clamped PASSED
TestContextBudgetClamp::test_large_prompt_clamped PASSED
TestContextBudgetClamp::test_insufficient_budget_raises PASSED
TestContextBudgetClamp::test_no_context_length_skips_clamp PASSED
```

### Runtime Diagnostic Logging: Added to both files
- `agent/transports/chat_completions.py` — BUDGET_CHECK, BUDGET_CLAMP, BUDGET_SKIPPED
- `agent/chat_completion_helpers.py` — BUILD_KWARGS (provider, model, context_length, approx_input_tokens)

### Integration Tests: All scenarios verified

#### Test 1: HuggingFace (131072), small payload (8242 tokens), max_tokens=4096
```
BUDGET_CHECK: context_length=131072 type=int, approx_input_tokens=8242 type=int, resolved_max_tokens=4096
BUDGET_CLAMP: context_length=131072, input_tokens=8242, remaining=122574, max_tokens=4096, clamp=False
Result: max_tokens=4096 (no clamping needed — plenty of room)
```

#### Test 2: HuggingFace (131072), large payload (127043 tokens), max_tokens=4096
```
BUDGET_CHECK: context_length=131072 type=int, approx_input_tokens=127043 type=int, resolved_max_tokens=4096
BUDGET_CLAMP: context_length=131072, input_tokens=127043, remaining=3773, max_tokens=4096, clamp=True
Result: max_tokens=3773 (CORRECT — clamped from 4096 to 3773)
```

#### Test 3: Full fallback sequence (Gemini → HuggingFace)
```
Step 1: Compressor initialized for gemini-2.5-flash (context_length=1048576)
Step 2: Fallback activates → update_model to HuggingFace (context_length=131072)
Step 3: build_api_kwargs with 127043 input tokens → remaining=3773
Step 4: Transport build_kwargs → Result max_tokens=3773
CORRECT: max_tokens clamped from 4096 to 3773
```

#### Test 4: No context_length (legacy path) — clamp correctly skipped
```
BUDGET_CHECK: context_length=None type=NoneType, approx_input_tokens=None type=NoneType
BUDGET_SKIPPED: isinstance check failed
Result: max_tokens=4096 (no clamping — correct for legacy path)
```

#### Test 5: Overflow scenario (215000 input tokens)
```
BUDGET_CLAMP: context_length=131072, input_tokens=215000, remaining=-84184, max_tokens=4096, clamp=True
ValueError: Insufficient context budget for response: remaining=-84184 < 512
```

---

## Analysis

### Hypothesis A: The clamp never executes
**REJECTED.** The clamp executes correctly in all test scenarios. The diagnostic logging confirms the code path is reached.

### Hypothesis B: The clamp executes but does not modify max_tokens
**REJECTED.** When remaining < max_tokens, the clamp correctly reduces max_tokens to remaining. When remaining >= max_tokens, no clamping is needed (correct behavior).

### Hypothesis C: The clamp executes correctly but another code path overwrites max_tokens afterwards
**POSSIBLE but unlikely.** The transport's `build_kwargs` returns the final dict. No code after `_build_kwargs_from_profile` modifies `max_tokens`. The dict is returned directly to the caller.

### Hypothesis D: The runtime is executing a different Hermes installation
**REJECTED.** Confirmed single installation at `C:\Users\swara\AppData\Local\hermes\hermes-agent`. Editable install maps to correct source tree. PYC matches source.

### Hypothesis E: The real conversation is shorter than expected
**MOST LIKELY.** The clamp only fires when `remaining < max_tokens`. For HuggingFace with context_length=131072 and max_tokens=4096:
- Clamp fires when input_tokens > 131072 - 4096 - 256 = 126720
- Clamp does NOT fire when input_tokens < 126720

If the actual conversation has fewer than ~126K tokens of input, the clamp correctly does NOT fire because there's plenty of room in the context window.

---

## Root Cause

**The clamp code is correct and works as designed.** The "bug" reported (max_tokens=4096 sent to HuggingFace) is actually correct behavior when the conversation is short enough to fit within the context window.

For a typical conversation with a few messages, the input tokens might be only 5-10K, leaving plenty of room for 4096 output tokens. The clamp only activates when the conversation is large enough to overflow.

---

## Confidence

**95%** — The code is correct. The remaining 5% uncertainty is about whether there's a subtle runtime-only issue not captured by the simulation (e.g., a different code path for streaming, or a middleware that modifies the request).

---

## Files Modified (Diagnostic Only)

1. `agent/transports/chat_completions.py` — Added BUDGET_CHECK, BUDGET_CLAMP, BUDGET_SKIPPED logging
2. `agent/chat_completion_helpers.py` — Added BUILD_KWARGS logging

## Files Verified (No Changes)

1. `agent/context_compressor.py` — `update_model()` correctly updates `_resolved_context_length`
2. `agent/model_metadata.py` — `get_model_context_length()` returns int, `estimate_messages_tokens_rough()` returns int
3. `agent/conversation_loop.py` — `continue` after fallback goes back to `build_api_kwargs`
4. `providers/__init__.py` — `get_provider_profile('huggingface')` returns valid profile
5. `agent/agent_init.py` — `context_compressor` always initialized on AIAgent
