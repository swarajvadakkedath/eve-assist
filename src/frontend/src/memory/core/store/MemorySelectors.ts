import type { MemoryNode, MemoryEdge, NodeId, NodeSuperType, NodeStatus } from "../types"
import type { MemoryGraph } from "../graph/MemoryGraph"

export class MemorySelectors {
  constructor(private readonly graph: MemoryGraph) {}

  getRecentNodes(count = 10): readonly MemoryNode[] {
    return [...this.graph.getAllNodes()]
      .sort((a, b) => b.updatedAt - a.updatedAt)
      .slice(0, count)
  }

  getMostAccessedNodes(count = 10): readonly MemoryNode[] {
    return [...this.graph.getAllNodes()]
      .sort((a, b) => b.accessCount - a.accessCount)
      .slice(0, count)
  }

  getMostImportantNodes(count = 10): readonly MemoryNode[] {
    return [...this.graph.getAllNodes()]
      .filter((n) => !n.archived)
      .sort((a, b) => b.importance - a.importance)
      .slice(0, count)
  }

  getHighestConfidenceNodes(count = 10): readonly MemoryNode[] {
    return [...this.graph.getAllNodes()]
      .filter((n) => !n.archived)
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, count)
  }

  getPinnedNodes(): readonly MemoryNode[] {
    return this.graph.getAllNodes().filter((n) => n.pinned && !n.archived)
  }

  getArchivedNodes(): readonly MemoryNode[] {
    return this.graph.getAllNodes().filter((n) => n.archived)
  }

  getActiveNodes(): readonly MemoryNode[] {
    return this.graph.getAllNodes().filter((n) => !n.archived && n.status === "active")
  }

  getNodesBySuperType(superType: NodeSuperType): readonly MemoryNode[] {
    return this.graph.getNodesBySuperType(superType)
  }

  getActionNodes(): readonly MemoryNode[] {
    return this.getNodesBySuperType("action")
  }

  getObservationNodes(): readonly MemoryNode[] {
    return this.getNodesBySuperType("observation")
  }

  getKnowledgeNodes(): readonly MemoryNode[] {
    return this.getNodesBySuperType("knowledge")
  }

  getArtifactNodes(): readonly MemoryNode[] {
    return this.getNodesBySuperType("artifact")
  }

  getEntityNodes(): readonly MemoryNode[] {
    return this.getNodesBySuperType("entity")
  }

  getMetaNodes(): readonly MemoryNode[] {
    return this.getNodesBySuperType("meta")
  }

  getNodesWithTag(tag: string): readonly MemoryNode[] {
    return this.graph.getAllNodes().filter((n) => n.tags.includes(tag) && !n.archived)
  }

  getNodesWithTags(tags: readonly string[], mode: "all" | "any" = "any"): readonly MemoryNode[] {
    return this.graph.getAllNodes().filter((n) => {
      if (n.archived) return false
      if (mode === "all") return tags.every((t) => n.tags.includes(t))
      return tags.some((t) => n.tags.includes(t))
    })
  }

  getNodesFromSource(source: string): readonly MemoryNode[] {
    return this.graph.getAllNodes().filter((n) => n.source === source && !n.archived)
  }

  getNodesByStatus(status: NodeStatus): readonly MemoryNode[] {
    return this.graph.getAllNodes().filter((n) => n.status === status)
  }

  getNodeCount(): number {
    return this.graph.nodeCount()
  }

  getEdgeCount(): number {
    return this.graph.edgeCount()
  }

  getEdgesForNode(id: NodeId): readonly MemoryEdge[] {
    return this.graph.getEdgesByNode(id)
  }

  getConnectedNodes(id: NodeId): readonly MemoryNode[] {
    return this.graph.getNeighbors(id)
  }

  getOutgoingConnections(id: NodeId): readonly MemoryNode[] {
    return this.graph.getOutgoingNeighbors(id)
  }

  getIncomingConnections(id: NodeId): readonly MemoryNode[] {
    return this.graph.getIncomingNeighbors(id)
  }

  search(keyword: string): readonly MemoryNode[] {
    const lower = keyword.toLowerCase().trim()
    if (!lower) return []

    return this.graph.getAllNodes().filter((n) => {
      if (n.archived) return false
      return (
        n.title.toLowerCase().includes(lower) ||
        n.summary.toLowerCase().includes(lower) ||
        n.tags.some((t) => t.toLowerCase().includes(lower)) ||
        n.type.toLowerCase().includes(lower) ||
        n.subtype.toLowerCase().includes(lower)
      )
    })
  }

  findDuplicates(
    predicate: (a: MemoryNode, b: MemoryNode) => boolean,
  ): readonly [MemoryNode, MemoryNode][] {
    const nodes = this.graph.getAllNodes()
    const pairs: [MemoryNode, MemoryNode][] = []

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (predicate(nodes[i], nodes[j])) {
          pairs.push([nodes[i], nodes[j]])
        }
      }
    }
    return pairs
  }

  getStats(): {
    total: number
    active: number
    archived: number
    pinned: number
    bySuperType: Record<NodeSuperType, number>
  } {
    const all = this.graph.getAllNodes()
    const bySuperType: Record<string, number> = {}

    for (const node of all) {
      const superType = node.type.split(":")[0]
      bySuperType[superType] = (bySuperType[superType] ?? 0) + 1
    }

    return {
      total: all.length,
      active: all.filter((n) => !n.archived).length,
      archived: all.filter((n) => n.archived).length,
      pinned: all.filter((n) => n.pinned).length,
      bySuperType: bySuperType as Record<NodeSuperType, number>,
    }
  }
}
