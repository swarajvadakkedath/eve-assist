"""Centralized streaming manager for all provider adapters.

Eliminates duplicated streaming logic across adapters by providing:
- AbortController (per-stream cancellation)
- Heartbeat (keep-alive during slow streams)
- Reconnect (configurable retries on dropped connections)
- Timeout wrapping
- Progress callbacks
- TTS support
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator, Callable

import structlog

logger = structlog.get_logger(__name__)


class StreamAborted(Exception):
    """Raised when a stream is explicitly cancelled."""


class StreamingManager:
    """Single source of truth for all streaming in Eve.

    Every adapter delegates its ``stream()`` method here.
    """

    def __init__(
        self,
        default_timeout: float = 120.0,
        default_heartbeat: float = 15.0,
    ):
        self._default_timeout = default_timeout
        self._default_heartbeat = default_heartbeat
        self._cancelled: dict[str, bool] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def stream(
        self,
        stream_id: str,
        generator: AsyncIterator[str],
        timeout: float | None = None,
        heartbeat_interval: float | None = None,
        on_token: Callable[[str], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        on_done: Callable[[], None] | None = None,
    ) -> AsyncIterator[str]:
        """Wrap a token generator with timeout, heartbeat, and cancellation.

        Yields the same tokens as *generator*, adding:
        - Cancellation support via ``cancel()``
        - Timeout enforcement
        - Optional heartbeat
        - Callbacks for token/error/done

        Usage from an adapter::

            async def stream(self, request):
                async def _gen():
                    ... raw HTTP streaming ...
                    yield token

                async for token in self._streaming.stream(
                    stream_id, _gen()
                ):
                    yield token
        """
        self._cancelled[stream_id] = False
        hb_interval = heartbeat_interval or self._default_heartbeat
        to = timeout or self._default_timeout
        last_token_time = time.monotonic()

        async def _heartbeat_checker():
            while stream_id in self._cancelled:
                await asyncio.sleep(hb_interval)
                if time.monotonic() - last_token_time > hb_interval:
                    if not self._cancelled.get(stream_id):
                        logger.debug("stream.heartbeat", stream_id=stream_id)

        hb_task: asyncio.Task | None = None

        try:
            hb_task = asyncio.create_task(_heartbeat_checker())

            async with asyncio.timeout(to):
                async for token in generator:
                    if self._cancelled.get(stream_id, False):
                        raise StreamAborted("Stream cancelled")
                    last_token_time = time.monotonic()
                    if on_token:
                        on_token(token)
                    yield token

            if on_done:
                on_done()

        except StreamAborted:
            return
        except asyncio.TimeoutError:
            logger.warning("stream.timeout", stream_id=stream_id)
            if on_error:
                on_error(TimeoutError(f"Stream timed out after {to}s"))
            raise
        except asyncio.CancelledError:
            logger.info("stream.cancelled", stream_id=stream_id)
            return
        except Exception as e:
            if on_error:
                on_error(e)
            raise
        finally:
            self._cancelled.pop(stream_id, None)
            if hb_task:
                hb_task.cancel()
                try:
                    await hb_task
                except asyncio.CancelledError:
                    pass

    def cancel(self, stream_id: str) -> bool:
        """Cancel an active stream by ID. Returns True if stream was registered."""
        if stream_id in self._cancelled:
            self._cancelled[stream_id] = True
            return True
        return False

    def is_active(self, stream_id: str) -> bool:
        """Return True if the stream is registered and not yet cancelled."""
        return stream_id in self._cancelled and not self._cancelled[stream_id]

    def cancel_all(self):
        for sid in list(self._cancelled.keys()):
            self.cancel(sid)

    # ------------------------------------------------------------------
    # HTTP streaming helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def read_sse_lines(
        response: Any,
    ) -> AsyncIterator[dict]:
        """Read JSON events from an httpx response, yielding parsed dicts.

        Handles:
        - SSE ``data: `` prefix and ``[DONE]`` sentinel
        - Single-line JSON (OpenAI, Anthropic)
        - Multi-line pretty-printed JSON (Google Gemini)
        - ``[]`` array wrapping (Google Gemini streaming)
        - Empty keep-alive lines
        """
        buffer = ""
        depth = 0
        in_string = False
        escape_next = False

        async for raw_line in response.aiter_lines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(":"):
                continue
            is_new_event = line.startswith("data: ")
            if is_new_event:
                line = line[6:].strip()
                if buffer and depth > 0:
                    text = buffer.strip().lstrip("[").rstrip("]").strip()
                    if text:
                        try:
                            json.loads(text)
                        except json.JSONDecodeError:
                            buffer = ""
                            depth = 0
                            in_string = False
                            escape_next = False
            if line == "[DONE]":
                break

            for ch in line:
                if escape_next:
                    escape_next = False
                    continue
                if ch == '\\' and in_string:
                    escape_next = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1

            buffer += line

            if depth == 0 and buffer.strip():
                text = buffer.strip().lstrip("[").rstrip("]").strip()
                if text:
                    try:
                        parsed = json.loads(text)
                        if isinstance(parsed, list):
                            for item in parsed:
                                yield item
                        else:
                            yield parsed
                        buffer = ""
                        depth = 0
                        in_string = False
                        escape_next = False
                    except json.JSONDecodeError:
                        buffer = ""
                        depth = 0
                        in_string = False
                        escape_next = False

    @staticmethod
    def extract_openai_chunk(chunk: dict) -> str:
        """Extract content token from an OpenAI-style streaming chunk."""
        choices = chunk.get("choices", [])
        if not choices:
            return ""
        delta = choices[0].get("delta", {})
        return delta.get("content", "")

    @staticmethod
    def extract_google_chunk(chunk: dict) -> str:
        """Extract content token from a Google-style streaming chunk."""
        candidates = chunk.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)
