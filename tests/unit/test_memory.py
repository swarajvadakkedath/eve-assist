"""Tests for Memory System."""

import pytest
from aios.core.memory_system import MemorySystem, Memory, MemoryType


@pytest.fixture
def mem():
    return MemorySystem()


@pytest.mark.asyncio
async def test_store_and_recall(mem):
    m = Memory(type=MemoryType.FACT, content="Python is a programming language", importance=0.8)
    mid = await mem.store(m)
    recalled = await mem.recall(mid)
    assert recalled is not None
    assert recalled.content == "Python is a programming language"


@pytest.mark.asyncio
async def test_search_memory(mem):
    await mem.store(Memory(type=MemoryType.FACT, content="User likes dark mode", importance=0.6))
    await mem.store(Memory(type=MemoryType.FACT, content="User works with React", importance=0.7))
    results = await mem.search("dark mode")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_forget(mem):
    m = Memory(type=MemoryType.FACT, content="Temporary fact", importance=0.1)
    await mem.store(m)
    await mem.forget(m.id)
    assert await mem.recall(m.id) is None


@pytest.mark.asyncio
async def test_conversation_messages(mem):
    await mem.add_to_conversation("conv1", {"role": "user", "content": "hello"})
    await mem.add_to_conversation("conv1", {"role": "assistant", "content": "hi"})
    msgs = await mem.get_conversation("conv1")
    assert len(msgs) == 2
