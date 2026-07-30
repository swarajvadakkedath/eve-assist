"""Memory system comprehensive test."""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "desktop", "src-tauri", "backend"))

from aios.core.memory_system import MemorySystem, Memory, MemoryType
from aios.core.event_bus import EventBus


async def test_memory_system():
    print("=== Memory System Test ===\n")
    
    event_bus = EventBus()
    await event_bus.start()
    
    memory = MemorySystem(event_bus=event_bus)
    
    print("--- Phase 4: Explicit Memory ---")
    mem_id = await memory.store(Memory(
        type=MemoryType.FACT,
        content="My temporary test codename is Orion",
        source="test",
        importance=0.8,
    ))
    print(f"Stored memory ID: {mem_id}")
    
    results = await memory.search("codename")
    print(f"Search 'codename': {len(results)} results")
    for r in results:
        print(f"  - {r.content[:80]}")
    
    print("\n--- Phase 5: Cross-conversation ---")
    results2 = await memory.search("Orion")
    print(f"Search 'Orion': {len(results2)} results")
    for r in results2:
        print(f"  - {r.content[:80]}")
    
    print("\n--- Phase 7: Relevance ---")
    await memory.store(Memory(type=MemoryType.PREFERENCE, content="I prefer VS Code as my editor", source="test", importance=0.7))
    await memory.store(Memory(type=MemoryType.FACT, content="My favorite test theme is dark", source="test", importance=0.5))
    await memory.store(Memory(type=MemoryType.FACT, content="Sandbox project uses SQLite database", source="test", importance=0.6))
    
    results = await memory.search("editor")
    print(f"Search 'editor': {len(results)} results")
    for r in results:
        print(f"  - {r.content[:80]}")
    
    print("\n--- Phase 9: Conflicts ---")
    await memory.store(Memory(type=MemoryType.PREFERENCE, content="My preferred editor is Cursor now", source="test", importance=0.9))
    
    results = await memory.search("editor")
    print(f"Search 'editor' after update: {len(results)} results")
    for r in results:
        print(f"  - {r.content[:80]}")
    
    print("\n--- Phase 10: Duplicates ---")
    await memory.store(Memory(type=MemoryType.PREFERENCE, content="My preferred editor is Cursor", source="test", importance=0.9))
    await memory.store(Memory(type=MemoryType.PREFERENCE, content="My preferred editor is Cursor", source="test", importance=0.9))
    
    results = await memory.search("Cursor")
    print(f"Search 'Cursor': {len(results)} results (should be 1 if deduped, 3 if not)")
    
    print("\n--- Phase 11: Forgetting ---")
    await memory.forget(mem_id)
    results = await memory.search("Orion")
    print(f"Search 'Orion' after forget: {len(results)} results")
    
    print("\n--- Phase 13: Sensitive Information ---")
    await memory.store(Memory(type=MemoryType.FACT, content="My API key is sk-1234567890abcdef", source="test", importance=0.5))
    await memory.store(Memory(type=MemoryType.FACT, content="Password: MySecretPass123!", source="test", importance=0.5))
    
    results = await memory.search("API key")
    print(f"Search 'API key': {len(results)} results")
    for r in results:
        print(f"  - {r.content[:80]}")
    
    print("\n--- Phase 17: Performance ---")
    start = time.monotonic()
    for i in range(100):
        await memory.store(Memory(type=MemoryType.FACT, content=f"Test memory number {i}", source="test", importance=0.5))
    elapsed = (time.monotonic() - start) * 1000
    print(f"100 writes: {elapsed:.1f}ms ({elapsed/100:.2f}ms per write)")
    
    start = time.monotonic()
    for i in range(100):
        await memory.search(f"memory number {i}")
    elapsed = (time.monotonic() - start) * 1000
    print(f"100 searches: {elapsed:.1f}ms ({elapsed/100:.2f}ms per search)")
    
    stats = await memory.stats()
    print(f"\nTotal nodes: {stats.totalNodes}")
    print(f"Total edges: {stats.totalEdges}")
    
    await event_bus.stop()


if __name__ == "__main__":
    asyncio.run(test_memory_system())
