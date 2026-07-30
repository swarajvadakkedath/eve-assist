"""Event Bus — decoupled async communication backbone."""

import asyncio
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from aios.models.events import Event, Subscription


class EventBus:
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self._subscriptions: dict[str, list[Subscription]] = {}
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._history: list[Event] = []
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._worker_task: asyncio.Task | None = None

    async def start(self):
        self._running = True
        self._worker_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def publish(
        self,
        event_type: str,
        payload: dict,
        source: str = "",
        correlation_id: str = "",
        priority: int = 0,
    ) -> str:
        event = Event(
            id=uuid4().hex,
            type=event_type,
            source=source,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
            correlation_id=correlation_id or uuid4().hex,
            priority=priority,
        )
        self._history.append(event)
        if len(self._history) > 10000:
            self._history = self._history[-5000:]
        await self._queue.put(event)
        return event.id

    async def subscribe(self, event_type: str, handler: Callable) -> str:
        sub_id = uuid4().hex
        sub = Subscription(id=sub_id, event_type=event_type, handler=handler)
        self._subscriptions.setdefault(event_type, []).append(sub)
        return sub_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        for event_type, subs in self._subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subs.remove(sub)
                    return True
        return False

    async def get_history(self, event_type: str | None = None, limit: int = 100) -> list[Event]:
        if event_type:
            return [e for e in self._history if e.type == event_type][-limit:]
        return self._history[-limit:]

    async def _dispatch_loop(self):
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._dispatch(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.publish("error:occurred", {
                    "module": "event_bus",
                    "error": str(e),
                })

    async def _dispatch(self, event: Event):
        subs = list(self._subscriptions.get(event.type, []))
        if not subs:
            subs = list(self._subscriptions.get("*", []))
        if not subs:
            for event_type, candidates in self._subscriptions.items():
                if event_type.endswith(".*") and event.type.startswith(event_type[:-1]):
                    subs.extend(candidates)

        tasks = []
        for sub in subs:
            tasks.append(self._deliver(sub, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _deliver(self, subscription: Subscription, event: Event):
        for attempt in range(self._max_retries + 1):
            try:
                result = subscription.handler(event)
                if hasattr(result, "__await__"):
                    await result
                return
            except Exception as e:
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay * (2 ** attempt))
                    event.retry_count += 1
                else:
                    await self.publish("error:occurred", {
                        "module": "event_bus",
                        "error": str(e),
                        "event_type": event.type,
                        "subscription": subscription.id,
                    })
