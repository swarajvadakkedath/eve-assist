"""Memory capability registration for CapabilityRegistry."""

from aios.core.capability_registry import CapabilityRegistry, Capability


async def register_memory_capabilities(registry: CapabilityRegistry):
    caps = [
        Capability(
            id="memory.store",
            name="Store Memory",
            description="Store a new memory node in the graph",
            provider_type="system",
            provider_id="memory_system",
            permission_level=1,
            tags=["memory", "store", "write"],
            version="1.1.0",
            quality=1.0,
        ),
        Capability(
            id="memory.search",
            name="Search Memories",
            description="Search memories by keyword or structured query",
            provider_type="system",
            provider_id="memory_system",
            permission_level=0,
            tags=["memory", "search", "read"],
            version="1.1.0",
            quality=1.0,
        ),
        Capability(
            id="memory.recall",
            name="Recall Memory",
            description="Retrieve a specific memory by ID",
            provider_type="system",
            provider_id="memory_system",
            permission_level=0,
            tags=["memory", "recall", "read"],
            version="1.1.0",
            quality=1.0,
        ),
        Capability(
            id="memory.forget",
            name="Forget Memory",
            description="Delete a memory from the graph",
            provider_type="system",
            provider_id="memory_system",
            permission_level=2,
            tags=["memory", "forget", "delete"],
            version="1.1.0",
            quality=1.0,
        ),
        Capability(
            id="memory.traverse",
            name="Traverse Memory Graph",
            description="BFS/DFS traversal of the memory graph from a seed node",
            provider_type="system",
            provider_id="memory_system",
            permission_level=0,
            tags=["memory", "traverse", "graph", "read"],
            version="1.1.0",
            quality=1.0,
        ),
        Capability(
            id="memory.stats",
            name="Memory Statistics",
            description="Get statistics about the memory graph",
            provider_type="system",
            provider_id="memory_system",
            permission_level=0,
            tags=["memory", "stats", "read"],
            version="1.1.0",
            quality=1.0,
        ),
    ]
    for cap in caps:
        await registry.register_capability(cap)
