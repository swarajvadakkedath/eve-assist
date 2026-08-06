# TOOL_EXECUTION_FIX_REPORT

**Date:** 2026-08-06
**Scope:** LLM native tool execution — tool definitions never reached the provider.
**Constraint honored:** Architecture unchanged (Phase C.8 intact). No new features, no registry duplication, all public interfaces preserved.

---

## Root Cause Addressed

`ConversationManager._run_tool_loop()` and `ConversationManager.stream_message()`
built their `AIRequest` with only `messages`, `stream`, `max_tokens`, `temperature`,
`provider_id`, and `model`. The OpenAI-native **`tools`** and **`tool_choice`** fields
were **never populated**.

Tool knowledge only reached the LLM as **plain text** inside the system prompt
(`build_tool_descriptions(...)`). Because the outbound provider request carried no
structured tool schemas, models could not emit native `tool_calls`. Instead they were
observed emitting **raw `<tool_call>` markup in the natural-language response**,
which `_run_tool_loop` returned verbatim (its `ai_response.tool_calls` list stayed empty).

This was a **data-flow gap, not a design flaw**:

1. `ChatRequest` already defined `tools` / `tool_choice` (`core/adapters/base.py`).
2. The OpenAI-compatible, OpenAI, Groq, Cloudflare, Anthropic, and Cohere adapters already
   serialized `request.tools` into the outbound payload (`chat` and `stream`).
3. `SmartRouter._make_request` already propagated `tools` + `tool_choice` to the adapter.
4. The execution loop already parsed `ai_response.tool_calls`, executed them via
   `ToolMediator`, and fed `role="tool"` results back to the LLM.

The fix simply **wires the existing registry into the request** at the three choke points,
plus carries `tool_choice` through `SmartRouter._to_chat_request`.

---

## Files Modified

| File | Change |
|------|--------|
| `src/backend/aios/conversation/manager.py` | Added `ConversationManager._build_tool_definitions()` — derives OpenAI-format `tools` **from the existing ToolManager registry** (`_get_available_tools()` → `ToolContract`). Returns `[]` when no tools registered. |
| `src/backend/aios/conversation/manager.py` | `_run_tool_loop()` now sets `req.tools` (computed once per loop) and `req.tool_choice = "auto"` on every iteration. |
| `src/backend/aios/conversation/manager.py` | `stream_message()` now sets `req.tools` and `req.tool_choice = "auto"` using the **identical mechanism**. |
| `src/backend/aios/core/smart_router.py` | `SmartRouter._to_chat_request()` now maps `tool_choice` from the request (it already mapped `tools`), so `ChatRequest` handed to adapters carries both fields. |
| `tests/provider_framework/test_tool_execution.py` | **New** — 15 focused regression tests. |
| `desktop/src-tauri/backend/aios/conversation/manager.py` | Mirror of the source change. |
| `desktop/src-tauri/backend/aios/core/smart_router.py` | Mirror of the source change. |

No adapter, router-selection, registry, or interface code was redesigned.

---

## Tests Added

`tests/provider_framework/test_tool_execution.py` — **15 tests** proving the full path:

1. **Tool definitions present in `AIRequest`** — `_run_tool_loop()` request carries the
   OpenAI function schema (`type`, `function.name`, `function.description`,
   `function.parameters`) built from the real ToolManager registry.
2. **`tool_choice` set** — request has `tool_choice == "auto"`.
3. **Schema shape** — tool entry is `{type: function, function: {...}}`.
4. **Empty registry** — no tools registered → `req.tools == []` (providers never get a stale schema).
5. **Dict-entry tolerance** — `_build_tool_definitions()` also accepts `ToolMediator.list_tools()`-style dicts.
6. **`stream_message()` identical mechanism** — streaming request carries the same `tools` + `tool_choice`.
7. **SmartRouter receives tools** — `_to_chat_request` produces a `ChatRequest` with populated `tools`.
8. **SmartRouter carries `tool_choice`** — round-trips through `_to_chat_request`.
9. **`_make_request` preserves tools + tool_choice** after model resolution.
10. **Provider payload contains tools** — OpenAI-compatible adapter's outbound JSON body
    contains `tools` and `tool_choice` (asserted via `httpx.MockTransport`).
11. **Provider payload omits tools when absent** — backward-compatible behavior preserved.
12. **`tool_calls` are returned** — adapter parses provider `tool_calls` into `ChatResponse.tool_calls`.
13. **`ToolMediator` executes** — real registry + real `ToolMediator` run the tool; handler called
    with the parsed arguments; audit log records success.
14. **`ToolResult` sent back to the LLM** — the second LLM request's `messages` contains a
    `role="tool"` message with `tool_call_id` and the tool's result content.
15. **Final response is natural language** — loop returns plain text; neither the returned
    content nor the stored assistant message contains `<tool_call>` markup.

---

## Regression Results

| Suite | Result |
|-------|--------|
| `tests/provider_framework/test_tool_execution.py` (new) | **15/15 passed** |
| `tests/provider_framework` (full) | **1363 passed** (includes all prior 1348 + 15 new) |
| `src/backend/aios/tests/test_quota_aware_routing.py` + `test_routing_policy.py` (legacy routing) | **99/99 passed** |
| `tests/provider_framework/test_desktop_integration.py` | **13/13 passed** |
| Desktop mirror imports (`desktop/src-tauri/backend/aios`) | Clean import of both modified modules |
| Desktop ↔ source byte-parity (`git diff --no-index`) | **Identical** |
| `py_compile` of all 4 modified source/mirror files | OK |

### Pre-existing failures (NOT introduced by this change — confirmed at `HEAD` via `git stash`)
- `tests/unit/test_conversation_manager.py` / `test_conversation_service.py` / `test_planner.py`
  — their `FakeAIRouter.route()` signatures don't accept the `routing_policy` kwarg added in
  **W4**. Reproduced at `HEAD` with the working tree stashed; unrelated to tool execution.
- Known machine quirk: full `pytest tests/` aggregate aborts with the pre-existing
  `bestrelpath` `INTERNALERROR` (`'E:\Eve_Ai' is not in the subpath of 'E:\Eve_Ai'`).
  Files are therefore run individually or by group, as documented in AGENTS.md.

---

## Why This Is Not a Redesign

- **No registry duplication** — `_build_tool_definitions()` reads the existing
  `ToolManager` registry through the existing `_get_available_tools()`; it maintains nothing.
- **No new subsystems** — the execution loop, `ToolMediator`, `ChatRequest`, adapter
  serialization, and `SmartRouter` routing all existed and are unchanged in behavior.
- **All public interfaces preserved** — `ConversationManager`, `SmartRouter`,
  `ToolMediator`, adapters, and their method signatures are untouched.
- **Phase C.8 architecture intact** — the fix fills a data-flow gap (tool schemas were
  not placed on the outbound request), which is exactly where the architecture intended
  them to travel.
