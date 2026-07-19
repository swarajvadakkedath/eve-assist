"""Unit tests for the Event Bus."""

import pytest
from aios.core.event_bus import EventBus


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


@pytest.mark.asyncio
async def test_publish_subscribe(event_bus):
    received = []

    async def handler(event):
        received.append(event)

    await event_bus.subscribe("test:event", handler)
    event_id = await event_bus.publish("test:event", {"data": "hello"})

    import asyncio
    await asyncio.sleep(0.1)

    assert len(received) == 1
    assert received[0].type == "test:event"
    assert received[0].payload["data"] == "hello"


@pytest.mark.asyncio
async def test_unsubscribe(event_bus):
    received = []

    async def handler(event):
        received.append(event)

    sub_id = await event_bus.subscribe("test:unsub", handler)
    await event_bus.unsubscribe(sub_id)
    await event_bus.publish("test:unsub", {})

    import asyncio
    await asyncio.sleep(0.1)

    assert len(received) == 0


@pytest.mark.asyncio
async def test_event_history(event_bus):
    await event_bus.publish("test:history", {"n": 1})
    await event_bus.publish("test:history", {"n": 2})

    history = await event_bus.get_history("test:history")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_wildcard_subscriber(event_bus):
    received = []

    async def handler(event):
        received.append(event)

    await event_bus.subscribe("*", handler)
    await event_bus.publish("test:wildcard", {})

    import asyncio
    await asyncio.sleep(0.1)

    assert len(received) == 1
