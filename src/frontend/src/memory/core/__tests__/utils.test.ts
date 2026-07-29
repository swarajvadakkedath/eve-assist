import { describe, it, expect, beforeAll } from "vitest"
import { MemoryValidation } from "../utils/MemoryValidation"
import { NodeTypeRegistry } from "../registry/NodeTypeRegistry"
import { EdgeTypeRegistry } from "../registry/EdgeTypeRegistry"
import {
  nodeKey,
  nodesMatch,
  findNodeById,
  findEdgesByNodeId,
  filterActiveNodes,
  filterArchivedNodes,
  filterPinnedNodes,
  filterBySuperType,
  filterByTag,
  filterByTags,
  sortByRecent,
  sortByImportance,
  sortByField,
  paginate,
  groupByType,
  groupBySuperType,
  formatTimestamp,
  isStale,
  calculateAverageImportance,
  calculateAverageConfidence,
} from "../utils/GraphUtils"
import type { MemoryNode, MemoryEdge, NodeId } from "../types"

function makeNode(id: string, overrides: Partial<MemoryNode> = {}): MemoryNode {
  return {
    id: { value: id, type: "test:node" },
    type: "test:node",
    subtype: "test",
    title: `Node ${id}`,
    summary: "",
    createdAt: 1000,
    updatedAt: 2000,
    lastAccessed: 1500,
    source: "test",
    metadata: {},
    tags: [],
    importance: 1,
    confidence: 1,
    accessCount: 0,
    pinned: false,
    archived: false,
    verified: false,
    verificationMethod: "",
    status: "active",
    ...overrides,
  }
}

function makeEdge(sourceId: NodeId, targetId: NodeId, type = "contains"): MemoryEdge {
  return {
    id: { value: "e1" },
    sourceNodeId: sourceId,
    targetNodeId: targetId,
    type,
    strength: 1,
    weight: 1,
    metadata: {},
    createdAt: 1000,
  }
}

describe("MemoryValidation", () => {
  const nodeReg = new NodeTypeRegistry()
  const edgeReg = new EdgeTypeRegistry()
  const validator = new MemoryValidation(nodeReg, edgeReg)

  beforeAll(() => {
    nodeReg.register({
      name: "test:node",
      superType: "action",
      description: "Test node type",
      allowedEdgeTypes: ["contains"],
      allowedAsTargetFor: [],
      defaultMetadata: {},
    })
    edgeReg.register({
      name: "contains",
      description: "Contains relationship",
      allowedSourceTypes: ["test:node"],
      allowedTargetTypes: ["test:node"],
      directional: true,
      defaultMetadata: {},
    })
  })

  describe("validateNode", () => {
    it("validates a correct node", () => {
      const node = makeNode("1", {
        type: "test:node",
        title: "Valid Node",
        source: "test",
        importance: 5,
        confidence: 0.8,
      })
      const errors = validator.validateNode(node)
      expect(errors).toHaveLength(0)
    })

    it("catches missing title", () => {
      const node = makeNode("1", { type: "test:node", title: "" })
      const errors = validator.validateNode(node)
      expect(errors.some((e) => e.code === "MISSING_TITLE")).toBe(true)
    })

    it("catches missing source", () => {
      const node = makeNode("1", { source: "" })
      const errors = validator.validateNode(node)
      expect(errors.some((e) => e.code === "MISSING_SOURCE")).toBe(true)
    })

    it("catches unknown node type", () => {
      const node = makeNode("1", { type: "unknown:type" })
      const errors = validator.validateNode(node)
      expect(errors.some((e) => e.code === "UNKNOWN_NODE_TYPE")).toBe(true)
    })

    it("catches invalid importance", () => {
      const node = makeNode("1", { type: "test:node", importance: 15 })
      const errors = validator.validateNode(node)
      expect(errors.some((e) => e.code === "INVALID_IMPORTANCE")).toBe(true)
    })

    it("catches invalid confidence", () => {
      const node = makeNode("1", { type: "test:node", confidence: 1.5 })
      const errors = validator.validateNode(node)
      expect(errors.some((e) => e.code === "INVALID_CONFIDENCE")).toBe(true)
    })

    it("catches future createdAt", () => {
      const node = makeNode("1", { type: "test:node", createdAt: Date.now() + 5000 })
      const errors = validator.validateNode(node)
      expect(errors.some((e) => e.code === "FUTURE_CREATED_AT")).toBe(true)
    })

    it("catches archived and pinned", () => {
      const node = makeNode("1", { type: "test:node", archived: true, pinned: true })
      const errors = validator.validateNode(node)
      expect(errors.some((e) => e.code === "ARCHIVED_AND_PINNED")).toBe(true)
    })
  })

  describe("validateNodeInput", () => {
    it("validates a correct input", () => {
      const errors = validator.validateNodeInput({
        type: "test:node",
        subtype: "test",
        title: "Test",
        source: "test",
      })
      expect(errors).toHaveLength(0)
    })

    it("catches missing type", () => {
      const errors = validator.validateNodeInput({
        type: "",
        subtype: "test",
        title: "Test",
        source: "test",
      })
      expect(errors.some((e) => e.code === "MISSING_TYPE")).toBe(true)
    })

    it("catches invalid importance range", () => {
      const errors = validator.validateNodeInput({
        type: "test:node",
        subtype: "test",
        title: "Test",
        source: "test",
        importance: -1,
      })
      expect(errors.some((e) => e.code === "INVALID_IMPORTANCE")).toBe(true)
    })
  })

  describe("validateEdge", () => {
    it("validates a correct edge", () => {
      const sourceId: NodeId = { value: "1", type: "test:node" }
      const targetId: NodeId = { value: "2", type: "test:node" }
      const edge = makeEdge(sourceId, targetId, "contains")
      const errors = validator.validateEdge(edge)
      expect(errors).toHaveLength(0)
    })

    it("catches invalid strength", () => {
      const edge = makeEdge(
        { value: "1", type: "test:node" },
        { value: "2", type: "test:node" },
        "contains",
      )
      const badEdge = { ...edge, strength: 1.5 }
      const errors = validator.validateEdge(badEdge)
      expect(errors.some((e) => e.code === "INVALID_STRENGTH")).toBe(true)
    })

    it("catches unknown edge type", () => {
      const edge = makeEdge(
        { value: "1", type: "test:node" },
        { value: "2", type: "test:node" },
        "unknown",
      )
      const errors = validator.validateEdge(edge)
      expect(errors.some((e) => e.code === "UNKNOWN_EDGE_TYPE")).toBe(true)
    })
  })

  describe("validateEdgeInput", () => {
    it("validates a correct input", () => {
      const errors = validator.validateEdgeInput({
        sourceNodeId: { value: "1", type: "test:node" },
        targetNodeId: { value: "2", type: "test:node" },
        type: "contains",
      })
      expect(errors).toHaveLength(0)
    })

    it("catches missing type", () => {
      const errors = validator.validateEdgeInput({
        sourceNodeId: { value: "1", type: "test:node" },
        targetNodeId: { value: "2", type: "test:node" },
        type: "",
      })
      expect(errors.some((e) => e.code === "MISSING_EDGE_TYPE")).toBe(true)
    })
  })

  describe("range validators", () => {
    it("validates importance range", () => {
      expect(validator.isValidImportance(5)).toBe(true)
      expect(validator.isValidImportance(-1)).toBe(false)
      expect(validator.isValidImportance(11)).toBe(false)
    })

    it("validates confidence range", () => {
      expect(validator.isValidConfidence(0.5)).toBe(true)
      expect(validator.isValidConfidence(-0.1)).toBe(false)
      expect(validator.isValidConfidence(1.1)).toBe(false)
    })

    it("validates strength range", () => {
      expect(validator.isValidStrength(0.5)).toBe(true)
      expect(validator.isValidStrength(-0.1)).toBe(false)
      expect(validator.isValidStrength(1.1)).toBe(false)
    })

    it("validates weight range", () => {
      expect(validator.isValidWeight(0.5)).toBe(true)
      expect(validator.isValidWeight(-0.1)).toBe(false)
      expect(validator.isValidWeight(1.1)).toBe(false)
    })
  })
})

describe("GraphUtils", () => {
  const aId: NodeId = { value: "a", type: "test:node" }
  const bId: NodeId = { value: "b", type: "test:node" }
  const cId: NodeId = { value: "c", type: "other:type" }

  const nodeA = makeNode("a")
  const nodeB = makeNode("b", { archived: true })
  const nodeC = makeNode("c", { pinned: true, tags: ["important"] })
  const nodeD = makeNode("d", { type: "action:exec", tags: ["action", "test"] })

  const nodes = [nodeA, nodeB, nodeC, nodeD]

  describe("nodeKey", () => {
    it("creates composite key", () => {
      expect(nodeKey(aId)).toBe("test:node:a")
    })
  })

  describe("nodesMatch", () => {
    it("matches same node", () => {
      expect(nodesMatch(aId, aId)).toBe(true)
    })
    it("does not match different nodes", () => {
      expect(nodesMatch(aId, bId)).toBe(false)
    })
  })

  describe("findNodeById", () => {
    it("finds a node by ID", () => {
      expect(findNodeById(nodes, aId)).toBe(nodeA)
    })
    it("returns undefined for missing", () => {
      expect(findNodeById(nodes, { value: "missing", type: "test" })).toBeUndefined()
    })
  })

  describe("findEdgesByNodeId", () => {
    it("finds edges for a node", () => {
      const edges = [makeEdge(aId, bId), makeEdge(bId, cId)]
      expect(findEdgesByNodeId(edges, aId)).toHaveLength(1)
      expect(findEdgesByNodeId(edges, bId)).toHaveLength(2)
    })
  })

  describe("filterActiveNodes", () => {
    it("filters out archived nodes", () => {
      const active = filterActiveNodes(nodes)
      expect(active).toHaveLength(3)
      expect(active.find((n) => n.archived)).toBeUndefined()
    })
  })

  describe("filterArchivedNodes", () => {
    it("returns only archived nodes", () => {
      const archived = filterArchivedNodes(nodes)
      expect(archived).toHaveLength(1)
      expect(archived[0].id.value).toBe("b")
    })
  })

  describe("filterPinnedNodes", () => {
    it("returns pinned nodes excluding archived", () => {
      const pinned = filterPinnedNodes(nodes)
      expect(pinned).toHaveLength(1)
      expect(pinned[0].id.value).toBe("c")
    })
  })

  describe("filterBySuperType", () => {
    it("filters by super type", () => {
      const action = filterBySuperType(nodes, "action")
      expect(action).toHaveLength(1)
    })
  })

  describe("filterByTag", () => {
    it("filters by single tag", () => {
      expect(filterByTag(nodes, "important")).toHaveLength(1)
      expect(filterByTag(nodes, "nonexistent")).toHaveLength(0)
    })
  })

  describe("filterByTags", () => {
    it("filters with any mode", () => {
      expect(filterByTags(nodes, ["important", "action"], "any")).toHaveLength(2)
    })
    it("filters with all mode", () => {
      expect(filterByTags(nodes, ["action", "test"], "all")).toHaveLength(1)
    })
  })

  describe("sortByRecent", () => {
    it("sorts by updatedAt descending", () => {
      const sorted = sortByRecent(nodes)
      expect(sorted[0].updatedAt).toBeGreaterThanOrEqual(sorted[1].updatedAt)
    })
  })

  describe("sortByImportance", () => {
    it("sorts by importance descending", () => {
      const sorted = sortByImportance(nodes)
      expect(sorted[0].importance).toBeGreaterThanOrEqual(sorted[1].importance)
    })
  })

  describe("sortByField", () => {
    it("sorts by field asc/desc", () => {
      const asc = sortByField(nodes, "createdAt", "asc")
      const desc = sortByField(nodes, "createdAt", "desc")
      expect(asc[0].createdAt).toBeLessThanOrEqual(asc[1].createdAt)
      expect(desc[0].createdAt).toBeGreaterThanOrEqual(desc[1].createdAt)
    })
  })

  describe("paginate", () => {
    it("applies offset and limit", () => {
      const items = [1, 2, 3, 4, 5]
      expect(paginate(items, 1, 2)).toEqual([2, 3])
      expect(paginate(items, 0, 10)).toEqual([1, 2, 3, 4, 5])
      expect(paginate(items, 10)).toEqual([])
    })
  })

  describe("groupByType", () => {
    it("groups nodes by type", () => {
      const grouped = groupByType(nodes)
      expect(grouped["test:node"]).toHaveLength(3)
      expect(grouped["action:exec"]).toHaveLength(1)
    })
  })

  describe("groupBySuperType", () => {
    it("groups by super type", () => {
    const grouped = groupBySuperType(nodes) as Record<string, MemoryNode[]>
    expect(grouped["test"]).toHaveLength(3)
    expect(grouped["action"]).toHaveLength(1)
    })
  })

  describe("formatTimestamp", () => {
    it("formats timestamp to ISO string", () => {
      const formatted = formatTimestamp(0)
      expect(formatted).toBe("1970-01-01T00:00:00.000Z")
    })
  })

  describe("isStale", () => {
    it("checks if node is stale", () => {
      const freshNode = makeNode("fresh", { updatedAt: Date.now() })
      expect(isStale(freshNode, 100000)).toBe(false)
      const staleNode = makeNode("old", { updatedAt: 1000 })
      expect(isStale(staleNode, 100)).toBe(true)
    })
  })

  describe("calculateAverageImportance", () => {
    it("calculates average", () => {
      expect(calculateAverageImportance(nodes)).toBe(1) // all have importance 1
      expect(calculateAverageImportance([])).toBe(0)
    })
  })

  describe("calculateAverageConfidence", () => {
    it("calculates average", () => {
      expect(calculateAverageConfidence(nodes)).toBe(1) // all have confidence 1
      expect(calculateAverageConfidence([])).toBe(0)
    })
  })
})
