"""Tests for EventBus."""

import asyncio
import pytest
from aios.core.event_bus import EventBus


@pytest.mark.asyncio
async def test_event_bus_publish_and_subscribe():
    bus = EventBus(max_retries=0, retry_delay=0.001)
    await bus.start()
    received = []
    async def handler(event):
        received.append(event.payload["msg"])
    await bus.subscribe("test:event", handler)
    await bus.publish("test:event", {"msg": "hello"})
    await bus.publish("test:event", {"msg": "world"})
    await asyncio.sleep(0.05)
    await bus.stop()
    assert received == ["hello", "world"]


@pytest.mark.asyncio
async def test_event_bus_wildcard():
    bus = EventBus(max_retries=0, retry_delay=0.001)
    await bus.start()
    received = []
    async def handler(event):
        received.append(event.type)
    await bus.subscribe("*", handler)
    await bus.publish("any:event", {})
    await bus.publish("another:event", {})
    await asyncio.sleep(0.05)
    await bus.stop()
    assert len(received) == 2


@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    bus = EventBus(max_retries=0, retry_delay=0.001)
    await bus.start()
    received = []
    async def handler(event):
        received.append(1)
    sub_id = await bus.subscribe("test:unsub", handler)
    await bus.publish("test:unsub", {})
    await asyncio.sleep(0.05)
    await bus.unsubscribe(sub_id)
    await bus.publish("test:unsub", {})
    await asyncio.sleep(0.05)
    await bus.stop()
    assert len(received) == 1
