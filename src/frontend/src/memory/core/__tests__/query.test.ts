import { describe, it, expect, beforeEach } from "vitest"
import { QueryEngine } from "../query/QueryEngine"
import { QueryParser } from "../query/QueryParser"
import { MemoryGraph } from "../graph/MemoryGraph"
import { MemorySelectors } from "../store/MemorySelectors"
import type { SearchQuery, NodeId } from "../types"

describe("QueryParser", () => {
  const parser = new QueryParser()

  it("parses a valid query", () => {
    const query: SearchQuery = {
      keyword: "test",
      filters: { types: ["test:node"], tags: ["important"] },
      options: { sortField: "updatedAt", sortOrder: "desc", limit: 10, offset: 0 },
    }
    const parsed = parser.parse(query)
    expect(parsed.keyword).toBe("test")
    expect(parsed.filters.types).toEqual(["test:node"])
    expect(parsed.options.sortField).toBe("updatedAt")
    expect(parsed.options.limit).toBe(10)
  })

  it("applies defaults for missing fields", () => {
    const parsed = parser.parse({ options: {} })
    expect(parsed.options.sortField).toBe("updatedAt")
    expect(parsed.options.sortOrder).toBe("desc")
    expect(parsed.options.offset).toBe(0)
    expect(parsed.options.limit).toBeUndefined()
  })

  it("validates a correct query", () => {
    const query: SearchQuery = {
      keyword: "test",
      filters: {},
      options: { sortField: "createdAt" },
    }
    expect(parser.validate(query)).toBe(true)
  })

  it("validates relationship queries", () => {
    const query: SearchQuery = {
      relationship: {
        seedNodeId: { value: "1", type: "test:node" },
        filter: { maxDepth: 3 },
      },
      options: {},
    }
    expect(parser.validate(query)).toBe(true)
  })

  it("rejects invalid queries", () => {
    expect(parser.validate(null)).toBe(false)
    expect(parser.validate("string")).toBe(false)
    expect(parser.validate(42)).toBe(false)
    expect(parser.validate({})).toBe(true)
  })

  it("rejects invalid keyword type", () => {
    expect(parser.validate({ keyword: 123, options: {} })).toBe(false)
  })

  it("rejects invalid relationship structure", () => {
    expect(parser.validate({ relationship: "invalid", options: {} })).toBe(false)
  })
})

describe("QueryEngine", () => {
  let graph: MemoryGraph
  let selectors: MemorySelectors
  let engine: QueryEngine

  beforeEach(() => {
    graph = new MemoryGraph()
    selectors = new MemorySelectors(graph)
    engine = new QueryEngine(graph, selectors)
  })

  function addNode(overrides: { id?: string; title?: string; type?: string; tags?: string[]; source?: string; importance?: number; confidence?: number; pinned?: boolean; archived?: boolean; status?: string; createdAt?: number } = {}): NodeId {
    return graph.addNode({
      type: overrides.type ?? "test:node",
      subtype: "test",
      title: overrides.title ?? "Test Node",
      source: overrides.source ?? "test",
      id: overrides.id,
      tags: overrides.tags,
      importance: overrides.importance,
      confidence: overrides.confidence,
      pinned: overrides.pinned,
      archived: overrides.archived,
      createdAt: overrides.createdAt,
      status: overrides.status as never,
    }).id
  }

  it("executes a basic query", () => {
    addNode({ id: "a", title: "Hello World", tags: ["greeting"] })
    addNode({ id: "b", title: "Goodbye", tags: ["farewell"] })
    const result = engine.execute({ keyword: "hello", options: {} })
    expect(result.nodes).toHaveLength(1)
    expect(result.total).toBe(1)
  })

  it("finds all nodes", () => {
    addNode({ id: "a", title: "A" })
    addNode({ id: "b", title: "B" })
    const result = engine.findAll()
    expect(result.nodes).toHaveLength(2)
  })

  it("finds by type", () => {
    addNode({ id: "a", title: "A", type: "action:exec" })
    addNode({ id: "b", title: "B", type: "observation:cap" })
    const result = engine.findByType("action:exec")
    expect(result.nodes).toHaveLength(1)
  })

  it("finds by super type", () => {
    addNode({ id: "a", title: "A", type: "action:exec" })
    addNode({ id: "b", title: "B", type: "action:cmd" })
    addNode({ id: "c", title: "C", type: "observation:cap" })
    const result = engine.findBySuperType("action")
    expect(result.nodes).toHaveLength(2)
  })

  it("finds by tag", () => {
    addNode({ id: "a", title: "A", tags: ["important"] })
    addNode({ id: "b", title: "B", tags: ["normal"] })
    const result = engine.findByTag("important")
    expect(result.nodes).toHaveLength(1)
  })

  it("finds by source", () => {
    addNode({ id: "a", title: "A", source: "api" })
    addNode({ id: "b", title: "B", source: "user" })
    const result = engine.findBySource("api")
    expect(result.nodes).toHaveLength(1)
  })

  it("searches by keyword", () => {
    addNode({ id: "a", title: "Hello World" })
    addNode({ id: "b", title: "Something Else" })
    const result = engine.searchByKeyword("hello")
    expect(result.nodes).toHaveLength(1)
  })

  it("applies sorting", () => {
    addNode({ id: "a", title: "A", importance: 1 })
    addNode({ id: "b", title: "B", importance: 5 })
    addNode({ id: "c", title: "C", importance: 3 })
    const result = engine.execute({ options: { sortField: "importance", sortOrder: "desc" } })
    expect(result.nodes[0].importance).toBe(5)
    expect(result.nodes[1].importance).toBe(3)
    expect(result.nodes[2].importance).toBe(1)
  })

  it("applies ascending sort", () => {
    addNode({ id: "a", title: "A", importance: 5 })
    addNode({ id: "b", title: "B", importance: 1 })
    const result = engine.execute({ options: { sortField: "importance", sortOrder: "asc" } })
    expect(result.nodes[0].importance).toBe(1)
    expect(result.nodes[1].importance).toBe(5)
  })

  it("applies pagination", () => {
    for (let i = 0; i < 10; i++) {
      addNode({ id: `node_${i}`, title: `Node ${i}` })
    }
    const result = engine.execute({ options: { limit: 3, offset: 0 } })
    expect(result.nodes).toHaveLength(3)
  })

  it("filters by type", () => {
    addNode({ id: "a", title: "A", type: "type:a" })
    addNode({ id: "b", title: "B", type: "type:b" })
    const result = engine.execute({ filters: { types: ["type:a"] }, options: {} })
    expect(result.nodes).toHaveLength(1)
  })

  it("filters by date range", () => {
    const now = Date.now()
    addNode({ id: "old", title: "Old", createdAt: now - 100000 })
    addNode({ id: "new", title: "New", createdAt: now })
    const result = engine.execute({ filters: { dateFrom: now - 50000 }, options: {} })
    expect(result.nodes).toHaveLength(1)
    expect(result.nodes[0].title).toBe("New")
  })

  it("filters by importance range", () => {
    addNode({ id: "low", title: "Low", importance: 2 })
    addNode({ id: "high", title: "High", importance: 8 })
    const result = engine.execute({ filters: { importanceMin: 5 }, options: {} })
    expect(result.nodes).toHaveLength(1)
    expect(result.nodes[0].title).toBe("High")
  })

  it("filters by confidence", () => {
    addNode({ id: "low", title: "LowConf", confidence: 0.3 })
    addNode({ id: "high", title: "HighConf", confidence: 0.9 })
    const result = engine.execute({ filters: { confidenceMin: 0.5 }, options: {} })
    expect(result.nodes).toHaveLength(1)
  })

  it("filters by status", () => {
    addNode({ id: "active", title: "Active" })
    addNode({ id: "archived", title: "Archived", status: "archived" })
    const result = engine.execute({ filters: { statuses: ["active"] }, options: {} })
    expect(result.nodes).toHaveLength(1)
  })

  it("filters by pinned", () => {
    addNode({ id: "pinned", title: "Pinned", pinned: true })
    addNode({ id: "not", title: "Not Pinned" })
    const result = engine.execute({ filters: { pinned: true }, options: {} })
    expect(result.nodes).toHaveLength(1)
  })

  it("filters by archived", () => {
    addNode({ id: "arch", title: "Archived", archived: true })
    addNode({ id: "active", title: "Active" })
    const result = engine.execute({ filters: { archived: false }, options: {} })
    expect(result.nodes).toHaveLength(1)
  })

  it("filters by source", () => {
    addNode({ id: "api", title: "From API", source: "api" })
    addNode({ id: "user", title: "From User", source: "user" })
    const result = engine.execute({ filters: { sources: ["api"] }, options: {} })
    expect(result.nodes).toHaveLength(1)
  })

  it("filters by superTypes", () => {
    addNode({ id: "a1", title: "Action", type: "action:exec" })
    addNode({ id: "o1", title: "Observation", type: "observation:cap" })
    const result = engine.execute({ filters: { superTypes: ["action"] }, options: {} })
    expect(result.nodes).toHaveLength(1)
  })

  it("handles empty keyword search returning no results", () => {
    addNode({ id: "a", title: "A" })
    addNode({ id: "b", title: "B" })
    const result = engine.execute({ keyword: "", options: {} })
    expect(result.nodes).toHaveLength(0)
  })

  it("handles whitespace-only keyword returning no results", () => {
    addNode({ id: "a", title: "A" })
    const result = engine.execute({ keyword: "   ", options: {} })
    expect(result.nodes).toHaveLength(0)
  })
})
