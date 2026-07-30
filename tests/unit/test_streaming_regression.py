"""Regression tests for streaming SSE parsing and Google adapter edge cases.

Covers:
- Pretty-printed multi-line Gemini JSON
- Multiple streamed Gemini events
- SSE `data:` prefix handling
- [DONE] sentinel
- Malformed/incomplete JSON
- Empty successful stream
- Provider error during stream
- UTF-8 chunk boundaries
- Braces inside JSON string values (critical brace-depth parser test)
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock
from typing import AsyncIterator

from aios.core.streaming_manager import StreamingManager


# ── Helpers ────────────────────────────────────────────────────────

class FakeResponse:
    """Mock httpx response for SSE line testing."""
    def __init__(self, lines: list[str]):
        self._lines = lines

    async def aiter_lines(self) -> AsyncIterator[str]:
        for line in self._lines:
            yield line


def make_sse_lines(*lines: str) -> list[str]:
    """Wrap raw lines as SSE transport."""
    return list(lines)


async def collect_events(lines: list[str]) -> list[dict]:
    """Run read_sse_lines and collect all yielded dicts."""
    resp = FakeResponse(lines)
    events = []
    async for event in StreamingManager.read_sse_lines(resp):
        events.append(event)
    return events


# ── 1. SSE data: prefix ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sse_data_prefix_stripped():
    lines = make_sse_lines(
        'data: {"candidates":[{"content":{"parts":[{"text":"hello"}]}}]}',
    )
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "hello"


@pytest.mark.asyncio
async def test_sse_multiple_data_prefix_lines():
    lines = make_sse_lines(
        'data: {"candidates":[{"content":{"parts":[{"text":"A"}]}}]}',
        'data: {"candidates":[{"content":{"parts":[{"text":"B"}]}}]}',
    )
    events = await collect_events(lines)
    assert len(events) == 2
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "A"
    assert events[1]["candidates"][0]["content"]["parts"][0]["text"] == "B"


# ── 2. [DONE] sentinel ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_done_sentinel_stops_iteration():
    lines = make_sse_lines(
        'data: {"candidates":[{"content":{"parts":[{"text":"A"}]}}]}',
        'data: [DONE]',
    )
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "A"


@pytest.mark.asyncio
async def test_done_sentinel_only():
    lines = make_sse_lines('data: [DONE]')
    events = await collect_events(lines)
    assert len(events) == 0


# ── 3. Empty lines and comments ────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_lines_skipped():
    lines = make_sse_lines(
        '',
        'data: {"candidates":[{"content":{"parts":[{"text":"hi"}]}}]}',
        '',
    )
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "hi"


@pytest.mark.asyncio
async def test_sse_comment_lines_skipped():
    lines = make_sse_lines(
        ': this is a comment',
        'data: {"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}',
    )
    events = await collect_events(lines)
    assert len(events) == 1


# ── 4. Pretty-printed multi-line Gemini JSON ────────────────────────

@pytest.mark.asyncio
async def test_pretty_printed_gemini_json():
    """Google Gemini streams can emit pretty-printed JSON across multiple lines."""
    lines = make_sse_lines(
        'data: {',
        '  "candidates": [{',
        '    "content": {',
        '      "parts": [{',
        '        "text": "Hello world"',
        '      }]',
        '    }',
        '  }]',
        '}',
    )
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "Hello world"


@pytest.mark.asyncio
async def test_pretty_printed_with_multiple_events():
    lines = make_sse_lines(
        'data: {',
        '  "candidates": [{',
        '    "content": {',
        '      "parts": [{"text": "First"}]',
        '    }',
        '  }]',
        '}',
        'data: {',
        '  "candidates": [{',
        '    "content": {',
        '      "parts": [{"text": "Second"}]',
        '    }',
        '  }]',
        '}',
    )
    events = await collect_events(lines)
    assert len(events) == 2
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "First"
    assert events[1]["candidates"][0]["content"]["parts"][0]["text"] == "Second"


# ── 5. Google array-wrapped responses ───────────────────────────────

@pytest.mark.asyncio
async def test_google_array_wrapped_single():
    lines = make_sse_lines(
        'data: [{"candidates":[{"content":{"parts":[{"text":"arr"}]}}]}]',
    )
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "arr"


@pytest.mark.asyncio
async def test_google_array_wrapped_multiple():
    lines = make_sse_lines(
        'data: [{"candidates":[{"content":{"parts":[{"text":"a"}]}}]}]',
        'data: [{"candidates":[{"content":{"parts":[{"text":"b"}]}}]}]',
    )
    events = await collect_events(lines)
    assert len(events) == 2


# ── 6. Braces inside JSON string values ────────────────────────────

@pytest.mark.asyncio
async def test_braces_in_string_value():
    """CRITICAL: A raw { or } inside a quoted JSON string must NOT change brace depth."""
    payload = json.dumps({
        "candidates": [{
            "content": {
                "parts": [{"text": "Use {example} here and {a}{b} too"}]
            }
        }]
    })
    lines = make_sse_lines(f'data: {payload}')
    events = await collect_events(lines)
    assert len(events) == 1
    text = events[0]["candidates"][0]["content"]["parts"][0]["text"]
    assert text == "Use {example} here and {a}{b} too"


@pytest.mark.asyncio
async def test_braces_in_string_multiline():
    """Pretty-printed JSON with braces in string values."""
    lines = make_sse_lines(
        'data: {',
        '  "candidates": [{',
        '    "content": {',
        '      "parts": [{"text": "Use {example} here"}]',
        '    }',
        '  }]',
        '}',
    )
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "Use {example} here"


@pytest.mark.asyncio
async def test_escaped_quotes_and_braces():
    """Escaped quotes inside string values with braces."""
    payload = json.dumps({"text": 'He said "use {x}" and "}"'})
    lines = make_sse_lines(f'data: {payload}')
    events = await collect_events(lines)
    assert len(events) == 1
    assert "use {x}" in events[0]["text"]


@pytest.mark.asyncio
async def test_deeply_nested_braces_in_string():
    """Braces deeply nested inside string values."""
    text_value = "{{{{nested{{braces}}}}}}"
    payload = json.dumps({"text": text_value})
    lines = make_sse_lines(f'data: {payload}')
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["text"] == "{{{{nested{{braces}}}}}}"


# ── 7. Malformed / incomplete JSON ─────────────────────────────────

@pytest.mark.asyncio
async def test_malformed_json_skipped():
    """Invalid JSON on a line should be skipped without crashing."""
    lines = make_sse_lines(
        'data: {invalid json',
        'data: {"candidates":[{"content":{"parts":[{"text":"ok"}]}}]}',
    )
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "ok"


@pytest.mark.asyncio
async def test_truncated_json_skipped():
    lines = make_sse_lines(
        'data: {"candidates":[{"content":{',
        'data: {"candidates":[{"content":{"parts":[{"text":"fixed"}]}}]}',
    )
    events = await collect_events(lines)
    assert len(events) == 1


# ── 8. Empty stream ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_stream():
    lines = make_sse_lines()
    events = await collect_events(lines)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_only_keepalive_lines():
    lines = make_sse_lines('', '', ': heartbeat', '')
    events = await collect_events(lines)
    assert len(events) == 0


# ── 9. Multiple Gemini streamed events ─────────────────────────────

@pytest.mark.asyncio
async def test_multiple_gemini_streamed_events():
    """Simulate a realistic Gemini streaming session with 5 chunks."""
    chunks = ["Hello", " world", "! This", " is", " Eve."]
    lines = []
    for chunk in chunks:
        payload = json.dumps({
            "candidates": [{"content": {"parts": [{"text": chunk}]}}]
        })
        lines.append(f"data: {payload}")
    lines.append("data: [DONE]")

    events = await collect_events(lines)
    assert len(events) == 5
    full_text = "".join(
        e["candidates"][0]["content"]["parts"][0]["text"] for e in events
    )
    assert full_text == "Hello world! This is Eve."


@pytest.mark.asyncio
async def test_mixed_pretty_and_compact():
    """Mix of compact and pretty-printed JSON events."""
    lines = make_sse_lines(
        'data: {"candidates":[{"content":{"parts":[{"text":"compact"}]}}]}',
        'data: {',
        '  "candidates": [{"content": {"parts": [{"text": "pretty"}]}}]',
        '}',
    )
    events = await collect_events(lines)
    assert len(events) == 2
    assert events[0]["candidates"][0]["content"]["parts"][0]["text"] == "compact"
    assert events[1]["candidates"][0]["content"]["parts"][0]["text"] == "pretty"


# ── 10. Extract helpers ────────────────────────────────────────────

def test_extract_google_chunk():
    chunk = {"candidates": [{"content": {"parts": [{"text": "hi"}]}}]}
    assert StreamingManager.extract_google_chunk(chunk) == "hi"


def test_extract_google_chunk_empty():
    assert StreamingManager.extract_google_chunk({}) == ""
    assert StreamingManager.extract_google_chunk({"candidates": []}) == ""


def test_extract_openai_chunk():
    chunk = {"choices": [{"delta": {"content": "hello"}}]}
    assert StreamingManager.extract_openai_chunk(chunk) == "hello"


def test_extract_openai_chunk_empty():
    assert StreamingManager.extract_openai_chunk({}) == ""
    assert StreamingManager.extract_openai_chunk({"choices": []}) == ""


# ── 11. UTF-8 chunk boundaries ────────────────────────────────────

@pytest.mark.asyncio
async def test_utf8_multibyte_chars():
    """Verify multi-byte UTF-8 characters stream correctly."""
    text = "Hello \u00e9\u00e8\u00ea \u4e16\u754c \U0001f600"
    payload = json.dumps({"text": text})
    lines = make_sse_lines(f'data: {payload}')
    events = await collect_events(lines)
    assert len(events) == 1
    assert events[0]["text"] == text


@pytest.mark.asyncio
async def test_utf8_emoji_in_gemini():
    chunk = json.dumps({
        "candidates": [{"content": {"parts": [{"text": "Great job! \U0001f389"}]}}]
    })
    lines = make_sse_lines(f'data: {chunk}')
    events = await collect_events(lines)
    assert "\U0001f389" in events[0]["candidates"][0]["content"]["parts"][0]["text"]


# ── 12. Provider error during stream ───────────────────────────────

@pytest.mark.asyncio
async def test_error_event_from_streaming_manager():
    """StreamingManager.stream should propagate errors through callbacks."""
    sm = StreamingManager(default_timeout=5.0)

    async def failing_gen():
        raise RuntimeError("Provider failed")
        yield  # make it async generator  # noqa: E501

    errors = []
    try:
        async for token in sm.stream("test-err", failing_gen(), on_error=lambda e: errors.append(e)):
            pass
    except RuntimeError:
        pass  # stream re-raises after calling on_error

    assert len(errors) == 1
    assert "Provider failed" in str(errors[0])


@pytest.mark.asyncio
async def test_empty_stream_no_done():
    """An empty generator should complete without error."""
    sm = StreamingManager(default_timeout=5.0)

    async def empty_gen():
        return
        yield  # noqa: E501

    tokens = []
    async for token in sm.stream("test-empty", empty_gen()):
        tokens.append(token)
    assert len(tokens) == 0


# ── 13. Conversation manager empty-response guard ──────────────────

@pytest.mark.asyncio
async def test_empty_assistant_response_guard():
    """Verify the stream error event is created for empty responses."""
    from aios.conversation.formatter import create_error_event
    event = create_error_event("The provider returned an empty response.", recoverable=True)
    assert event["type"] == "error"
    assert event["data"]["recoverable"] is True
    assert "empty" in event["data"]["error"].lower()


# ── 14. Status service singleton ───────────────────────────────────

def test_status_service_singleton():
    from aios.desktop.status_service import StatusService, AppStatus
    s1 = StatusService()
    s2 = StatusService()
    assert s1 is s2


@pytest.mark.asyncio
async def test_status_transitions():
    from aios.desktop.status_service import StatusService, AppStatus
    svc = StatusService()
    await svc.set_status(AppStatus.READY)
    assert svc.get_status() == AppStatus.READY
    await svc.set_status(AppStatus.THINKING)
    assert svc.get_status() == AppStatus.THINKING
    # Reset for other tests
    await svc.set_status(AppStatus.STARTING)
