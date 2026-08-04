# EVE v1.2.3 — Chat "Empty Response" & Retry Bug Report

Status: root causes identified — fixes NOT yet implemented (per instructions)
Report date: 2026-08-04

---

## Executive summary

Two independent, unrelated bugs were confirmed.

### Bug 1 — "The provider returned an empty response." (tool-style prompts)

**The empty response is NOT caused by tool-call handling.** Live-log evidence shows all 6
`stream.empty_response` occurrences were preceded by a provider *transport/HTTP failure*:

| # | backend.log line | conversation | provider / model | underlying failure |
|---|---|---|---|---|
| 1 | 21492 | f4e3f830… | ollama `localhost:11434/api/chat` | **404 Not Found** (daemon/model missing) |
| 2 | 24069 | 6d22aa… | google `gemini-1.5-flash:streamGenerateContent?alt=sse` | **404 Not Found** (model EOL / not in account) |
| 3 | 24103 | 6d22aa… | google `gemini-1.5-flash` | **404 Not Found** (user re-sent) |
| 4 | 24290 | 212eeb… | nvidia `meta/llama-3.3-70b-instruct` | **60 s silent timeout** (connection held, no data) |
| 5 | 29718 | e7e723… | nvidia `meta/llama-3.3-70b-instruct` | **60 s silent timeout** ("what can you do?") |
| 6 | 30355 | e7e723… | nvidia `meta/llama-3.3-70b-instruct` | **60 s silent timeout** ("find "De Sales.png" in the system") |

The tool-style prompt in the bug report ("find image from the files.") is a **coincidence**:
the same conversation (`e7e723…`) produced an identical empty response for the plain question
"what can you do?" (line 29718). The common factor is not the prompt's intent — it is that the
SmartRouter selected a provider/model that then failed at the HTTP layer, and the failure was
swallowed into a generic "empty response" message.

### Bug 2 — Retry regenerates the previous successful assistant response

Confirmed: `retryLast` is a **pure local-state mutation** in the frontend. It slices the failed
user message (and its empty assistant bubble) out of the local message array, clears the error,
and **never calls the backend** — the failed prompt is never actually re-sent. Because the slice
removes the last two messages, the conversation appears to "go back" to the previous *successful*
assistant response, which is exactly what the user observed.

---

## Bug 1 — root cause chain (3 defects + 2 contributing factors)

### Defect A — No failover at stream time (`SmartRouter.route_stream`)

`src/backend/aios/core/smart_router.py:603-632` — `route_stream` resolves **one** candidate
(`_resolve_route` → `_resolve_auto`), then:

```python
async def _token_generator():
    try:
        async for token in result.candidate.adapter.stream(result.request):
            yield token
    except Exception:
        # Post-token failure: do NOT attempt failover (avoid duplicate answers)
        raise
```

There is **no attempt to try the next-ranked candidate** once the chosen provider fails, even
when the provider fails *before emitting a single token* (404, timeout). Failover in AUTO mode
only exists at candidate-*selection* time (`_resolve_auto` → `_filter_eligible`), not at
stream time. So a broken top-ranked provider guarantees a failed response.

### Defect B — Broken retry in `StreamManager.stream` (`conversation/stream.py`)

`src/backend/aios/conversation/stream.py:37-64` — the retry loop re-iterates the **same async
generator object** after it raised:

```python
while retries <= max_retries:
    try:
        async for token in token_generator:      # <-- same generator each attempt
            ...
        yield create_done_event(...)
        return
    except ... Exception as e:
        retries += 1
        if retries <= max_retries:
            yield create_status_event("retrying", ...)
            await asyncio.sleep(retries * 0.5)
        ...
```

An async generator that raised an exception is **closed/exhausted**. Re-iterating it completes
immediately with zero tokens, so the "retry" emits a `done` event with no content and returns
**without error**. This is why the log shows exactly one `stream.error attempt=1` followed by a
successful-looking empty `done` (e.g. line 24290: `first_yield` at 60 078 ms = the "retrying…"
status, `exiting` at 60 578 ms = the empty `done`).

### Defect C — Error masking in `ConversationManager.stream_message`

`src/backend/aios/conversation/manager.py:638-641`:

```python
if not full_content and not had_error:
    logger.error("stream.empty_response", conversation_id=conversation_id)
    yield create_error_event("The provider returned an empty response.", recoverable=True)
    return
```

Because Defect B leaves `had_error = False` and `full_content = ""`, the real cause
(404 / 60 s timeout) is hidden behind "The provider returned an empty response." The user and
the routing/health subsystems never learn that the provider is actually broken.

### Contributing factor 1 — no health feedback for chat/stream failures

`HealthMonitor.record_failure` is only ever called from the monitor's **own background health
check** (`src/backend/aios/core/health_monitor.py:271-325`). No adapter, router, or stream path
records a chat failure. Consequence: after a provider 404s or times out on a real message, its
health score stays healthy, so the router **keeps selecting it** on the next message — observed
in the logs: nvidia `meta/llama-3.3-70b-instruct` was selected for 3 separate failing messages.

### Contributing factor 2 — timeout layering

`TimeoutConfig.chat = 60.0` (`src/backend/aios/core/timeout_retry.py:53`) is the httpx client
read timeout, which fires first at 60 s when the provider sends nothing; the outer
`asyncio.timeout` in `StreamingManager.stream` is 120 s (`streaming_manager.py:94`). The observed
~60 s failures are the httpx `ReadTimeout` (whose `str()` is empty — matching the blank
`error=` in the log lines 24290/29718/30355).

Note: `extract_openai_chunk` (`streaming_manager.py:251-257`) returns `""` for chunks with no
`content` field (e.g. tool-call-only deltas), so a provider that answered with only `tool_calls`
would also produce a zero-token stream — but that is **not** the failure mode observed in the
live logs.

### Exact files/functions for Bug 1

- `src/backend/aios/core/smart_router.py` → `route_stream` / `_token_generator` (:620-626) — no failover.
- `src/backend/aios/conversation/stream.py` → `StreamManager.stream` (:37-64) — broken retry re-iterates exhausted generator.
- `src/backend/aios/conversation/manager.py` → `stream_message` (:638-641) — empty-response masking.
- `src/backend/aios/core/health_monitor.py` (+ adapters) — no `record_failure` on chat failures.
- `src/backend/aios/core/timeout_retry.py` — `TimeoutConfig.chat = 60.0`.

---

## Bug 2 — root cause (Retry)

### The frontend bug

`src/frontend/src/components/conversation/ConversationView.tsx:279-290`:

```ts
const retryLast = useCallback(() => {
    const { messages } = state;
    if (messages.length === 0) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      setState((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
        error: null,
      }));
    }
}, [state, setState]);
```

Sequence on an empty-response failure:

1. `sendMessage` (ConversationView.tsx:91) appends the user message optimistically.
2. Backend yields `done` (stream.py:45) with **zero tokens**, then the empty-response error.
   The frontend `done` handler (ConversationView.tsx:196-232) appends an **assistant message
   with empty `content`** (`` `fullContent` is `""` ``), so `messages` ends as
   `[ …, userMsg, assistantMsg("") ]`.
3. `retryLast` runs `messages.slice(0, -2)` → removes **both** the failed user message **and** the
   empty assistant bubble, and clears `error`.

Result: the failed user message is silently dropped from the UI, the conversation appears to end
at the *previous successful assistant response*, and nothing is re-sent. This is the observed
"Retry regenerates the previous successful assistant response." For HTTP-level failures (before
`done`), `slice(0, -2)` can even wipe the entire local display.

### No regenerate path exists

- `src/backend/aios/api/chat.py` routes: only `POST /chat/conversation`, `GET /chat/conversations`,
  `GET/PUT/DELETE /chat/conversation/{id}`, `POST /chat/message`, `POST /chat/stream`,
  `GET/DELETE /chat/history/{id}` — **no regenerate route**.
- `src/frontend/src/services/api.ts` (chat helpers at :45-57) — **no regenerate call**.
- Backend `ConversationManager.regenerate_message` (`src/backend/aios/conversation/manager.py:307-368`)
  exists but is unexposed over HTTP and has a different semantic (truncate at target message +
  non-streaming regenerate of the *assistant* message — not a retry of the last user message).

### Exact files/functions for Bug 2

- `src/frontend/src/components/conversation/ConversationView.tsx` → `retryLast` (:279-290),
  `sendMessage` (:91), `done` handler (:196-232).
- `src/frontend/src/components/conversation/ConversationErrorState.tsx` → Retry button wiring
  (`onClick={onRetry}`, via `ConversationTimeline` `onRetry`/`renderError` at ConversationView.tsx:314,322).
- Missing: `/chat/regenerate` API route + `api.ts` helper + backend wiring of `regenerate_message`.

---

## Recommended fixes (proposed — NOT implemented)

Bug 1:
1. **Failover in `route_stream`** — on an exception raised before the first token, fall through to
   the next-ranked eligible candidate instead of re-raising (mirror `_resolve_auto` ordering;
   only give up after all candidates are exhausted). Preserve "no failover after tokens began"
   to avoid duplicate answers.
2. **Fix `StreamManager.stream` retry** — take a *generator factory* (or re-resolve a fresh
   generator per attempt) so each retry actually starts a new stream; or remove the broken
   retry loop and surface the first error.
3. **Health feedback** — call `health_monitor.record_failure(ProviderStatus.ERROR/TIMEOUT, …)` on
   chat/stream failures (404, timeout) so the router stops selecting the broken provider.
4. **Honest errors** — when the provider returned nothing and `had_error`, surface the real
   sanitized error instead of "The provider returned an empty response."; only use the generic
   message when there is genuinely no error info.

Bug 2:
5. **Make Retry actually retry** — have `retryLast` re-invoke `sendMessage(lastUserMsg.content)`
   (and/or wire a new `POST /chat/regenerate` route to the existing backend
   `regenerate_message`). Remove the `slice(0, -2)` state-destruction.

Housekeeping:
6. Mirror every backend change to `desktop/src-tauri/backend/aios/` (byte parity per repo policy).

---

## Evidence references

- Live log: `C:\Users\swara\.eve\logs\backend.log` (lines 21492, 24069, 24103, 24290, 29718, 30355).
- Conversation history: `C:\Users\swara\.eve\conversations\e7e723e206894089b5ab3fe946ed80b1\messages.jsonl`
  (shows the non-tool "what can you do?" also failing, then succeeding after a retry).
- Failing conversations: f4e3f830…, 6d22aa…, 212eeb…, e7e723….
