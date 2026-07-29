import type { MemoryNode, MemoryEdge, NodeId, NodeSuperType } from "../types"

export function nodeKey(id: NodeId): string {
  return `${id.type}:${id.value}`
}

export function nodesMatch(a: NodeId, b: NodeId): boolean {
  return a.value === b.value && a.type === b.type
}

export function findNodeById(nodes: readonly MemoryNode[], id: NodeId): MemoryNode | undefined {
  return nodes.find((n) => nodesMatch(n.id, id))
}

export function findEdgesByNodeId(edges: readonly MemoryEdge[], id: NodeId): MemoryEdge[] {
  return edges.filter(
    (e) => nodesMatch(e.sourceNodeId, id) || nodesMatch(e.targetNodeId, id),
  )
}

export function filterActiveNodes(nodes: readonly MemoryNode[]): MemoryNode[] {
  return nodes.filter((n) => !n.archived && n.status === "active")
}

export function filterArchivedNodes(nodes: readonly MemoryNode[]): MemoryNode[] {
  return nodes.filter((n) => n.archived)
}

export function filterPinnedNodes(nodes: readonly MemoryNode[]): MemoryNode[] {
  return nodes.filter((n) => n.pinned && !n.archived)
}

export function filterBySuperType(nodes: readonly MemoryNode[], superType: NodeSuperType): MemoryNode[] {
  return nodes.filter((n) => n.type.startsWith(superType))
}

export function filterByTag(nodes: readonly MemoryNode[], tag: string): MemoryNode[] {
  return nodes.filter((n) => n.tags.includes(tag))
}

export function filterByTags(
  nodes: readonly MemoryNode[],
  tags: readonly string[],
  mode: "all" | "any" = "any",
): MemoryNode[] {
  return nodes.filter((n) => {
    if (mode === "all") return tags.every((t) => n.tags.includes(t))
    return tags.some((t) => n.tags.includes(t))
  })
}

export function sortByRecent(nodes: readonly MemoryNode[]): MemoryNode[] {
  return [...nodes].sort((a, b) => b.updatedAt - a.updatedAt)
}

export function sortByImportance(nodes: readonly MemoryNode[]): MemoryNode[] {
  return [...nodes].sort((a, b) => b.importance - a.importance)
}

export function sortByConfidence(nodes: readonly MemoryNode[]): MemoryNode[] {
  return [...nodes].sort((a, b) => b.confidence - a.confidence)
}

export function sortByAccessCount(nodes: readonly MemoryNode[]): MemoryNode[] {
  return [...nodes].sort((a, b) => b.accessCount - a.accessCount)
}

export function sortByField(
  nodes: readonly MemoryNode[],
  field: keyof MemoryNode,
  order: "asc" | "desc" = "desc",
): MemoryNode[] {
  return [...nodes].sort((a, b) => {
    const aVal = a[field]
    const bVal = b[field]
    if (typeof aVal === "number" && typeof bVal === "number") {
      return order === "desc" ? bVal - aVal : aVal - bVal
    }
    const aStr = String(aVal ?? "")
    const bStr = String(bVal ?? "")
    return order === "desc" ? bStr.localeCompare(aStr) : aStr.localeCompare(bStr)
  })
}

export function paginate<T>(items: readonly T[], offset = 0, limit?: number): T[] {
  const actualLimit = limit ?? items.length
  return items.slice(offset, offset + actualLimit)
}

export function groupByType(nodes: readonly MemoryNode[]): Record<string, MemoryNode[]> {
  const groups: Record<string, MemoryNode[]> = {}
  for (const node of nodes) {
    if (!groups[node.type]) groups[node.type] = []
    groups[node.type].push(node)
  }
  return groups
}

export function groupBySuperType(nodes: readonly MemoryNode[]): Record<NodeSuperType, MemoryNode[]> {
  const groups: Partial<Record<NodeSuperType, MemoryNode[]>> = {}
  for (const node of nodes) {
    const superType = node.type.split(":")[0] as NodeSuperType
    if (!groups[superType]) groups[superType] = []
    groups[superType]!.push(node)
  }
  return groups as Record<NodeSuperType, MemoryNode[]>
}

export function formatTimestamp(ts: number): string {
  return new Date(ts).toISOString()
}

export function isStale(node: MemoryNode, maxAgeMs: number): boolean {
  return Date.now() - node.updatedAt > maxAgeMs
}

export function calculateAverageImportance(nodes: readonly MemoryNode[]): number {
  if (nodes.length === 0) return 0
  return nodes.reduce((sum, n) => sum + n.importance, 0) / nodes.length
}

export function calculateAverageConfidence(nodes: readonly MemoryNode[]): number {
  if (nodes.length === 0) return 0
  return nodes.reduce((sum, n) => sum + n.confidence, 0) / nodes.length
}
