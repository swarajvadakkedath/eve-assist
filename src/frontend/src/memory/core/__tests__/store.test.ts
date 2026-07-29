import { describe, it, expect, beforeEach, vi } from "vitest"
import { MemoryEventBus } from "../store/MemoryEvents"
import { MemorySelectors } from "../store/MemorySelectors"
import { MemoryStore, getMemoryStore, resetMemoryStore, setMemoryStore } from "../store/MemoryStore"
import { MemoryGraph } from "../graph/MemoryGraph"
import type { NodeInput, MemoryEvent, NodeId } from "../types"

describe("MemoryEventBus", () => {
  let bus: MemoryEventBus

  beforeEach(() => {
    bus = new MemoryEventBus()
  })

  it("emits and receives events", () => {
    const handler = vi.fn()
    bus.on("node:created", handler)
    bus.emit({ type: "node:created", payload: {} as never })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it("handles wildcard subscribers (onAny)", () => {
    const handler = vi.fn()
    bus.onAny(handler)
    bus.emit({ type: "node:created", payload: {} as never })
    bus.emit({ type: "edge:created", payload: {} as never })
    expect(handler).toHaveBeenCalledTimes(2)
  })

  it("handles once subscribers", () => {
    const handler = vi.fn()
    bus.once("node:created", handler)
    bus.emit({ type: "node:created", payload: {} as never })
    bus.emit({ type: "node:created", payload: {} as never })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it("unsubscribes from events", () => {
    const handler = vi.fn()
    const unsub = bus.on("node:created", handler)
    unsub()
    bus.emit({ type: "node:created", payload: {} as never })
    expect(handler).not.toHaveBeenCalled()
  })

  it("supports filtered subscribers", () => {
    const handler = vi.fn()
    bus.subscribe({
      id: "filtered",
      callback: handler,
      filter: (e: MemoryEvent) => e.type === "node:created",
    })
    bus.emit({ type: "node:updated", payload: {} as never })
    expect(handler).not.toHaveBeenCalled()
    bus.emit({ type: "node:created", payload: {} as never })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it("removes specific event listeners", () => {
    const handler = vi.fn()
    bus.on("node:created", handler)
    bus.off("node:created", handler)
    bus.emit({ type: "node:created", payload: {} as never })
    expect(handler).not.toHaveBeenCalled()
  })

  it("maintains event history", () => {
    bus.emit({ type: "node:created", payload: {} as never })
    bus.emit({ type: "edge:created", payload: {} as never })
    expect(bus.getHistory()).toHaveLength(2)
    expect(bus.getHistory("node:created")).toHaveLength(1)
  })

  it("limits event history", () => {
    const smallBus = new MemoryEventBus(3)
    for (let i = 0; i < 5; i++) {
      smallBus.emit({ type: "node:created", payload: {} as never })
    }
    expect(smallBus.getHistory()).toHaveLength(3)
  })

  it("clears event history", () => {
    bus.emit({ type: "node:created", payload: {} as never })
    bus.clearHistory()
    expect(bus.getHistory()).toHaveLength(0)
  })

  it("removes all listeners", () => {
    bus.on("node:created", () => {})
    bus.on("edge:created", () => {})
    expect(bus.listenerCount()).toBe(2)
    bus.removeAllListeners()
    expect(bus.listenerCount()).toBe(0)
  })

  it("removes listeners by type", () => {
    bus.on("node:created", () => {})
    bus.on("edge:created", () => {})
    bus.removeAllListeners("node:created")
    expect(bus.listenerCount("node:created")).toBe(0)
    expect(bus.listenerCount("edge:created")).toBe(1)
  })

  it("counts listeners", () => {
    bus.on("node:created", () => {})
    bus.onAny(() => {})
    expect(bus.listenerCount()).toBe(2)
    expect(bus.listenerCount("node:created")).toBe(1)
    expect(bus.listenerCount("edge:created")).toBe(0)
  })
})

describe("MemorySelectors", () => {
  let graph: MemoryGraph
  let selectors: MemorySelectors

  beforeEach(() => {
    graph = new MemoryGraph()
    selectors = new MemorySelectors(graph)
  })

  function addNode(overrides: Partial<NodeInput> = {}): NodeId {
    return graph.addNode({
      type: "test:node",
      subtype: "test",
      title: "Test",
      source: "test",
      tags: [],
      ...overrides,
    }).id
  }

  it("gets recent nodes", () => {
    addNode({ id: "a", title: "A" })
    addNode({ id: "b", title: "B" })
    const recent = selectors.getRecentNodes(2)
    expect(recent).toHaveLength(2)
  })

  it("gets most accessed nodes", () => {
    addNode({ id: "a", title: "A" })
    addNode({ id: "b", title: "B" })
    // Access "a" twice
    graph.getNode({ value: "a", type: "test:node" })
    graph.getNode({ value: "a", type: "test:node" })

    const mostAccessed = selectors.getMostAccessedNodes(2)
    expect(mostAccessed[0].id.value).toBe("a")
  })

  it("gets most important nodes", () => {
    addNode({ id: "a", title: "A", importance: 8 })
    addNode({ id: "b", title: "B", importance: 3 })
    const important = selectors.getMostImportantNodes(1)
    expect(important).toHaveLength(1)
    expect(important[0].id.value).toBe("a")
  })

  it("gets highest confidence nodes", () => {
    addNode({ id: "a", title: "A", confidence: 0.9 })
    addNode({ id: "b", title: "B", confidence: 0.5 })
    const confident = selectors.getHighestConfidenceNodes(1)
    expect(confident).toHaveLength(1)
    expect(confident[0].id.value).toBe("a")
  })

  it("gets pinned nodes", () => {
    addNode({ id: "a", title: "A", pinned: true })
    addNode({ id: "b", title: "B" })
    const pinned = selectors.getPinnedNodes()
    expect(pinned).toHaveLength(1)
    expect(pinned[0].id.value).toBe("a")
  })

  it("excludes archived from pinned", () => {
    graph.addNode({
      type: "test:node", subtype: "test", title: "A", source: "test", id: "a", pinned: true,
    })
    graph.archiveNode({ value: "a", type: "test:node" })
    expect(selectors.getPinnedNodes()).toHaveLength(0)
  })

  it("gets archived nodes", () => {
    addNode({ id: "a", title: "A" })
    graph.archiveNode({ value: "a", type: "test:node" })
    addNode({ id: "b", title: "B" })
    expect(selectors.getArchivedNodes()).toHaveLength(1)
  })

  it("gets active nodes", () => {
    addNode({ id: "a", title: "A" })
    const b = addNode({ id: "b", title: "B" })
    graph.archiveNode(b)
    expect(selectors.getActiveNodes()).toHaveLength(1)
  })

  it("gets nodes by super type", () => {
    addNode({ id: "a", type: "action:exec" })
    addNode({ id: "b", type: "observation:cap" })
    expect(selectors.getActionNodes()).toHaveLength(1)
    expect(selectors.getObservationNodes()).toHaveLength(1)
    expect(selectors.getKnowledgeNodes()).toHaveLength(0)
  })

  it("gets nodes with tag", () => {
    addNode({ id: "a", tags: ["important"] })
    addNode({ id: "b", tags: ["normal"] })
    expect(selectors.getNodesWithTag("important")).toHaveLength(1)
  })

  it("gets nodes with tags (any/all)", () => {
    addNode({ id: "a", tags: ["x", "y"] })
    addNode({ id: "b", tags: ["y", "z"] })
    expect(selectors.getNodesWithTags(["x", "z"], "any")).toHaveLength(2)
    expect(selectors.getNodesWithTags(["x", "y"], "all")).toHaveLength(1)
  })

  it("gets nodes from source", () => {
    addNode({ id: "a", source: "api" })
    addNode({ id: "b", source: "user" })
    expect(selectors.getNodesFromSource("api")).toHaveLength(1)
  })

  it("gets nodes by status", () => {
    addNode({ id: "a" })
    graph.archiveNode({ value: "a", type: "test:node" })
    addNode({ id: "b" })
    expect(selectors.getNodesByStatus("active")).toHaveLength(1)
    expect(selectors.getNodesByStatus("archived")).toHaveLength(1)
  })

  it("counts nodes and edges", () => {
    addNode({ id: "a" })
    addNode({ id: "b" })
    expect(selectors.getNodeCount()).toBe(2)
    expect(selectors.getEdgeCount()).toBe(0)
  })

  it("does text search across title, summary, tags, type, subtype", () => {
    addNode({ id: "a", title: "Hello World", tags: ["greeting"] })
    addNode({ id: "b", title: "Goodbye", summary: "farewell message" })

    const results = selectors.search("hello")
    expect(results).toHaveLength(1)
    expect(results[0].id.value).toBe("a")

    const results2 = selectors.search("farewell")
    expect(results2).toHaveLength(1)

    const results3 = selectors.search("greeting")
    expect(results3).toHaveLength(1)

    const results4 = selectors.search("nothing")
    expect(results4).toHaveLength(0)
  })

  it("finds duplicates with custom predicate", () => {
    addNode({ id: "a", title: "Same" })
    addNode({ id: "b", title: "Same" })
    addNode({ id: "c", title: "Different" })

    const duplicates = selectors.findDuplicates((a, b) => a.title === b.title)
    expect(duplicates).toHaveLength(1)
    expect(duplicates[0][0].id.value).toBe("a")
    expect(duplicates[0][1].id.value).toBe("b")
  })

  it("gets stats", () => {
    addNode({ id: "a", type: "action:exec" })
    const b = addNode({ id: "b", type: "observation:cap" })
    addNode({ id: "c", type: "action:cmd", pinned: true })
    graph.archiveNode(b)

    const stats = selectors.getStats()
    expect(stats.total).toBe(3)
    expect(stats.active).toBe(2)
    expect(stats.archived).toBe(1)
    expect(stats.pinned).toBe(1)
  })
})

describe("MemoryStore", () => {
  let store: MemoryStore

  beforeEach(() => {
    store = new MemoryStore()
  })

  it("creates and retrieves nodes", () => {
    const node = store.addNode({
      type: "test:node",
      subtype: "test",
      title: "Hello",
      source: "test",
    })
    expect(node.title).toBe("Hello")
    expect(store.getNode(node.id)).toBeDefined()
  })

  it("emits events on node operations", () => {
    const handler = vi.fn()
    store.onNodeEvent("created", handler)

    store.addNode({ type: "test", subtype: "test", title: "X", source: "test" })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it("emits events on edge operations", () => {
    store.registry.registerNodeType({
      name: "test",
      superType: "action",
      description: "Test",
      allowedEdgeTypes: ["connects"],
      allowedAsTargetFor: ["connects"],
      defaultMetadata: {},
    })
    store.registry.registerEdgeType({
      name: "connects",
      description: "Connects",
      allowedSourceTypes: ["test"],
      allowedTargetTypes: ["test"],
      directional: true,
      defaultMetadata: {},
    })

    const handler = vi.fn()
    store.onEdgeEvent("created", handler)

    const a = store.addNode({ type: "test", subtype: "test", title: "A", source: "test", id: "a" })
    const b = store.addNode({ type: "test", subtype: "test", title: "B", source: "test", id: "b" })
    store.addEdge({ sourceNodeId: a.id, targetNodeId: b.id, type: "connects" })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it("handles any events", () => {
    const handler = vi.fn()
    store.onAnyEvent(handler)

    store.addNode({ type: "test", subtype: "test", title: "X", source: "test" })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it("subscribes to state changes", () => {
    const listener = vi.fn()
    store.subscribe(listener)

    store.addNode({ type: "test", subtype: "test", title: "X", source: "test" })
    expect(listener).toHaveBeenCalled()
  })

  it("gets state", () => {
    const state = store.getState()
    expect(state).toHaveProperty("nodeCount")
    expect(state).toHaveProperty("edgeCount")
    expect(state).toHaveProperty("lastEvent")
  })

  it("updates node count after adding/removing", () => {
    expect(store.getState().nodeCount).toBe(0)
    const node = store.addNode({ type: "test", subtype: "test", title: "X", source: "test" })
    expect(store.getState().nodeCount).toBe(1)
    store.deleteNode(node.id)
    expect(store.getState().nodeCount).toBe(0)
  })

  it("snapshots and loads", () => {
    store.addNode({ type: "test", subtype: "test", title: "A", source: "test", id: "a" })
    const snap = store.snapshot()
    expect(snap.nodes).toHaveLength(1)

    const store2 = new MemoryStore()
    store2.loadSnapshot(snap)
    expect(store2.getState().nodeCount).toBe(1)
  })

  it("clears the store", () => {
    store.addNode({ type: "test", subtype: "test", title: "A", source: "test" })
    store.clear()
    expect(store.getState().nodeCount).toBe(0)
  })

  it("gets stats", () => {
    store.addNode({ type: "action:exec", subtype: "test", title: "X", source: "test" })
    const stats = store.getStats()
    expect(stats.total).toBe(1)
  })

  it("searches via query engine", () => {
    store.addNode({ type: "test", subtype: "test", title: "Hello World", source: "test", tags: ["greeting"] })
    const results = store.search({
      keyword: "hello",
      options: {},
    })
    expect(results.nodes).toHaveLength(1)
  })

  describe("singleton access", () => {
    it("gets/sets/resets default store", () => {
      resetMemoryStore()
      const s = getMemoryStore()
      expect(s).toBeInstanceOf(MemoryStore)

      const newStore = new MemoryStore()
      setMemoryStore(newStore)
      expect(getMemoryStore()).toBe(newStore)

      resetMemoryStore()
      expect(getMemoryStore()).not.toBe(newStore)
    })
  })
})
