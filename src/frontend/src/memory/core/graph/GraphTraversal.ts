import type { MemoryNode, MemoryEdge, NodeId, EdgeDirection, TraversalResult } from "../types"
import type { MemoryGraph } from "./MemoryGraph"

export class GraphTraversal {
  constructor(private readonly graph: MemoryGraph) {}

  bfs(
    startId: NodeId,
    options: { maxDepth?: number; edgeTypes?: readonly string[] } = {},
  ): TraversalResult {
    const { maxDepth = 10, edgeTypes } = options
    const visited = new Set<string>()
    const nodes: MemoryNode[] = []
    const edges: MemoryEdge[] = []
    const queue: Array<{ id: NodeId; depth: number; path: NodeId[] }> = []
    const startKey = this.nodeKey(startId)
    const startNode = this.graph.getNode(startId)

    if (!startNode) {
      return { nodes: [], edges: [], depth: 0 }
    }

    visited.add(startKey)
    queue.push({ id: startId, depth: 0, path: [startId] })
    nodes.push(startNode)

    while (queue.length > 0) {
      const current = queue.shift()!
      if (current.depth >= maxDepth) continue

      const outEdges = this.graph.getOutgoingEdges(current.id)
      const inEdges = this.graph.getIncomingEdges(current.id)
      const allEdges = [...outEdges, ...inEdges]

      for (const edge of allEdges) {
        if (edgeTypes && !edgeTypes.includes(edge.type)) continue

        const neighborId = this.nodeKey(edge.sourceNodeId) === this.nodeKey(current.id)
          ? edge.targetNodeId
          : edge.sourceNodeId

        const neighborKey = this.nodeKey(neighborId)
        if (visited.has(neighborKey)) continue

        visited.add(neighborKey)
        edges.push(edge)
        const neighbor = this.graph.getNodeById(neighborId)
        if (neighbor) {
          nodes.push(neighbor)
          queue.push({
            id: neighborId,
            depth: current.depth + 1,
            path: [...current.path, neighborId],
          })
        }
      }
    }

    return { nodes, edges, depth: Math.min(maxDepth, nodes.length > 1 ? 1 : 0) }
  }

  dfs(
    startId: NodeId,
    options: { maxDepth?: number; edgeTypes?: readonly string[] } = {},
  ): TraversalResult {
    const { maxDepth = 10, edgeTypes } = options
    const visited = new Set<string>()
    const nodes: MemoryNode[] = []
    const edges: MemoryEdge[] = []
    const startNode = this.graph.getNode(startId)

    if (!startNode) return { nodes: [], edges: [], depth: 0 }

    const stack: Array<{ id: NodeId; depth: number; path: NodeId[] }> = []
    stack.push({ id: startId, depth: 0, path: [startId] })
    visited.add(this.nodeKey(startId))
    nodes.push(startNode)

    while (stack.length > 0) {
      const current = stack.pop()!
      if (current.depth >= maxDepth) continue

      const outEdges = this.graph.getOutgoingEdges(current.id)
      const inEdges = this.graph.getIncomingEdges(current.id)
      const allEdges = [...outEdges, ...inEdges]

      for (const edge of allEdges) {
        if (edgeTypes && !edgeTypes.includes(edge.type)) continue

        const neighborId = this.nodeKey(edge.sourceNodeId) === this.nodeKey(current.id)
          ? edge.targetNodeId
          : edge.sourceNodeId

        const neighborKey = this.nodeKey(neighborId)
        if (visited.has(neighborKey)) continue

        visited.add(neighborKey)
        edges.push(edge)
        const neighbor = this.graph.getNodeById(neighborId)
        if (neighbor) {
          nodes.push(neighbor)
          stack.push({ id: neighborId, depth: current.depth + 1, path: [...current.path, neighborId] })
        }
      }
    }

    return { nodes, edges, depth: Math.min(maxDepth, nodes.length > 1 ? 1 : 0) }
  }

  findPaths(
    startId: NodeId,
    endId: NodeId,
    options: { maxDepth?: number; edgeTypes?: readonly string[] } = {},
  ): TraversalResult[] {
    const { maxDepth = 10, edgeTypes } = options
    const results: TraversalResult[] = []
    const visited = new Set<string>()

    const dfs = (currentId: NodeId, endId: NodeId, depth: number, path: NodeId[], edges: MemoryEdge[]) => {
      const currentKey = this.nodeKey(currentId)
      if (depth > maxDepth) return
      if (visited.has(currentKey)) return

      if (this.nodeKey(currentId) === this.nodeKey(endId)) {
        const pathNodes = path
          .map((id) => this.graph.getNodeById(id))
          .filter(Boolean) as MemoryNode[]
        results.push({
          nodes: pathNodes,
          edges: [...edges],
          depth,
          path: [...path],
        })
        return
      }

      visited.add(currentKey)
      const outEdges = this.graph.getOutgoingEdges(currentId)
      const inEdges = this.graph.getIncomingEdges(currentId)

      for (const edge of [...outEdges, ...inEdges]) {
        if (edgeTypes && !edgeTypes.includes(edge.type)) continue

        const neighborId = this.nodeKey(edge.sourceNodeId) === currentKey
          ? edge.targetNodeId
          : edge.sourceNodeId

        dfs(neighborId, endId, depth + 1, [...path, neighborId], [...edges, edge])
      }

      visited.delete(currentKey)
    }

    dfs(startId, endId, 0, [startId], [])
    return results
  }

  findShortestPath(
    startId: NodeId,
    endId: NodeId,
    options: { edgeTypes?: readonly string[] } = {},
  ): TraversalResult | undefined {
    const paths = this.findPaths(startId, endId, { maxDepth: 10, ...options })
    if (paths.length === 0) return undefined

    return paths.reduce((shortest, current) =>
      current.depth < shortest.depth ? current : shortest,
    )
  }

  getConnectedComponent(startId: NodeId): TraversalResult {
    return this.bfs(startId, { maxDepth: 100 })
  }

  getNeighborsAtDepth(
    id: NodeId,
    depth: number,
    options: { edgeTypes?: readonly string[]; direction?: EdgeDirection } = {},
  ): readonly MemoryNode[] {
    if (depth === 0) {
      const node = this.graph.getNodeById(id)
      return node ? [node] : []
    }

    const result = this.bfs(id, { maxDepth: depth, edgeTypes: options.edgeTypes })
    if (depth === 1) {
      return result.nodes.filter((n) => this.nodeKey(n.id) !== this.nodeKey(id))
    }

    const depthMap = new Map<string, number>()
    depthMap.set(this.nodeKey(id), 0)

    const queue: Array<{ id: NodeId; depth: number }> = [{ id, depth: 0 }]
    while (queue.length > 0) {
      const current = queue.shift()!
      if (current.depth >= depth) continue

      for (const neighbor of this.graph.getNeighbors(current.id)) {
        const key = this.nodeKey(neighbor.id)
        if (!depthMap.has(key)) {
          depthMap.set(key, current.depth + 1)
          queue.push({ id: neighbor.id, depth: current.depth + 1 })
        }
      }
    }

    return result.nodes.filter((n) => depthMap.get(this.nodeKey(n.id)) === depth)
  }

  private nodeKey(id: NodeId): string {
    return `${id.type}:${id.value}`
  }
}
