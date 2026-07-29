"""Comprehensive tests for Memory Core (graph-based memory system)."""

import pytest
from aios.core.memory_system import MemorySystem, Memory, MemoryType
from aios.models.memory import (
    NodeId,
    EdgeId,
    NodeInput,
    EdgeInput,
    SearchQuery,
    SearchFilters,
    QueryOptions,
    NodeTypeDefinition,
    EdgeTypeDefinition,
)
from aios.core.memory.graph import MemoryGraph
from aios.core.memory.traversal import GraphTraversal
from aios.core.memory.registry import (
    NodeTypeRegistry,
    EdgeTypeRegistry,
    MemoryRegistry,
    get_memory_registry,
    reset_memory_registry,
)
from aios.core.memory.query import QueryParser
from aios.core.memory.events import MemoryEventBus
from aios.core.memory.store import MemoryStore, reset_memory_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_node_id(value="n1", type_str="custom") -> NodeId:
    return NodeId(value=value, type=type_str)


def make_edge_id(value="e1") -> EdgeId:
    return EdgeId(value=value)


# ---------------------------------------------------------------------------
# MemorySystem backward-compatible API tests
# ---------------------------------------------------------------------------

@pytest.fixture
def mem():
    reset_memory_store()
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
    assert "dark mode" in results[0].content.lower()


@pytest.mark.asyncio
async def test_forget(mem):
    m = Memory(type=MemoryType.FACT, content="Temporary fact", importance=0.1)
    mid = await mem.store(m)
    await mem.forget(mid)
    assert await mem.recall(mid) is None


@pytest.mark.asyncio
async def test_conversation_messages(mem):
    await mem.add_to_conversation("conv1", {"role": "user", "content": "hello"})
    await mem.add_to_conversation("conv1", {"role": "assistant", "content": "hi"})
    msgs = await mem.get_conversation("conv1")
    assert len(msgs) == 2


@pytest.mark.asyncio
async def test_search_returns_multiple(mem):
    await mem.store(Memory(type=MemoryType.LEARNING, content="First learning", importance=0.5))
    await mem.store(Memory(type=MemoryType.LEARNING, content="Second learning", importance=0.9))
    results = await mem.search("learning")
    assert len(results) == 2


# ---------------------------------------------------------------------------
# MemoryGraph unit tests
# ---------------------------------------------------------------------------

class TestMemoryGraph:
    def test_add_node(self):
        g = MemoryGraph()
        node = g.add_node(NodeInput(type="test_type", subtype="sub", title="Test Node", source="test"))
        assert node.id.value
        assert node.type == "test_type"
        assert node.title == "Test Node"
        assert node.createdAt > 0
        assert g.node_count() == 1

    def test_add_node_with_custom_id(self):
        g = MemoryGraph()
        node = g.add_node(NodeInput(id="my_id", type="test", subtype="", title="Custom", source="test"))
        assert node.id.value == "my_id"

    def test_update_node(self):
        g = MemoryGraph()
        node = g.add_node(NodeInput(type="test", subtype="", title="Original", source="test"))
        updated = g.update_node(node.id, {"title": "Updated"})
        assert updated is not None
        assert updated.title == "Updated"

    def test_update_nonexistent(self):
        g = MemoryGraph()
        result = g.update_node(NodeId(value="nope", type="x"), {"title": "nope"})
        assert result is None

    def test_delete_node(self):
        g = MemoryGraph()
        node = g.add_node(NodeInput(type="test", subtype="", title="To Delete", source="test"))
        assert g.delete_node(node.id) is True
        assert g.node_count() == 0

    def test_delete_nonexistent(self):
        g = MemoryGraph()
        assert g.delete_node(make_node_id()) is False

    def test_get_node(self):
        g = MemoryGraph()
        node = g.add_node(NodeInput(type="test", subtype="", title="Get Me", source="test"))
        fetched = g.get_node(node.id)
        assert fetched is not None
        assert fetched.id.value == node.id.value

    def test_get_node_by_id(self):
        g = MemoryGraph()
        node = g.add_node(NodeInput(type="test", subtype="", title="By ID", source="test"))
        fetched = g.get_node_by_id(node.id)
        assert fetched is not None

    def test_get_nodes_by_type(self):
        g = MemoryGraph()
        g.add_node(NodeInput(type="fruit", subtype="", title="Apple", source="test"))
        g.add_node(NodeInput(type="fruit", subtype="", title="Banana", source="test"))
        g.add_node(NodeInput(type="veg", subtype="", title="Carrot", source="test"))
        assert len(g.get_nodes_by_type("fruit")) == 2
        assert len(g.get_nodes_by_type("veg")) == 1

    def test_get_nodes_by_super_type(self):
        g = MemoryGraph()
        g.add_node(NodeInput(type="knowledge:statement", subtype="", title="K1", source="test"))
        g.add_node(NodeInput(type="knowledge:summary", subtype="", title="K2", source="test"))
        g.add_node(NodeInput(type="entity:person", subtype="", title="P1", source="test"))
        assert len(g.get_nodes_by_super_type("knowledge")) == 2

    def test_archive_restore(self):
        g = MemoryGraph()
        node = g.add_node(NodeInput(type="test", subtype="", title="Archivable", source="test"))
        archived = g.archive_node(node.id)
        assert archived is not None
        assert archived.archived is True
        assert archived.status == "archived"
        restored = g.restore_node(node.id)
        assert restored is not None
        assert restored.archived is False
        assert restored.status == "active"

    def test_stats(self):
        g = MemoryGraph()
        assert g.stats().totalNodes == 0
        g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        g.add_node(NodeInput(type="b", subtype="", title="B", source="test"))
        stats = g.stats()
        assert stats.totalNodes == 2
        assert stats.totalEdges == 0


# ---------------------------------------------------------------------------
# MemoryGraph edge tests
# ---------------------------------------------------------------------------

class TestMemoryGraphEdges:
    def test_add_edge(self):
        g = MemoryGraph()
        n1 = g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        n2 = g.add_node(NodeInput(type="b", subtype="", title="B", source="test"))
        edge = g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        assert edge is not None
        assert edge.type == "related_to"
        assert g.edge_count() == 1

    def test_add_edge_missing_node(self):
        g = MemoryGraph()
        n1 = g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        edge = g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=make_node_id("missing"), type="related_to"))
        assert edge is None

    def test_delete_edge(self):
        g = MemoryGraph()
        n1 = g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        n2 = g.add_node(NodeInput(type="b", subtype="", title="B", source="test"))
        e = g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        assert g.delete_edge(e.id) is True
        assert g.edge_count() == 0

    def test_get_edges_by_node(self):
        g = MemoryGraph()
        n1 = g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        n2 = g.add_node(NodeInput(type="b", subtype="", title="B", source="test"))
        n3 = g.add_node(NodeInput(type="c", subtype="", title="C", source="test"))
        g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n3.id, type="contains"))
        assert len(g.get_edges_by_node(n1.id)) == 2
        assert len(g.get_edges_by_node(n2.id)) == 1

    def test_delete_node_cascades_edges(self):
        g = MemoryGraph()
        n1 = g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        n2 = g.add_node(NodeInput(type="b", subtype="", title="B", source="test"))
        g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        g.delete_node(n1.id)
        assert g.edge_count() == 0

    def test_neighbors(self):
        g = MemoryGraph()
        n1 = g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        n2 = g.add_node(NodeInput(type="b", subtype="", title="B", source="test"))
        n3 = g.add_node(NodeInput(type="c", subtype="", title="C", source="test"))
        g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n3.id, type="related_to"))
        assert len(g.get_neighbors(n1.id)) == 2


# ---------------------------------------------------------------------------
# Snapshot tests
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_snapshot_roundtrip(self):
        g = MemoryGraph()
        n1 = g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        n2 = g.add_node(NodeInput(type="b", subtype="", title="B", source="test"))
        g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        snap = g.snapshot()
        assert len(snap.nodes) == 2
        assert len(snap.edges) == 1
        g2 = MemoryGraph()
        g2.load_snapshot(snap)
        assert g2.node_count() == 2
        assert g2.edge_count() == 1

    def test_clear(self):
        g = MemoryGraph()
        g.add_node(NodeInput(type="a", subtype="", title="A", source="test"))
        g.clear()
        assert g.node_count() == 0
        assert g.edge_count() == 0


# ---------------------------------------------------------------------------
# GraphTraversal tests
# ---------------------------------------------------------------------------

class TestGraphTraversal:
    @pytest.fixture
    def graph_with_chain(self):
        g = MemoryGraph()
        n1 = g.add_node(NodeInput(type="a", subtype="", title="Node1", source="test"))
        n2 = g.add_node(NodeInput(type="b", subtype="", title="Node2", source="test"))
        n3 = g.add_node(NodeInput(type="c", subtype="", title="Node3", source="test"))
        n4 = g.add_node(NodeInput(type="d", subtype="", title="Node4", source="test"))
        g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        g.add_edge(EdgeInput(sourceNodeId=n2.id, targetNodeId=n3.id, type="contains"))
        g.add_edge(EdgeInput(sourceNodeId=n3.id, targetNodeId=n4.id, type="produces"))
        return g

    def test_bfs(self, graph_with_chain):
        g = graph_with_chain
        nodes = g.get_all_nodes()
        t = GraphTraversal(g)
        start = nodes[0]
        result = t.bfs(start.id, max_depth=10)
        assert len(result.nodes) == 4
        assert len(result.edges) == 3

    def test_bfs_with_depth_limit(self, graph_with_chain):
        g = graph_with_chain
        t = GraphTraversal(g)
        start = g.get_all_nodes()[0]
        result = t.bfs(start.id, max_depth=1)
        assert len(result.nodes) == 2

    def test_dfs(self, graph_with_chain):
        g = graph_with_chain
        t = GraphTraversal(g)
        start = g.get_all_nodes()[0]
        result = t.dfs(start.id, max_depth=10)
        assert len(result.nodes) == 4

    def test_bfs_nonexistent(self):
        g = MemoryGraph()
        t = GraphTraversal(g)
        result = t.bfs(make_node_id("ghost"), max_depth=5)
        assert len(result.nodes) == 0

    def test_find_paths(self, graph_with_chain):
        g = graph_with_chain
        t = GraphTraversal(g)
        nodes = g.get_all_nodes()
        paths = t.find_paths(nodes[0].id, nodes[3].id)
        assert len(paths) >= 1

    def test_find_shortest_path(self, graph_with_chain):
        g = graph_with_chain
        t = GraphTraversal(g)
        nodes = g.get_all_nodes()
        path = t.find_shortest_path(nodes[0].id, nodes[3].id)
        assert path is not None
        assert path.depth == 3

    def test_connected_component(self, graph_with_chain):
        g = graph_with_chain
        t = GraphTraversal(g)
        result = t.get_connected_component(g.get_all_nodes()[0].id)
        assert len(result.nodes) == 4


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

class TestNodeTypeRegistry:
    def test_register_and_get(self):
        r = NodeTypeRegistry()
        r.register(NodeTypeDefinition(name="test_type", superType="entity"))
        assert r.has("test_type")
        defn = r.get("test_type")
        assert defn is not None
        assert defn.superType == "entity"

    def test_register_duplicate(self):
        r = NodeTypeRegistry()
        r.register(NodeTypeDefinition(name="dup", superType="entity"))
        r.register(NodeTypeDefinition(name="dup", superType="action"))
        assert r.count() == 1

    def test_get_all(self):
        r = NodeTypeRegistry()
        r.register(NodeTypeDefinition(name="a", superType="entity"))
        r.register(NodeTypeDefinition(name="b", superType="action"))
        assert len(r.get_all()) == 2

    def test_is_valid_node_type(self):
        r = NodeTypeRegistry()
        r.register(NodeTypeDefinition(name="valid", superType="entity"))
        assert r.is_valid_node_type("valid") is True
        assert r.is_valid_node_type("invalid") is False

    def test_get_by_super_type(self):
        r = NodeTypeRegistry()
        r.register(NodeTypeDefinition(name="p1", superType="entity"))
        r.register(NodeTypeDefinition(name="p2", superType="entity"))
        r.register(NodeTypeDefinition(name="a1", superType="action"))
        assert len(r.get_by_super_type("entity")) == 2
        assert len(r.get_by_super_type("action")) == 1

    def test_clear(self):
        r = NodeTypeRegistry()
        r.register(NodeTypeDefinition(name="x", superType="entity"))
        r.clear()
        assert r.count() == 0


class TestEdgeTypeRegistry:
    def test_register_and_get(self):
        r = EdgeTypeRegistry()
        r.register(EdgeTypeDefinition(name="related_to", allowedSourceTypes=[], allowedTargetTypes=[]))
        assert r.has("related_to")

    def test_can_connect(self):
        r = EdgeTypeRegistry()
        r.register(EdgeTypeDefinition(
            name="contains",
            allowedSourceTypes=["folder"],
            allowedTargetTypes=["file"],
            directional=True,
        ))
        assert r.can_connect("folder", "contains", "file") is True
        assert r.can_connect("file", "contains", "folder") is False

    def test_missing_type(self):
        r = EdgeTypeRegistry()
        assert r.can_connect("any", "missing", "any") is False


class TestMemoryRegistry:
    def test_load_defaults(self):
        r = MemoryRegistry()
        r.load_defaults()
        assert r.nodeTypes.count() > 0
        assert r.edgeTypes.count() > 0

    def test_clear(self):
        r = MemoryRegistry()
        r.load_defaults()
        r.clear()
        assert r.nodeTypes.count() == 0

    def test_singleton(self):
        reset_memory_registry()
        r1 = get_memory_registry()
        r2 = get_memory_registry()
        assert r1 is r2
        reset_memory_registry()


# ---------------------------------------------------------------------------
# QueryEngine tests
# ---------------------------------------------------------------------------

class TestQueryEngine:
    @pytest.fixture
    def engine(self):
        from aios.core.memory.store import reset_memory_store
        reset_memory_store()
        store = MemoryStore()
        store.graph.add_node(NodeInput(type="knowledge", subtype="statement", title="Python rules", summary="Python is great", source="user", tags=["python", "lang"]))
        store.graph.add_node(NodeInput(type="preference", subtype="theme", title="Dark mode", summary="User likes dark mode", source="user", tags=["theme", "dark"]))
        store.graph.add_node(NodeInput(type="knowledge", subtype="fact", title="Sky is blue", summary="The sky appears blue", source="observation", tags=["science"]))
        return store

    def test_keyword_search(self, engine):
        result = engine.search_by_keyword("Python")
        assert len(result.nodes) >= 1
        assert "Python" in result.nodes[0].title

    def test_keyword_empty(self, engine):
        result = engine.search_by_keyword("")
        assert len(result.nodes) == 0

    def test_find_all(self, engine):
        result = engine.find_all()
        assert result.total == 3

    def test_find_by_type(self, engine):
        result = engine.find_by_type("knowledge")
        assert len(result.nodes) >= 1

    def test_find_by_super_type(self, engine):
        result = engine.find_by_super_type("knowledge")
        assert len(result.nodes) >= 1

    def test_filter_by_tag(self, engine):
        query = SearchQuery(filters=SearchFilters(tags=["python"]))
        result = engine.search(query)
        assert len(result.nodes) >= 1
        assert "python" in result.nodes[0].tags

    def test_sort_by_title_asc(self, engine):
        query = SearchQuery(options=QueryOptions(sortField="title", sortOrder="asc"))
        result = engine.search(query)
        titles = [n.title for n in result.nodes]
        assert titles == sorted(titles)

    def test_pagination(self, engine):
        query = SearchQuery(options=QueryOptions(limit=2, offset=0))
        result = engine.search(query)
        assert len(result.nodes) == 2


# ---------------------------------------------------------------------------
# MemoryEventBus tests
# ---------------------------------------------------------------------------

class TestMemoryEventBus:
    def test_publish_subscribe(self):
        bus = MemoryEventBus()
        received = []
        unsub = bus.subscribe("node:created", lambda e: received.append(e))
        bus.publish("node:created", {"id": "123"})
        assert len(received) == 1
        assert received[0]["payload"]["id"] == "123"
        unsub()
        bus.publish("node:created", {"id": "456"})
        assert len(received) == 1

    def test_wildcard(self):
        bus = MemoryEventBus()
        received = []
        bus.subscribe("*", lambda e: received.append(e["type"]))
        bus.publish("node:created", {})
        bus.publish("edge:deleted", {})
        assert len(received) == 2

    def test_history(self):
        bus = MemoryEventBus(history_limit=5)
        for i in range(10):
            bus.publish("test", {"i": i})
        assert len(bus.get_history()) == 5

    def test_filtered_subscription(self):
        bus = MemoryEventBus()
        received = []
        bus.subscribe("node:created", lambda e: received.append(e), event_filter=lambda e: e["payload"].get("type") == "important")
        bus.publish("node:created", {"type": "normal"})
        bus.publish("node:created", {"type": "important"})
        assert len(received) == 1

    def test_on_any(self):
        bus = MemoryEventBus()
        received = []
        bus.on_any(lambda e: received.append(e["type"]))
        bus.publish("a", {})
        assert received == ["a"]


# ---------------------------------------------------------------------------
# MemoryValidation tests
# ---------------------------------------------------------------------------

class TestMemoryValidation:
    def test_validate_node_input_empty(self):
        from aios.core.memory.store import reset_memory_store
        reset_memory_store()
        store = MemoryStore()
        errors = store.validation.validate_node_input(NodeInput(type="", title=""))
        assert len(errors) >= 1

    def test_validate_node_input_valid(self):
        from aios.core.memory.store import reset_memory_store
        reset_memory_store()
        store = MemoryStore()
        errors = store.validation.validate_node_input(NodeInput(type="test", title="Hello"))
        assert len(errors) == 0

    def test_validate_edge_input_invalid_strength(self):
        from aios.core.memory.store import reset_memory_store
        reset_memory_store()
        store = MemoryStore()
        errors = store.validation.validate_edge_input(EdgeInput(type="related_to", strength=1.5))
        assert len(errors) >= 1

    def test_validate_edge_input_valid(self):
        from aios.core.memory.store import reset_memory_store
        reset_memory_store()
        store = MemoryStore()
        errors = store.validation.validate_edge_input(EdgeInput(type="related_to"))
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# MemoryStore integration tests
# ---------------------------------------------------------------------------

class TestMemoryStore:
    @pytest.fixture
    def store(self):
        reset_memory_store()
        return MemoryStore()

    def test_create_node(self, store):
        node, errors = store.create_node(NodeInput(type="test", title="Hello"))
        assert node is not None
        assert len(errors) == 0

    def test_create_node_validation_fails(self, store):
        node, errors = store.create_node(NodeInput(type="", title=""))
        assert node is None
        assert len(errors) > 0

    def test_create_edge(self, store):
        n1, _ = store.create_node(NodeInput(type="a", title="A"))
        n2, _ = store.create_node(NodeInput(type="b", title="B"))
        edge, errors = store.create_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        assert edge is not None
        assert len(errors) == 0

    def test_create_edge_missing_node(self, store):
        edge, errors = store.create_edge(EdgeInput(sourceNodeId=make_node_id("missing"), targetNodeId=make_node_id("missing2"), type="related_to"))
        assert edge is None
        assert len(errors) > 0

    def test_delete_node(self, store):
        node, _ = store.create_node(NodeInput(type="test", title="Delete me"))
        assert store.delete_node(node.id) is True

    def test_archive_restore(self, store):
        node, _ = store.create_node(NodeInput(type="test", title="Archive me"))
        archived = store.archive_node(node.id)
        assert archived.archived is True
        restored = store.restore_node(node.id)
        assert restored.archived is False

    def test_snapshot_roundtrip(self, store):
        n1, _ = store.create_node(NodeInput(type="a", title="A"))
        n2, _ = store.create_node(NodeInput(type="b", title="B"))
        store.create_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        snap = store.snapshot()
        store2 = MemoryStore()
        store2.load_snapshot(snap)
        assert store2.graph.node_count() == 2
        assert store2.graph.edge_count() == 1

    def test_clear(self, store):
        store.create_node(NodeInput(type="test", title="A"))
        store.clear()
        assert store.graph.node_count() == 0

    def test_stats(self, store):
        store.create_node(NodeInput(type="a", title="A"))
        store.create_node(NodeInput(type="b", title="B"))
        stats = store.stats()
        assert stats.totalNodes == 2
        assert stats.totalEdges == 0

    def test_search_multiple_nodes(self, store):
        store.create_node(NodeInput(type="knowledge", title="Python basics", tags=["python"]))
        store.create_node(NodeInput(type="knowledge", title="Python advanced", tags=["python"]))
        store.create_node(NodeInput(type="preference", title="Dark theme", tags=["theme"]))
        result = store.search_by_keyword("Python")
        assert len(result.nodes) == 2
        result2 = store.search_by_keyword("Dark")
        assert len(result2.nodes) == 1


# ---------------------------------------------------------------------------
# BFS/DFS through store
# ---------------------------------------------------------------------------

class TestStoreTraversal:
    @pytest.fixture
    def store(self):
        reset_memory_store()
        s = MemoryStore()
        n1, _ = s.create_node(NodeInput(type="a", title="Root"))
        n2, _ = s.create_node(NodeInput(type="b", title="Child1"))
        n3, _ = s.create_node(NodeInput(type="c", title="Child2"))
        n4, _ = s.create_node(NodeInput(type="d", title="Grandchild"))
        s.create_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="contains"))
        s.create_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n3.id, type="contains"))
        s.create_edge(EdgeInput(sourceNodeId=n2.id, targetNodeId=n4.id, type="contains"))
        return s, n1, n4

    def test_bfs(self, store):
        s, root, _ = store
        result = s.bfs(root.id)
        assert len(result.nodes) == 4

    def test_dfs(self, store):
        s, root, _ = store
        result = s.dfs(root.id)
        assert len(result.nodes) == 4

    def test_find_paths(self, store):
        s, root, leaf = store
        paths = s.find_paths(root.id, leaf.id)
        assert len(paths) >= 1


# ---------------------------------------------------------------------------
# QueryParser tests
# ---------------------------------------------------------------------------

class TestQueryParser:
    def test_parse_full_query(self):
        p = QueryParser()
        query = SearchQuery(
            keyword="test",
            filters=SearchFilters(types=["knowledge"], tags=["python"]),
            options=QueryOptions(sortField="createdAt", sortOrder="asc", limit=10, offset=5),
        )
        parsed = p.parse(query)
        assert parsed["keyword"] == "test"
        assert parsed["filters"]["types"] == ["knowledge"]
        assert parsed["filters"]["tags"] == ["python"]
        assert parsed["options"]["sortField"] == "createdAt"
        assert parsed["options"]["limit"] == 10
        assert parsed["options"]["offset"] == 5

    def test_parse_empty(self):
        p = QueryParser()
        parsed = p.parse(SearchQuery())
        assert parsed["keyword"] is None
        assert parsed["options"]["sortField"] == "updatedAt"


# ---------------------------------------------------------------------------
# Event publishing on graph changes
# ---------------------------------------------------------------------------

class TestGraphEvents:
    def test_node_created_event(self):
        g = MemoryGraph()
        events = []
        g.on_node_change(lambda c: events.append(c.type))
        g.add_node(NodeInput(type="test", title="Event Test"))
        assert "created" in events

    def test_node_deleted_event(self):
        g = MemoryGraph()
        events = []
        g.on_node_change(lambda c: events.append(c.type))
        n = g.add_node(NodeInput(type="test", title="Delete"))
        g.delete_node(n.id)
        assert "deleted" in events

    def test_edge_created_event(self):
        g = MemoryGraph()
        events = []
        g.on_edge_change(lambda c: events.append(c.type))
        n1 = g.add_node(NodeInput(type="a", title="A"))
        n2 = g.add_node(NodeInput(type="b", title="B"))
        g.add_edge(EdgeInput(sourceNodeId=n1.id, targetNodeId=n2.id, type="related_to"))
        assert "created" in events

    def test_unsubscribe(self):
        g = MemoryGraph()
        events = []
        unsub = g.on_node_change(lambda c: events.append(c.type))
        g.add_node(NodeInput(type="test", title="First"))
        unsub()
        g.add_node(NodeInput(type="test", title="Second"))
        assert len(events) == 1
