"""Stream manager for token-level streaming with cancellation and recovery."""

import asyncio
from typing import AsyncIterator, Callable

from aios.conversation.formatter import (
    create_token_event,
    create_done_event,
    create_error_event,
    create_status_event,
)
from aios.conversation.exceptions import StreamError
from aios.utils.logger import get_logger
from aios.utils.tracer import trace_async_gen

logger = get_logger(__name__)


class StreamManager:
    def __init__(self):
        self._cancelled: dict[str, bool] = {}
        self._active_streams: dict[str, asyncio.Task] = {}

    @trace_async_gen
    async def stream(
        self,
        stream_id: str,
        token_generator: AsyncIterator[str],
        max_retries: int = 2,
        done_metadata: dict | None = None,
    ) -> AsyncIterator[dict]:
        self._cancelled[stream_id] = False
        retries = 0

        try:
            while retries <= max_retries:
                try:
                    async for token in token_generator:
                        if self._cancelled.get(stream_id, False):
                            logger.info("stream.cancelled", stream_id=stream_id)
                            return
                        yield create_token_event(token)

                    yield create_done_event(
                        stream_id,
                        routing_trace=done_metadata.get("routing_trace") if done_metadata else None,
                    )
                    return

                except asyncio.CancelledError:
                    logger.info("stream.cancelled_by_task", stream_id=stream_id)
                    yield create_status_event("cancelled", "Stream cancelled")
                    return

                except Exception as e:
                    retries += 1
                    logger.error("stream.error", stream_id=stream_id, error=str(e), attempt=retries)
                    if retries <= max_retries:
                        yield create_status_event("retrying", f"Retrying... (attempt {retries}/{max_retries})")
                        await asyncio.sleep(retries * 0.5)
                    else:
                        yield create_error_event(str(e), recoverable=False)
                        return
        finally:
            self._cancelled.pop(stream_id, None)
            self._active_streams.pop(stream_id, None)

    def cancel(self, stream_id: str) -> bool:
        if stream_id in self._cancelled:
            self._cancelled[stream_id] = True
            task = self._active_streams.get(stream_id)
            if task and not task.done():
                task.cancel()
            return True
        return False

    def is_active(self, stream_id: str) -> bool:
        return stream_id in self._active_streams and not self._active_streams[stream_id].done()
