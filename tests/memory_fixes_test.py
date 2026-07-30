"""Memory system fixes test."""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "desktop", "src-tauri", "backend"))

from aios.core.memory_system import MemorySystem, Memory, MemoryType
from aios.core.event_bus import EventBus


async def test_memory_fixes():
    print("=== Memory System Fixes Test ===\n")
    
    event_bus = EventBus()
    await event_bus.start()
    
    persistence_path = os.path.join(os.path.dirname(__file__), "test_memory.json")
    memory = MemorySystem(event_bus=event_bus, persistence_path=persistence_path)
    
    print("--- Phase 3: Candidate Detection ---")
    try:
        await memory.store(Memory(type=MemoryType.FACT, content="Open Calculator", source="test", importance=0.3))
        print("FAIL: Should have rejected non-candidate")
    except ValueError as e:
        print(f"PASS: Rejected non-candidate: {e}")
    
    try:
        await memory.store(Memory(type=MemoryType.FACT, content="Remember that my preferred editor is VS Code", source="test", importance=0.5))
        print("PASS: Stored candidate with 'remember' keyword")
    except ValueError as e:
        print(f"FAIL: Rejected valid candidate: {e}")
    
    print("\n--- Phase 9: Conflict Resolution ---")
    await memory.store(Memory(type=MemoryType.PREFERENCE, content="My preferred editor is VS Code", source="test", importance=0.7))
    results = await memory.search("editor")
    print(f"After storing VS Code: {len(results)} results")
    
    await memory.store(Memory(type=MemoryType.PREFERENCE, content="My preferred editor is Cursor", source="test", importance=0.9))
    results = await memory.search("editor")
    print(f"After storing Cursor: {len(results)} results (should be 1)")
    for r in results:
        print(f"  - {r.content[:80]}")
    
    print("\n--- Phase 10: Deduplication ---")
    await memory.store(Memory(type=MemoryType.PREFERENCE, content="My preferred editor is Cursor", source="test", importance=0.9))
    await memory.store(Memory(type=MemoryType.PREFERENCE, content="My preferred editor is Cursor", source="test", importance=0.9))
    results = await memory.search("Cursor")
    print(f"After storing Cursor 3 times: {len(results)} results (should be 1)")
    
    print("\n--- Phase 13: Sensitive Data Protection ---")
    try:
        await memory.store(Memory(type=MemoryType.FACT, content="My API key is sk-1234567890abcdef", source="test", importance=0.5))
        print("FAIL: Should have blocked sensitive data")
    except ValueError as e:
        print(f"PASS: Blocked sensitive data: {e}")
    
    try:
        await memory.store(Memory(type=MemoryType.FACT, content="Password: MySecretPass123!", source="test", importance=0.5))
        print("FAIL: Should have blocked sensitive data")
    except ValueError as e:
        print(f"PASS: Blocked sensitive data: {e}")
    
    print("\n--- Phase 6: Persistence ---")
    await memory.store(Memory(type=MemoryType.FACT, content="Remember that my test codename is Orion", source="test", importance=0.8))
    saved = await memory.save()
    print(f"Save result: {saved}")
    print(f"File exists: {os.path.exists(persistence_path)}")
    
    memory2 = MemorySystem(event_bus=event_bus, persistence_path=persistence_path)
    loaded = await memory2.load()
    print(f"Load result: {loaded}")
    results = await memory2.search("Orion")
    print(f"Search 'Orion' after load: {len(results)} results")
    for r in results:
        print(f"  - {r.content[:80]}")
    
    print("\n--- Phase 17: Performance ---")
    start = time.monotonic()
    for i in range(100):
        await memory.store(Memory(type=MemoryType.FACT, content=f"Performance test memory {i}", source="test", importance=0.5), force=True)
    elapsed = (time.monotonic() - start) * 1000
    print(f"100 writes: {elapsed:.1f}ms ({elapsed/100:.2f}ms per write)")
    
    start = time.monotonic()
    for i in range(100):
        await memory.search(f"Performance test memory {i}")
    elapsed = (time.monotonic() - start) * 1000
    print(f"100 searches: {elapsed:.1f}ms ({elapsed/100:.2f}ms per search)")
    
    stats = await memory.stats()
    print(f"\nTotal nodes: {stats.totalNodes}")
    
    await event_bus.stop()
    
    if os.path.exists(persistence_path):
        os.remove(persistence_path)
    
    print("\n=== ALL TESTS COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(test_memory_fixes())
