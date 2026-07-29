import { describe, it, expect } from "vitest"
import { NodeTypeRegistry } from "../registry/NodeTypeRegistry"
import { EdgeTypeRegistry } from "../registry/EdgeTypeRegistry"
import { MemoryRegistry, getMemoryRegistry, resetMemoryRegistry, setMemoryRegistry } from "../registry/MemoryRegistry"
import type { NodeTypeDefinition, EdgeTypeDefinition, MemoryProvider, NodeId } from "../types"

describe("NodeTypeRegistry", () => {
  it("registers and retrieves a node type", () => {
    const reg = new NodeTypeRegistry()
    const def: NodeTypeDefinition = {
      name: "test:node",
      superType: "action",
      description: "A test node type",
      allowedEdgeTypes: ["contains"],
      allowedAsTargetFor: ["contains"],
      defaultMetadata: {},
    }
    reg.register(def)
    expect(reg.get("test:node")).toEqual(def)
    expect(reg.has("test:node")).toBe(true)
    expect(reg.count()).toBe(1)
  })

  it("does not overwrite existing registrations", () => {
    const reg = new NodeTypeRegistry()
    reg.register({
      name: "test:node",
      superType: "action",
      description: "First",
      allowedEdgeTypes: [],
      allowedAsTargetFor: [],
      defaultMetadata: {},
    })
    reg.register({
      name: "test:node",
      superType: "observation",
      description: "Second",
      allowedEdgeTypes: [],
      allowedAsTargetFor: [],
      defaultMetadata: {},
    })
    expect(reg.get("test:node")!.description).toBe("First")
  })

  it("registers multiple types at once", () => {
    const reg = new NodeTypeRegistry()
    reg.registerMany([
      { name: "a", superType: "action", description: "A", allowedEdgeTypes: [], allowedAsTargetFor: [], defaultMetadata: {} },
      { name: "b", superType: "action", description: "B", allowedEdgeTypes: [], allowedAsTargetFor: [], defaultMetadata: {} },
    ])
    expect(reg.count()).toBe(2)
  })

  it("returns all registered types", () => {
    const reg = new NodeTypeRegistry()
    reg.registerMany([
      { name: "a", superType: "action", description: "A", allowedEdgeTypes: [], allowedAsTargetFor: [], defaultMetadata: {} },
      { name: "b", superType: "knowledge", description: "B", allowedEdgeTypes: [], allowedAsTargetFor: [], defaultMetadata: {} },
    ])
    expect(reg.getAll()).toHaveLength(2)
    expect(reg.getBySuperType("action")).toHaveLength(1)
    expect(reg.getBySuperType("knowledge")).toHaveLength(1)
  })

  it("checks allowed edge types", () => {
    const reg = new NodeTypeRegistry()
    reg.register({
      name: "test:node",
      superType: "action",
      description: "Test",
      allowedEdgeTypes: ["contains", "references"],
      allowedAsTargetFor: [],
      defaultMetadata: {},
    })
    expect(reg.getAllowedEdgeTypes("test:node")).toEqual(["contains", "references"])
    expect(reg.isAllowedEdgeType("test:node", "contains")).toBe(true)
    expect(reg.isAllowedEdgeType("test:node", "unknown")).toBe(false)
    expect(reg.isAllowedEdgeType("unknown", "contains")).toBe(false)
  })

  it("validates node IDs based on registered types", () => {
    const reg = new NodeTypeRegistry()
    reg.register({
      name: "valid:type",
      superType: "action",
      description: "Valid",
      allowedEdgeTypes: [],
      allowedAsTargetFor: [],
      defaultMetadata: {},
    })
    expect(reg.validateNodeId({ value: "1", type: "valid:type" })).toBe(true)
    expect(reg.validateNodeId({ value: "1", type: "invalid:type" })).toBe(false)
  })

  it("returns default metadata", () => {
    const reg = new NodeTypeRegistry()
    reg.register({
      name: "test:node",
      superType: "action",
      description: "Test",
      allowedEdgeTypes: [],
      allowedAsTargetFor: [],
      defaultMetadata: { key: "value", num: 42 },
    })
    expect(reg.getDefaultMetadata("test:node")).toEqual({ key: "value", num: 42 })
    expect(reg.getDefaultMetadata("unknown")).toEqual({})
  })

  it("clears all registrations", () => {
    const reg = new NodeTypeRegistry()
    reg.register({ name: "a", superType: "action", description: "A", allowedEdgeTypes: [], allowedAsTargetFor: [], defaultMetadata: {} })
    reg.clear()
    expect(reg.count()).toBe(0)
  })
})

describe("EdgeTypeRegistry", () => {
  it("registers and retrieves an edge type", () => {
    const reg = new EdgeTypeRegistry()
    const def: EdgeTypeDefinition = {
      name: "contains",
      description: "Contains relationship",
      allowedSourceTypes: ["*"],
      allowedTargetTypes: ["*"],
      directional: true,
      defaultMetadata: {},
    }
    reg.register(def)
    expect(reg.get("contains")).toEqual(def)
    expect(reg.has("contains")).toBe(true)
    expect(reg.count()).toBe(1)
  })

  it("validates connections", () => {
    const reg = new EdgeTypeRegistry()
    reg.register({
      name: "produces",
      description: "Produces",
      allowedSourceTypes: ["action:execution"],
      allowedTargetTypes: ["artifact:file"],
      directional: true,
      defaultMetadata: {},
    })
    expect(reg.canConnect("action:execution", "produces", "artifact:file")).toBe(true)
    expect(reg.canConnect("unknown", "produces", "artifact:file")).toBe(false)
    expect(reg.canConnect("action:execution", "produces", "unknown")).toBe(false)
    expect(reg.canConnect("action:execution", "unknown", "artifact:file")).toBe(false)
  })

  it("returns allowed source/target types", () => {
    const reg = new EdgeTypeRegistry()
    reg.register({
      name: "references",
      description: "References",
      allowedSourceTypes: ["*"],
      allowedTargetTypes: ["knowledge:*"],
      directional: true,
      defaultMetadata: {},
    })
    expect(reg.getAllowedSourceTypes("references")).toEqual(["*"])
    expect(reg.getAllowedTargetTypes("references")).toEqual(["knowledge:*"])
  })

  it("checks directionality", () => {
    const reg = new EdgeTypeRegistry()
    reg.register({
      name: "related_to",
      description: "Related to",
      allowedSourceTypes: ["*"],
      allowedTargetTypes: ["*"],
      directional: false,
      defaultMetadata: {},
    })
    expect(reg.isDirectional("related_to")).toBe(false)
    expect(reg.isDirectional("unknown")).toBe(true) // default
  })

  it("registers multiple types at once", () => {
    const reg = new EdgeTypeRegistry()
    reg.registerMany([
      { name: "a", description: "A", allowedSourceTypes: [], allowedTargetTypes: [], directional: true, defaultMetadata: {} },
      { name: "b", description: "B", allowedSourceTypes: [], allowedTargetTypes: [], directional: false, defaultMetadata: {} },
    ])
    expect(reg.count()).toBe(2)
  })

  it("returns all registered types", () => {
    const reg = new EdgeTypeRegistry()
    reg.registerMany([
      { name: "x", description: "X", allowedSourceTypes: [], allowedTargetTypes: [], directional: true, defaultMetadata: {} },
      { name: "y", description: "Y", allowedSourceTypes: [], allowedTargetTypes: [], directional: true, defaultMetadata: {} },
    ])
    expect(reg.getAll()).toHaveLength(2)
  })

  it("clears all registrations", () => {
    const reg = new EdgeTypeRegistry()
    reg.register({ name: "a", description: "A", allowedSourceTypes: [], allowedTargetTypes: [], directional: true, defaultMetadata: {} })
    reg.clear()
    expect(reg.count()).toBe(0)
  })
})

describe("MemoryRegistry", () => {
  it("creates registry with defaults", () => {
    const reg = new MemoryRegistry()
    expect(reg.nodeTypes).toBeInstanceOf(NodeTypeRegistry)
    expect(reg.edgeTypes).toBeInstanceOf(EdgeTypeRegistry)
    expect(reg.count()).toEqual({ nodeTypes: 0, edgeTypes: 0, providers: 0 })
  })

  it("registers node and edge types", () => {
    const reg = new MemoryRegistry()
    reg.registerNodeType({ name: "test:node", superType: "action", description: "Test", allowedEdgeTypes: ["contains"], allowedAsTargetFor: [], defaultMetadata: {} })
    reg.registerEdgeType({ name: "contains", description: "Contains", allowedSourceTypes: ["*"], allowedTargetTypes: ["*"], directional: true, defaultMetadata: {} })
    expect(reg.count().nodeTypes).toBe(1)
    expect(reg.count().edgeTypes).toBe(1)
  })

  it("validates node type completeness", () => {
    const reg = new MemoryRegistry()
    reg.registerNodeType({ name: "test:node", superType: "action", description: "Test", allowedEdgeTypes: ["contains"], allowedAsTargetFor: [], defaultMetadata: {} })
    reg.registerEdgeType({ name: "contains", description: "Contains", allowedSourceTypes: ["*"], allowedTargetTypes: ["*"], directional: true, defaultMetadata: {} })
    expect(reg.validateNodeType("test:node")).toBe(true)
    expect(reg.validateNodeType("unknown")).toBe(false)
  })

  it("checks edge connections across registries", () => {
    const reg = new MemoryRegistry()
    reg.registerNodeType({ name: "source:type", superType: "action", description: "Source", allowedEdgeTypes: ["connects"], allowedAsTargetFor: [], defaultMetadata: {} })
    reg.registerNodeType({ name: "target:type", superType: "observation", description: "Target", allowedEdgeTypes: [], allowedAsTargetFor: ["connects"], defaultMetadata: {} })
    reg.registerEdgeType({ name: "connects", description: "Connects", allowedSourceTypes: ["source:type"], allowedTargetTypes: ["target:type"], directional: true, defaultMetadata: {} })

    const sourceId: NodeId = { value: "1", type: "source:type" }
    const targetId: NodeId = { value: "2", type: "target:type" }
    expect(reg.canConnect(sourceId, "connects", targetId)).toBe(true)
    expect(reg.canConnect(targetId, "connects", sourceId)).toBe(false)
  })

  it("manages providers", () => {
    const reg = new MemoryRegistry()
    const provider: MemoryProvider = {
      name: "test-provider",
      registerTypes: () => {},
      canHandleNode: () => true,
      canHandleEdge: () => true,
      validate: () => [],
    }
    reg.registerProvider(provider)
    expect(reg.getProvider("test-provider")).toBe(provider)
    expect(reg.getProviders()).toHaveLength(1)
  })

  it("initializes providers", () => {
    const reg = new MemoryRegistry()
    let initialized = false
    reg.registerProvider({
      name: "init-test",
      registerTypes: () => { initialized = true },
      canHandleNode: () => true,
      canHandleEdge: () => true,
      validate: () => [],
    })
    reg.initialize()
    expect(initialized).toBe(true)
    expect(reg.isInitialized()).toBe(true)
  })

  it("does not re-initialize", () => {
    const reg = new MemoryRegistry()
    let count = 0
    reg.registerProvider({
      name: "count-test",
      registerTypes: () => { count++ },
      canHandleNode: () => true,
      canHandleEdge: () => true,
      validate: () => [],
    })
    reg.initialize()
    reg.initialize()
    expect(count).toBe(1)
  })

  it("validates all providers", () => {
    const reg = new MemoryRegistry()
    reg.registerProvider({
      name: "faulty",
      registerTypes: () => {},
      canHandleNode: () => true,
      canHandleEdge: () => true,
      validate: () => ["error1", "error2"],
    })
    const errors = reg.validateAll()
    expect(errors).toEqual(["[faulty] error1", "[faulty] error2"])
  })

  it("resets registry", () => {
    const reg = new MemoryRegistry()
    reg.registerNodeType({ name: "test", superType: "action", description: "Test", allowedEdgeTypes: [], allowedAsTargetFor: [], defaultMetadata: {} })
    reg.initialize()
    reg.reset()
    expect(reg.count().nodeTypes).toBe(0)
    expect(reg.isInitialized()).toBe(false)
  })

  describe("singleton access", () => {
    it("gets/sets/resets default registry", () => {
      resetMemoryRegistry()
      const reg = getMemoryRegistry()
      expect(reg).toBeInstanceOf(MemoryRegistry)

      const newReg = new MemoryRegistry()
      setMemoryRegistry(newReg)
      expect(getMemoryRegistry()).toBe(newReg)

      resetMemoryRegistry()
      expect(getMemoryRegistry()).not.toBe(newReg)
    })
  })
})
