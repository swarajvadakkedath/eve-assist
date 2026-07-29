import type {
  MemoryNode,
  MemoryEdge,
  NodeId,
  EdgeId,
  NodeInput,
  EdgeInput,
  MemorySnapshot,
  MemoryGraphStats,
  NodeSuperType,
  NodeChange,
  EdgeChange,
} from "../types"

type NodeListener = (change: NodeChange) => void
type EdgeListener = (change: EdgeChange) => void

let nodeCounter = 0
let edgeCounter = 0

function generateNodeId(type: string): NodeId {
  nodeCounter++
  return { value: `${type}_${Date.now()}_${nodeCounter}`, type }
}

function generateEdgeId(): EdgeId {
  edgeCounter++
  return { value: `edge_${Date.now()}_${edgeCounter}` }
}

export class MemoryGraph {
  private nodes = new Map<string, MemoryNode>()
  private edges = new Map<string, MemoryEdge>()
  private adjacencyOut = new Map<string, Set<string>>()
  private adjacencyIn = new Map<string, Set<string>>()
  private nodeByType = new Map<string, Set<string>>()

  private nodeListeners = new Set<NodeListener>()
  private edgeListeners = new Set<EdgeListener>()

  onNodeChange(listener: NodeListener): () => void {
    this.nodeListeners.add(listener)
    return () => this.nodeListeners.delete(listener)
  }

  onEdgeChange(listener: EdgeListener): () => void {
    this.edgeListeners.add(listener)
    return () => this.edgeListeners.delete(listener)
  }

  private notifyNode(change: NodeChange): void {
    for (const listener of this.nodeListeners) {
      listener(change)
    }
  }

  private notifyEdge(change: EdgeChange): void {
    for (const listener of this.edgeListeners) {
      listener(change)
    }
  }

  addNode(input: NodeInput): MemoryNode {
    const now = input.createdAt ?? Date.now()
    const node: MemoryNode = {
      id: input.id ? { value: input.id, type: input.type } : generateNodeId(input.type),
      type: input.type,
      subtype: input.subtype,
      title: input.title,
      summary: input.summary ?? "",
      createdAt: now,
      updatedAt: now,
      lastAccessed: now,
      source: input.source,
      metadata: (input.metadata ?? {}) as Record<string, unknown>,
      tags: input.tags ?? [],
      importance: input.importance ?? 1,
      confidence: input.confidence ?? 1,
      accessCount: 0,
      pinned: input.pinned ?? false,
      archived: input.archived ?? false,
      verified: input.verified ?? false,
      verificationMethod: input.verificationMethod ?? "",
      status: input.status ?? "active",
    }

    const key = this.nodeKey(node.id)
    this.nodes.set(key, node)
    this.addTypeIndex(node)
    this.notifyNode({ type: "created", node, timestamp: now })
    return node
  }

  updateNode(id: NodeId, partial: Partial<MemoryNode>): MemoryNode | undefined {
    const key = this.nodeKey(id)
    const existing = this.nodes.get(key)
    if (!existing) return undefined

    const now = Date.now()
    const updated: MemoryNode = {
      ...existing,
      ...partial,
      id: existing.id,
      updatedAt: now,
    }

    this.nodes.set(key, updated)
    this.notifyNode({ type: "updated", node: updated, previous: existing, timestamp: now })
    return updated
  }

  deleteNode(id: NodeId): boolean {
    const key = this.nodeKey(id)
    const existing = this.nodes.get(key)
    if (!existing) return false

    const now = Date.now()
    const outEdges = this.getOutgoingEdges(id)
    const inEdges = this.getIncomingEdges(id)

    for (const edge of [...outEdges, ...inEdges]) {
      this.removeEdgeData(edge.id)
    }

    this.nodes.delete(key)
    this.removeTypeIndex(existing)
    this.adjacencyOut.delete(key)
    this.adjacencyIn.delete(key)

    for (const edges of this.adjacencyOut.values()) {
      edges.delete(key)
    }
    for (const edges of this.adjacencyIn.values()) {
      edges.delete(key)
    }

    this.notifyNode({ type: "deleted", node: existing, timestamp: now })
    return true
  }

  getNode(id: NodeId): MemoryNode | undefined {
    const key = this.nodeKey(id)
    const node = this.nodes.get(key)
    if (node) {
      this.touchNode(id)
    }
    return node
  }

  getNodeById(id: NodeId): MemoryNode | undefined {
    return this.nodes.get(this.nodeKey(id))
  }

  hasNode(id: NodeId): boolean {
    return this.nodes.has(this.nodeKey(id))
  }

  getAllNodes(): readonly MemoryNode[] {
    return [...this.nodes.values()]
  }

  getNodesByType(type: string): readonly MemoryNode[] {
    const keys = this.nodeByType.get(type)
    if (!keys) return []
    return [...keys].map((k) => this.nodes.get(k)!).filter(Boolean)
  }

  getNodesBySuperType(superType: NodeSuperType): readonly MemoryNode[] {
    return this.getAllNodes().filter((n) => n.type.startsWith(superType))
  }

  archiveNode(id: NodeId): MemoryNode | undefined {
    const key = this.nodeKey(id)
    const existing = this.nodes.get(key)
    if (!existing) return undefined
    const now = Date.now()
    const node: MemoryNode = { ...existing, archived: true, status: "archived", updatedAt: now }
    this.nodes.set(key, node)
    this.notifyNode({ type: "archived", node, timestamp: now })
    return node
  }

  restoreNode(id: NodeId): MemoryNode | undefined {
    const key = this.nodeKey(id)
    const existing = this.nodes.get(key)
    if (!existing) return undefined
    const now = Date.now()
    const node: MemoryNode = { ...existing, archived: false, status: "active", updatedAt: now }
    this.nodes.set(key, node)
    this.notifyNode({ type: "restored", node, timestamp: now })
    return node
  }

  addEdge(input: EdgeInput): MemoryEdge | undefined {
    const sourceKey = this.nodeKey(input.sourceNodeId)
    const targetKey = this.nodeKey(input.targetNodeId)

    if (!this.nodes.has(sourceKey) || !this.nodes.has(targetKey)) {
      return undefined
    }

    const now = Date.now()
    const edge: MemoryEdge = {
      id: input.id ? { value: input.id } : generateEdgeId(),
      sourceNodeId: input.sourceNodeId,
      targetNodeId: input.targetNodeId,
      type: input.type,
      strength: input.strength ?? 1,
      weight: input.weight ?? 1,
      metadata: (input.metadata ?? {}) as Record<string, unknown>,
      createdAt: now,
    }

    this.edges.set(edge.id.value, edge)

    if (!this.adjacencyOut.has(sourceKey)) {
      this.adjacencyOut.set(sourceKey, new Set())
    }
    this.adjacencyOut.get(sourceKey)!.add(targetKey)

    if (!this.adjacencyIn.has(targetKey)) {
      this.adjacencyIn.set(targetKey, new Set())
    }
    this.adjacencyIn.get(targetKey)!.add(sourceKey)

    this.notifyEdge({ type: "created", edge, timestamp: now })
    return edge
  }

  deleteEdge(id: EdgeId): boolean {
    const edge = this.edges.get(id.value)
    if (!edge) return false
    this.removeEdgeData(id)
    return true
  }

  getEdge(id: EdgeId): MemoryEdge | undefined {
    return this.edges.get(id.value)
  }

  getEdgesByNode(id: NodeId): readonly MemoryEdge[] {
    const key = this.nodeKey(id)
    const results: MemoryEdge[] = []

    for (const edge of this.edges.values()) {
      if (this.nodeKey(edge.sourceNodeId) === key || this.nodeKey(edge.targetNodeId) === key) {
        results.push(edge)
      }
    }
    return results
  }

  getOutgoingEdges(id: NodeId): readonly MemoryEdge[] {
    const key = this.nodeKey(id)
    return [...this.edges.values()].filter((e) => this.nodeKey(e.sourceNodeId) === key)
  }

  getIncomingEdges(id: NodeId): readonly MemoryEdge[] {
    const key = this.nodeKey(id)
    return [...this.edges.values()].filter((e) => this.nodeKey(e.targetNodeId) === key)
  }

  getOutgoingNeighbors(id: NodeId): readonly MemoryNode[] {
    const key = this.nodeKey(id)
    const neighbors = this.adjacencyOut.get(key)
    if (!neighbors) return []
    return [...neighbors].map((k) => this.nodes.get(k)!).filter(Boolean)
  }

  getIncomingNeighbors(id: NodeId): readonly MemoryNode[] {
    const key = this.nodeKey(id)
    const neighbors = this.adjacencyIn.get(key)
    if (!neighbors) return []
    return [...neighbors].map((k) => this.nodes.get(k)!).filter(Boolean)
  }

  getNeighbors(id: NodeId): readonly MemoryNode[] {
    const seen = new Set<string>()
    const out = this.getOutgoingNeighbors(id)
    const inc = this.getIncomingNeighbors(id)
    return [...out, ...inc].filter((n) => {
      const key = this.nodeKey(n.id)
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }

  getConnectedEdges(id: NodeId): { outgoing: readonly MemoryEdge[]; incoming: readonly MemoryEdge[] } {
    return {
      outgoing: this.getOutgoingEdges(id),
      incoming: this.getIncomingEdges(id),
    }
  }

  nodeCount(): number {
    return this.nodes.size
  }

  edgeCount(): number {
    return this.edges.size
  }

  snapshot(): MemorySnapshot {
    return {
      nodes: [...this.nodes.values()],
      edges: [...this.edges.values()],
      timestamp: Date.now(),
    }
  }

  loadSnapshot(snapshot: MemorySnapshot): void {
    this.nodes.clear()
    this.edges.clear()
    this.adjacencyOut.clear()
    this.adjacencyIn.clear()
    this.nodeByType.clear()

    for (const node of snapshot.nodes) {
      const key = this.nodeKey(node.id)
      this.nodes.set(key, node)
      this.addTypeIndex(node)
    }
    for (const edge of snapshot.edges) {
      this.edges.set(edge.id.value, edge)
      const sourceKey = this.nodeKey(edge.sourceNodeId)
      const targetKey = this.nodeKey(edge.targetNodeId)
      if (!this.adjacencyOut.has(sourceKey)) this.adjacencyOut.set(sourceKey, new Set())
      this.adjacencyOut.get(sourceKey)!.add(targetKey)
      if (!this.adjacencyIn.has(targetKey)) this.adjacencyIn.set(targetKey, new Set())
      this.adjacencyIn.get(targetKey)!.add(sourceKey)
    }
  }

  clear(): void {
    this.nodes.clear()
    this.edges.clear()
    this.adjacencyOut.clear()
    this.adjacencyIn.clear()
    this.nodeByType.clear()
  }

  stats(): MemoryGraphStats {
    const bySuperType: Record<string, number> = {}
    const byType: Record<string, number> = {}
    let totalArchived = 0
    let totalPinned = 0
    let totalEdges = 0

    for (const node of this.nodes.values()) {
      const superType = node.type.split(":")[0] as NodeSuperType
      bySuperType[superType] = (bySuperType[superType] ?? 0) + 1
      byType[node.type] = (byType[node.type] ?? 0) + 1
      if (node.archived) totalArchived++
      if (node.pinned) totalPinned++
    }

    for (const key of this.adjacencyOut.keys()) {
      totalEdges += this.adjacencyOut.get(key)?.size ?? 0
    }

    return {
      totalNodes: this.nodes.size,
      totalEdges: this.edges.size,
      bySuperType: bySuperType as MemoryGraphStats["bySuperType"],
      byType,
      totalArchived,
      totalPinned,
      averageEdgesPerNode: this.nodes.size > 0 ? this.edges.size / this.nodes.size : 0,
    }
  }

  private touchNode(id: NodeId): void {
    const key = this.nodeKey(id)
    const node = this.nodes.get(key)
    if (node) {
      this.nodes.set(key, {
        ...node,
        lastAccessed: Date.now(),
        accessCount: node.accessCount + 1,
      })
    }
  }

  private removeEdgeData(id: EdgeId): void {
    const edge = this.edges.get(id.value)
    if (!edge) return

    this.edges.delete(id.value)
    const sourceKey = this.nodeKey(edge.sourceNodeId)
    const targetKey = this.nodeKey(edge.targetNodeId)
    this.adjacencyOut.get(sourceKey)?.delete(targetKey)
    this.adjacencyIn.get(targetKey)?.delete(sourceKey)
    this.notifyEdge({ type: "deleted", edge, timestamp: Date.now() })
  }

  private addTypeIndex(node: MemoryNode): void {
    if (!this.nodeByType.has(node.type)) {
      this.nodeByType.set(node.type, new Set())
    }
    this.nodeByType.get(node.type)!.add(this.nodeKey(node.id))
  }

  private removeTypeIndex(node: MemoryNode): void {
    const keys = this.nodeByType.get(node.type)
    if (keys) {
      keys.delete(this.nodeKey(node.id))
      if (keys.size === 0) {
        this.nodeByType.delete(node.type)
      }
    }
  }

  private nodeKey(id: NodeId): string {
    return `${id.type}:${id.value}`
  }
}
