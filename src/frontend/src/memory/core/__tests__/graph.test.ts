import { describe, it, expect, beforeEach } from "vitest"
import { MemoryGraph } from "../graph/MemoryGraph"
import { GraphTraversal } from "../graph/GraphTraversal"
import { RelationshipEngine } from "../graph/RelationshipEngine"
import { MemoryRegistry } from "../registry/MemoryRegistry"
import type { NodeInput, NodeId, NodeChange, EdgeChange } from "../types"

describe("MemoryGraph", () => {
  let graph: MemoryGraph

  beforeEach(() => {
    graph = new MemoryGraph()
  })

  function makeNodeInput(overrides: Partial<NodeInput> = {}): NodeInput {
    return {
      type: "test:node",
      subtype: "test",
      title: "Test Node",
      source: "test",
      ...overrides,
    }
  }

  it("adds a node", () => {
    const node = graph.addNode(makeNodeInput({ title: "Hello" }))
    expect(node.id.value).toBeTruthy()
    expect(node.id.type).toBe("test:node")
    expect(node.title).toBe("Hello")
    expect(node.createdAt).toBeGreaterThan(0)
    expect(node.updatedAt).toBeGreaterThan(0)
    expect(node.importance).toBe(1)
    expect(node.confidence).toBe(1)
    expect(node.status).toBe("active")
    expect(node.archived).toBe(false)
    expect(node.pinned).toBe(false)
  })

  it("adds a node with custom ID", () => {
    const node = graph.addNode(makeNodeInput({ id: "custom-id" }))
    expect(node.id.value).toBe("custom-id")
    expect(node.id.type).toBe("test:node")
  })

  it("retrieves a node by ID", () => {
    const node = graph.addNode(makeNodeInput())
    const retrieved = graph.getNode(node.id)
    expect(retrieved).toBeDefined()
    expect(retrieved!.id.value).toBe(node.id.value)
  })

  it("touches node on access (updates lastAccessed)", () => {
    const node = graph.addNode(makeNodeInput())
    const before = node.lastAccessed
    graph.getNode(node.id)
    const after = graph.getNode(node.id)!.lastAccessed
    expect(after).toBeGreaterThanOrEqual(before)
    expect(graph.getNode(node.id)!.accessCount).toBe(2)
  })

  it("updates a node", () => {
    const node = graph.addNode(makeNodeInput({ title: "Original" }))
    const updated = graph.updateNode(node.id, { title: "Updated", importance: 5 })
    expect(updated!.title).toBe("Updated")
    expect(updated!.importance).toBe(5)
    expect(updated!.updatedAt).toBeGreaterThanOrEqual(node.updatedAt)
  })

  it("returns undefined when updating unknown node", () => {
    const result = graph.updateNode({ value: "unknown", type: "test" }, { title: "X" })
    expect(result).toBeUndefined()
  })

  it("deletes a node", () => {
    const node = graph.addNode(makeNodeInput())
    expect(graph.hasNode(node.id)).toBe(true)
    expect(graph.deleteNode(node.id)).toBe(true)
    expect(graph.hasNode(node.id)).toBe(false)
  })

  it("deletes a node's edges when node is deleted", () => {
    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const b = graph.addNode(makeNodeInput({ id: "b" }))
    graph.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "contains" })
    expect(graph.edgeCount()).toBe(1)
    graph.deleteNode(a.id)
    expect(graph.edgeCount()).toBe(0)
  })

  it("returns false when deleting unknown node", () => {
    expect(graph.deleteNode({ value: "unknown", type: "test" })).toBe(false)
  })

  it("archives and restores nodes", () => {
    const node = graph.addNode(makeNodeInput())
    const archived = graph.archiveNode(node.id)
    expect(archived!.archived).toBe(true)
    expect(archived!.status).toBe("archived")

    const restored = graph.restoreNode(node.id)
    expect(restored!.archived).toBe(false)
    expect(restored!.status).toBe("active")
  })

  it("adds an edge between existing nodes", () => {
    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const b = graph.addNode(makeNodeInput({ id: "b" }))
    const edge = graph.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "contains" })
    expect(edge).toBeDefined()
    expect(edge!.type).toBe("contains")
    expect(edge!.strength).toBe(1)
    expect(edge!.weight).toBe(1)
  })

  it("returns undefined when adding edge to missing node", () => {
    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const missingId: NodeId = { value: "missing", type: "test:node" }
    const edge = graph.addEdge({ sourceNodeId: a.id, targetNodeId: missingId, type: "contains" })
    expect(edge).toBeUndefined()
  })

  it("deletes an edge", () => {
    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const b = graph.addNode(makeNodeInput({ id: "b" }))
    const edge = graph.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "contains" })!
    expect(graph.deleteEdge(edge.id)).toBe(true)
    expect(graph.getEdge(edge.id)).toBeUndefined()
  })

  it("retrieves edges by node", () => {
    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const b = graph.addNode(makeNodeInput({ id: "b" }))
    const c = graph.addNode(makeNodeInput({ id: "c" }))
    graph.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "contains" })
    graph.addEdge({ sourceNodeId: a.id, targetNodeId: c.id, type: "references" })
    expect(graph.getEdgesByNode(a.id)).toHaveLength(2)
    expect(graph.getEdgesByNode(b.id)).toHaveLength(1)
  })

  it("retrieves outgoing/incoming edges and neighbors", () => {
    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const b = graph.addNode(makeNodeInput({ id: "b" }))
    graph.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "contains" })

    const outEdges = graph.getOutgoingEdges(a.id)
    expect(outEdges).toHaveLength(1)
    expect(outEdges[0].targetNodeId.value).toBe("b")

    const inEdges = graph.getIncomingEdges(b.id)
    expect(inEdges).toHaveLength(1)
    expect(inEdges[0].sourceNodeId.value).toBe("a")

    const outNeighbors = graph.getOutgoingNeighbors(a.id)
    expect(outNeighbors).toHaveLength(1)
    expect(outNeighbors[0].id.value).toBe("b")

    const inNeighbors = graph.getIncomingNeighbors(b.id)
    expect(inNeighbors).toHaveLength(1)
    expect(inNeighbors[0].id.value).toBe("a")
  })

  it("retrieves all neighbors (outgoing + incoming, deduped)", () => {
    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const b = graph.addNode(makeNodeInput({ id: "b" }))
    const c = graph.addNode(makeNodeInput({ id: "c" }))
    graph.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "contains" })
    graph.addEdge({ sourceNodeId: c.id, targetNodeId: a.id, type: "references" })

    const neighbors = graph.getNeighbors(a.id)
    expect(neighbors).toHaveLength(2)
  })

  it("gets connected edges", () => {
    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const b = graph.addNode(makeNodeInput({ id: "b" }))
    graph.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "contains" })

    const { outgoing, incoming } = graph.getConnectedEdges(a.id)
    expect(outgoing).toHaveLength(1)
    expect(incoming).toHaveLength(0)
  })

  it("returns nodes by type", () => {
    graph.addNode(makeNodeInput({ id: "a", type: "test:type-a" }))
    graph.addNode(makeNodeInput({ id: "b", type: "test:type-a" }))
    graph.addNode(makeNodeInput({ id: "c", type: "test:type-b" }))

    expect(graph.getNodesByType("test:type-a")).toHaveLength(2)
    expect(graph.getNodesByType("test:type-b")).toHaveLength(1)
    expect(graph.getNodesByType("unknown")).toHaveLength(0)
  })

  it("returns nodes by super type", () => {
    graph.addNode(makeNodeInput({ id: "a", type: "action:exec" }))
    graph.addNode(makeNodeInput({ id: "b", type: "action:cmd" }))
    graph.addNode(makeNodeInput({ id: "c", type: "observation:capture" }))

    expect(graph.getNodesBySuperType("action")).toHaveLength(2)
    expect(graph.getNodesBySuperType("observation")).toHaveLength(1)
  })

  it("takes a snapshot", () => {
    graph.addNode(makeNodeInput({ id: "a" }))
    graph.addNode(makeNodeInput({ id: "b" }))
    const snap = graph.snapshot()
    expect(snap.nodes).toHaveLength(2)
    expect(snap.timestamp).toBeGreaterThan(0)
  })

  it("loads from a snapshot", () => {
    graph.addNode(makeNodeInput({ id: "a" }))
    graph.addNode(makeNodeInput({ id: "b" }))
    const snap = graph.snapshot()

    const graph2 = new MemoryGraph()
    graph2.loadSnapshot(snap)
    expect(graph2.nodeCount()).toBe(2)
  })

  it("clears the graph", () => {
    graph.addNode(makeNodeInput({ id: "a" }))
    graph.addNode(makeNodeInput({ id: "b" }))
    graph.clear()
    expect(graph.nodeCount()).toBe(0)
    expect(graph.edgeCount()).toBe(0)
  })

  it("computes stats", () => {
    graph.addNode(makeNodeInput({ id: "a", type: "action:exec", pinned: true }))
    const b = graph.addNode(makeNodeInput({ id: "b", type: "observation:cap" }))
    graph.archiveNode(b.id)

    const stats = graph.stats()
    expect(stats.totalNodes).toBe(2)
    expect(stats.totalArchived).toBe(1)
    expect(stats.totalPinned).toBe(1)
    expect(stats.byType["action:exec"]).toBe(1)
    expect(stats.byType["observation:cap"]).toBe(1)
  })

  it("notifies on node changes", () => {
    const changes: NodeChange[] = []
    graph.onNodeChange((c) => changes.push(c))

    const node = graph.addNode(makeNodeInput({ id: "a" }))
    expect(changes).toHaveLength(1)
    expect(changes[0].type).toBe("created")

    graph.updateNode(node.id, { title: "Updated" })
    expect(changes).toHaveLength(2)
    expect(changes[1].type).toBe("updated")

    graph.archiveNode(node.id)
    expect(changes).toHaveLength(3)
    expect(changes[2].type).toBe("archived")

    graph.restoreNode(node.id)
    expect(changes).toHaveLength(4)
    expect(changes[3].type).toBe("restored")

    graph.deleteNode(node.id)
    expect(changes).toHaveLength(5)
    expect(changes[4].type).toBe("deleted")
  })

  it("notifies on edge changes", () => {
    const changes: EdgeChange[] = []
    graph.onEdgeChange((c) => changes.push(c))

    const a = graph.addNode(makeNodeInput({ id: "a" }))
    const b = graph.addNode(makeNodeInput({ id: "b" }))

    graph.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "contains" })
    expect(changes).toHaveLength(1)
    expect(changes[0].type).toBe("created")
  })

  it("unsubscribes node listeners", () => {
    let count = 0
    const unsub = graph.onNodeChange(() => count++)
    graph.addNode(makeNodeInput({ id: "a" }))
    expect(count).toBe(1)
    unsub()
    graph.addNode(makeNodeInput({ id: "b" }))
    expect(count).toBe(1)
  })
})

describe("GraphTraversal", () => {
  let graph: MemoryGraph
  let traversal: GraphTraversal

  beforeEach(() => {
    graph = new MemoryGraph()
    traversal = new GraphTraversal(graph)
  })

  function addNode(id: string, type = "test:node"): NodeId {
    return graph.addNode({ type, subtype: "test", title: id, source: "test", id }).id
  }

  it("returns empty result for missing start node", () => {
    const result = traversal.bfs({ value: "missing", type: "test" })
    expect(result.nodes).toHaveLength(0)
    expect(result.depth).toBe(0)
  })

  it("traverses BFS", () => {
    const a = addNode("a")
    const b = addNode("b")
    const c = addNode("c")
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "contains" })
    graph.addEdge({ sourceNodeId: a, targetNodeId: c, type: "contains" })

    const result = traversal.bfs(a)
    expect(result.nodes).toHaveLength(3)
    expect(result.edges).toHaveLength(2)
  })

  it("traverses DFS", () => {
    const a = addNode("a")
    const b = addNode("b")
    const c = addNode("c")
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "contains" })
    graph.addEdge({ sourceNodeId: b, targetNodeId: c, type: "contains" })

    const result = traversal.dfs(a)
    expect(result.nodes).toHaveLength(3)
    expect(result.edges).toHaveLength(2)
  })

  it("respects max depth in BFS", () => {
    const a = addNode("a")
    const b = addNode("b")
    const c = addNode("c")
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "contains" })
    graph.addEdge({ sourceNodeId: b, targetNodeId: c, type: "contains" })

    const result = traversal.bfs(a, { maxDepth: 1 })
    expect(result.nodes).toHaveLength(2) // a and b only
  })

  it("filters by edge type", () => {
    const a = addNode("a")
    const b = addNode("b")
    const c = addNode("c")
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "contains" })
    graph.addEdge({ sourceNodeId: a, targetNodeId: c, type: "references" })

    const result = traversal.bfs(a, { edgeTypes: ["references"] })
    expect(result.nodes).toHaveLength(2) // a and c
    expect(result.edges).toHaveLength(1)
  })

  it("finds paths between nodes", () => {
    const a = addNode("a")
    const b = addNode("b")
    const c = addNode("c")
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "contains" })
    graph.addEdge({ sourceNodeId: b, targetNodeId: c, type: "contains" })

    const paths = traversal.findPaths(a, c)
    expect(paths).toHaveLength(1)
    expect(paths[0].nodes).toHaveLength(3)
    expect(paths[0].path).toBeDefined()
  })

  it("finds shortest path", () => {
    const a = addNode("a")
    const b = addNode("b")
    const c = addNode("c")
    const d = addNode("d")
    // a -> b -> c (short: 2 edges)
    // a -> d -> c (same length)
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "contains" })
    graph.addEdge({ sourceNodeId: b, targetNodeId: c, type: "contains" })
    graph.addEdge({ sourceNodeId: a, targetNodeId: d, type: "contains" })
    graph.addEdge({ sourceNodeId: d, targetNodeId: c, type: "contains" })

    const path = traversal.findShortestPath(a, c)
    expect(path).toBeDefined()
    expect(path!.nodes).toHaveLength(3) // a, b, c or a, d, c
  })

  it("gets connected component", () => {
    const a = addNode("a")
    const b = addNode("b")
    const c = addNode("c")
    addNode("isolated")
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "contains" })
    graph.addEdge({ sourceNodeId: b, targetNodeId: c, type: "contains" })

    const component = traversal.getConnectedComponent(a)
    expect(component.nodes).toHaveLength(3) // a, b, c
    expect(component.nodes.find((n) => n.id.value === "isolated")).toBeUndefined()
  })

  it("gets neighbors at depth", () => {
    const a = addNode("a")
    const b = addNode("b")
    const c = addNode("c")
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "contains" })
    graph.addEdge({ sourceNodeId: b, targetNodeId: c, type: "contains" })

    const depth1 = traversal.getNeighborsAtDepth(a, 1)
    expect(depth1).toHaveLength(1)
    expect(depth1[0].id.value).toBe("b")

    const depth2 = traversal.getNeighborsAtDepth(a, 2)
    expect(depth2).toHaveLength(1)
    expect(depth2[0].id.value).toBe("c")
  })

  it("gets neighbors at depth 0 (self)", () => {
    const a = addNode("a")
    const result = traversal.getNeighborsAtDepth(a, 0)
    expect(result).toHaveLength(1)
    expect(result[0].id.value).toBe("a")
  })
})

describe("RelationshipEngine", () => {
  let graph: MemoryGraph
  let registry: MemoryRegistry
  let engine: RelationshipEngine

  beforeEach(() => {
    graph = new MemoryGraph()
    registry = new MemoryRegistry()
    registry.registerNodeType({
      name: "source:type",
      superType: "action",
      description: "Source",
      allowedEdgeTypes: ["connects"],
      allowedAsTargetFor: ["connects"],
      defaultMetadata: {},
    })
    registry.registerNodeType({
      name: "target:type",
      superType: "observation",
      description: "Target",
      allowedEdgeTypes: ["connects"],
      allowedAsTargetFor: ["connects"],
      defaultMetadata: {},
    })
    registry.registerEdgeType({
      name: "connects",
      description: "Connects",
      allowedSourceTypes: ["source:type"],
      allowedTargetTypes: ["target:type"],
      directional: true,
      defaultMetadata: {},
    })
    engine = new RelationshipEngine(graph, registry)
  })

  function addSource(id: string): NodeId {
    return graph.addNode({
      id,
      type: "source:type",
      subtype: "test",
      title: id,
      source: "test",
    }).id
  }

  function addTarget(id: string): NodeId {
    return graph.addNode({
      id,
      type: "target:type",
      subtype: "test",
      title: id,
      source: "test",
    }).id
  }

  it("validates a valid edge", () => {
    const source = addSource("a")
    const target = addTarget("b")
    const { valid, errors } = engine.canAddEdge({
      sourceNodeId: source,
      targetNodeId: target,
      type: "connects",
    })
    expect(valid).toBe(true)
    expect(errors).toHaveLength(0)
  })

  it("rejects edge with missing source node", () => {
    const missing: NodeId = { value: "missing", type: "source:type" }
    const target = addTarget("b")
    const { valid, errors } = engine.canAddEdge({
      sourceNodeId: missing,
      targetNodeId: target,
      type: "connects",
    })
    expect(valid).toBe(false)
    expect(errors.some((e) => e.code === "SOURCE_NODE_NOT_FOUND")).toBe(true)
  })

  it("rejects edge with missing target node", () => {
    const source = addSource("a")
    const missing: NodeId = { value: "missing", type: "target:type" }
    const { valid, errors } = engine.canAddEdge({
      sourceNodeId: source,
      targetNodeId: missing,
      type: "connects",
    })
    expect(valid).toBe(false)
    expect(errors.some((e) => e.code === "TARGET_NODE_NOT_FOUND")).toBe(true)
  })

  it("rejects edge with unknown type", () => {
    const source = addSource("a")
    const target = addTarget("b")
    const { valid, errors } = engine.canAddEdge({
      sourceNodeId: source,
      targetNodeId: target,
      type: "unknown",
    })
    expect(valid).toBe(false)
    expect(errors.some((e) => e.code === "UNKNOWN_EDGE_TYPE")).toBe(true)
  })

  it("rejects edge that violates type constraints", () => {
    const source = addSource("a")
    const target = addTarget("b")
    const { valid, errors } = engine.canAddEdge({
      sourceNodeId: target, // wrong direction
      targetNodeId: source,
      type: "connects",
    })
    expect(valid).toBe(false)
    expect(errors.some((e) => e.code === "INVALID_EDGE_CONNECTION")).toBe(true)
  })

  it("rejects edge with invalid strength", () => {
    const source = addSource("a")
    const target = addTarget("b")
    const { valid, errors } = engine.canAddEdge({
      sourceNodeId: source,
      targetNodeId: target,
      type: "connects",
      strength: 1.5,
    })
    expect(valid).toBe(false)
    expect(errors.some((e) => e.code === "INVALID_STRENGTH")).toBe(true)
  })

  it("rejects edge with invalid weight", () => {
    const source = addSource("a")
    const target = addTarget("b")
    const { valid, errors } = engine.canAddEdge({
      sourceNodeId: source,
      targetNodeId: target,
      type: "connects",
      weight: -1,
    })
    expect(valid).toBe(false)
    expect(errors.some((e) => e.code === "INVALID_WEIGHT")).toBe(true)
  })

  it("detects cycle when adding edge back to source that already has path", () => {
    const a = addSource("a")
    const b = addTarget("b")
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "connects" })
    // wouldCreateCycle(b, a) checks if 'a' can reach 'b' via existing path -> yes (a->b)
    const cycle = engine.wouldCreateCycle(b, a)
    expect(cycle).toBeDefined()
    expect(cycle!.path).toHaveLength(2)
  })

  it("detects self-loop as cycle", () => {
    const a = addSource("a")
    const cycle = engine.wouldCreateCycle(a, a)
    expect(cycle).toBeDefined()
  })

  it("detects cycles in the graph", () => {
    // Need a bidirectional connection to test cycles properly
    const a = graph.addNode({
      id: "a", type: "source:type", subtype: "test", title: "A", source: "test",
    }).id
    const b = graph.addNode({
      id: "b", type: "source:type", subtype: "test", title: "B", source: "test",
    }).id

    // For cycle detection we need edges that go in both directions
    // Let's add edges manually to bypass type checks
    graph.addEdge({ sourceNodeId: a, targetNodeId: b, type: "connects" })
    graph.addEdge({ sourceNodeId: b, targetNodeId: a, type: "connects" })

    const cycles = engine.findCycles()
    expect(cycles.length).toBeGreaterThan(0)
  })

  it("adds edge through engine with validation", () => {
    const source = addSource("a")
    const target = addTarget("b")
    const edge = engine.addEdge({
      sourceNodeId: source,
      targetNodeId: target,
      type: "connects",
    })
    expect(edge).toBeDefined()
    expect(graph.edgeCount()).toBe(1)
  })

  it("does not add invalid edge through engine", () => {
    const source = addSource("a")
    const target = addTarget("b")
    const edge = engine.addEdge({
      sourceNodeId: source,
      targetNodeId: target,
      type: "unknown",
    })
    expect(edge).toBeUndefined()
  })

  it("deletes node with all its edges", () => {
    const a = addSource("a")
    const b = addTarget("b")
    engine.addEdge({ sourceNodeId: a, targetNodeId: b, type: "connects" })
    expect(graph.nodeCount()).toBe(2)
    expect(graph.edgeCount()).toBe(1)

    engine.deleteNodeWithEdges(a)
    expect(graph.nodeCount()).toBe(1)
    expect(graph.edgeCount()).toBe(0)
  })

  it("validates the entire graph", () => {
    const source = addSource("a")
    const target = addTarget("b")
    engine.addEdge({ sourceNodeId: source, targetNodeId: target, type: "connects" })

    const errors = engine.validateGraph()
    expect(errors).toHaveLength(0)
  })

  it("gets relationship summary", () => {
    const source = addSource("a")
    const target = addTarget("b")
    engine.addEdge({ sourceNodeId: source, targetNodeId: target, type: "connects" })

    const summary = engine.getRelationshipSummary(source)
    expect(summary.node).toBeDefined()
    expect(summary.outgoingCount).toBe(1)
    expect(summary.incomingCount).toBe(0)
    expect(summary.totalConnections).toBe(1)
  })
})
