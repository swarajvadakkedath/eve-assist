import type { MemoryNode, MemoryEdge, NodeId, EdgeInput, ValidationError, CircularDependency } from "../types"
import type { MemoryGraph } from "./MemoryGraph"
import type { MemoryRegistry } from "../registry/MemoryRegistry"
import { GraphTraversal } from "./GraphTraversal"

export class RelationshipEngine {
  private graph: MemoryGraph
  private registry: MemoryRegistry
  private traversal: GraphTraversal

  constructor(graph: MemoryGraph, registry: MemoryRegistry) {
    this.graph = graph
    this.registry = registry
    this.traversal = new GraphTraversal(graph)
  }

  canAddEdge(input: EdgeInput): { valid: boolean; errors: readonly ValidationError[] } {
    const errors: ValidationError[] = []

    const sourceNode = this.graph.getNodeById(input.sourceNodeId)
    const targetNode = this.graph.getNodeById(input.targetNodeId)

    if (!sourceNode) {
      errors.push({
        code: "SOURCE_NODE_NOT_FOUND",
        message: `Source node ${input.sourceNodeId.type}:${input.sourceNodeId.value} not found`,
        nodeId: input.sourceNodeId,
      })
    }

    if (!targetNode) {
      errors.push({
        code: "TARGET_NODE_NOT_FOUND",
        message: `Target node ${input.targetNodeId.type}:${input.targetNodeId.value} not found`,
        nodeId: input.targetNodeId,
      })
    }

    if (!sourceNode || !targetNode) {
      return { valid: errors.length === 0, errors }
    }

    if (!this.registry.edgeTypes.has(input.type)) {
      errors.push({
        code: "UNKNOWN_EDGE_TYPE",
        message: `Edge type '${input.type}' is not registered`,
        field: "type",
      })
      return { valid: false, errors }
    }

    if (!this.registry.edgeTypes.canConnect(sourceNode.type, input.type, targetNode.type)) {
      errors.push({
        code: "INVALID_EDGE_CONNECTION",
        message: `Edge type '${input.type}' cannot connect node type '${sourceNode.type}' to '${targetNode.type}'`,
      })
    }

    const edgeDef = this.registry.edgeTypes.get(input.type)
    if (edgeDef) {
      if (input.strength !== undefined && (input.strength < 0 || input.strength > 1)) {
        errors.push({
          code: "INVALID_STRENGTH",
          message: "Edge strength must be between 0 and 1",
          field: "strength",
        })
      }
      if (input.weight !== undefined && (input.weight < 0 || input.weight > 1)) {
        errors.push({
          code: "INVALID_WEIGHT",
          message: "Edge weight must be between 0 and 1",
          field: "weight",
        })
      }
    }

    const cycle = this.wouldCreateCycle(input.sourceNodeId, input.targetNodeId)
    if (cycle) {
      errors.push({
        code: "CIRCULAR_DEPENDENCY",
        message: `Adding this edge would create a circular dependency`,
        nodeId: input.sourceNodeId,
        edgeId: cycle.edge?.id,
      })
    }

    return { valid: errors.length === 0, errors }
  }

  addEdge(input: EdgeInput): MemoryEdge | undefined {
    const { valid } = this.canAddEdge(input)
    if (!valid) return undefined
    return this.graph.addEdge(input)
  }

  deleteNodeWithEdges(id: NodeId): boolean {
    const edges = this.graph.getConnectedEdges(id)
    for (const edge of [...edges.outgoing, ...edges.incoming]) {
      this.graph.deleteEdge(edge.id)
    }
    return this.graph.deleteNode(id)
  }

  getConnectedComponent(id: NodeId): { nodes: readonly MemoryNode[]; edges: readonly MemoryEdge[] } {
    return this.traversal.getConnectedComponent(id)
  }

  validateGraph(): readonly ValidationError[] {
    const errors: ValidationError[] = []
    const nodes = this.graph.getAllNodes()

    for (const node of nodes) {
      if (!this.registry.nodeTypes.isValidNodeType(node.type)) {
        errors.push({
          code: "INVALID_NODE_TYPE",
          message: `Node type '${node.type}' is not registered`,
          nodeId: node.id,
          field: "type",
        })
      }
    }

    const cycles = this.findCycles()
    for (const cycle of cycles) {
      errors.push({
        code: "CIRCULAR_DEPENDENCY",
        message: "Circular dependency detected in the graph",
        nodeId: cycle.path[0],
        edgeId: cycle.edge?.id,
      })
    }

    return errors
  }

  findCycles(): readonly CircularDependency[] {
    const cycles: CircularDependency[] = []
    const visited = new Set<string>()
    const inStack = new Set<string>()
    const nodes = this.graph.getAllNodes()

    const dfs = (nodeId: NodeId, path: NodeId[]): boolean => {
      const key = this.nodeKey(nodeId)
      if (inStack.has(key)) {
        const cycleStart = path.findIndex((n) => this.nodeKey(n) === key)
        if (cycleStart >= 0) {
          const cyclePath = path.slice(cycleStart)
          const edges = this.getPathEdges(cyclePath)
          cycles.push({ path: cyclePath, edge: edges[0] })
        }
        return true
      }
      if (visited.has(key)) return false

      visited.add(key)
      inStack.add(key)

      const outgoing = this.graph.getOutgoingNeighbors(nodeId)
      for (const neighbor of outgoing) {
        dfs(neighbor.id, [...path, neighbor.id])
      }

      inStack.delete(key)
      return false
    }

    for (const node of nodes) {
      if (!visited.has(this.nodeKey(node.id))) {
        dfs(node.id, [node.id])
      }
    }

    return cycles
  }

  wouldCreateCycle(sourceId: NodeId, targetId: NodeId): CircularDependency | undefined {
    if (this.nodeKey(sourceId) === this.nodeKey(targetId)) {
      return { path: [sourceId], edge: undefined as unknown as MemoryEdge }
    }

    const traversal = new GraphTraversal(this.graph)
    const paths = traversal.findPaths(targetId, sourceId, { maxDepth: 50 })
    if (paths.length > 0) {
      const firstPath = paths[0]
      return {
        path: firstPath.path ?? [],
        edge: firstPath.edges[0],
      }
    }
    return undefined
  }

  getRelationshipSummary(id: NodeId): {
    node: MemoryNode | undefined
    outgoingCount: number
    incomingCount: number
    totalConnections: number
    connectedTypes: Record<string, number>
  } {
    const node = this.graph.getNodeById(id)
    if (!node) {
      return { node: undefined, outgoingCount: 0, incomingCount: 0, totalConnections: 0, connectedTypes: {} }
    }

    const connected = this.graph.getNeighbors(id)
    const connectedTypes: Record<string, number> = {}
    for (const n of connected) {
      connectedTypes[n.type] = (connectedTypes[n.type] ?? 0) + 1
    }

    return {
      node,
      outgoingCount: this.graph.getOutgoingEdges(id).length,
      incomingCount: this.graph.getIncomingEdges(id).length,
      totalConnections: connected.length,
      connectedTypes,
    }
  }

  private getPathEdges(path: readonly NodeId[]): readonly MemoryEdge[] {
    const edges: MemoryEdge[] = []
    for (let i = 0; i < path.length - 1; i++) {
      const outgoing = this.graph.getOutgoingEdges(path[i])
      const match = outgoing.find((e) => this.nodeKey(e.targetNodeId) === this.nodeKey(path[i + 1]))
      if (match) edges.push(match)
    }
    return edges
  }

  private nodeKey(id: NodeId): string {
    return `${id.type}:${id.value}`
  }
}
