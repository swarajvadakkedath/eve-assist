import type {
  MemoryNode,
  SearchQuery,
  SearchResult,
  SearchFilters,
  QueryOptions,
  SortField,
  SortOrder,
} from "../types"
import type { MemoryGraph } from "../graph/MemoryGraph"
import type { MemorySelectors } from "../store/MemorySelectors"
import { QueryParser } from "./QueryParser"
import { GraphTraversal } from "../graph/GraphTraversal"

export class QueryEngine {
  private graph: MemoryGraph
  private selectors: MemorySelectors
  private traversal: GraphTraversal
  private parser: QueryParser

  constructor(
    graph: MemoryGraph,
    selectors: MemorySelectors,
  ) {
    this.graph = graph
    this.selectors = selectors
    this.traversal = new GraphTraversal(graph)
    this.parser = new QueryParser()
  }

  execute(query: SearchQuery): SearchResult {
    const parsed = this.parser.parse(query)
    let results: MemoryNode[] = [...this.graph.getAllNodes()]

    if (parsed.keyword === undefined) {
      results = this.applyFilters(results, parsed.filters)
    } else {
      results = this.applyKeywordFilter(results, parsed.keyword)
      results = this.applyFilters(results, parsed.filters)
    }
    results = this.applyTraversal(results, query)
    results = this.applySort(results, parsed.options.sortField, parsed.options.sortOrder)
    results = this.applyPagination(results, parsed.options)

    return {
      nodes: results,
      total: results.length,
      hasMore: false,
      query,
    }
  }

  findAll(options?: QueryOptions): SearchResult {
    const nodes = this.graph.getAllNodes()
    const sorted = this.applySort(nodes, options?.sortField, options?.sortOrder)
    const paginated = this.applyPagination(sorted, options ?? {})
    return {
      nodes: paginated,
      total: nodes.length,
      hasMore: false,
      query: { options: options ?? {} },
    }
  }

  findByType(type: string, options?: QueryOptions): SearchResult {
    const nodes = this.graph.getNodesByType(type)
    const sorted = this.applySort(nodes, options?.sortField, options?.sortOrder)
    const paginated = this.applyPagination(sorted, options ?? {})
    return {
      nodes: paginated,
      total: nodes.length,
      hasMore: false,
      query: { options: options ?? {} },
    }
  }

  findBySuperType(superType: string, options?: QueryOptions): SearchResult {
    const nodes = this.graph.getNodesBySuperType(superType as never)
    const sorted = this.applySort(nodes, options?.sortField, options?.sortOrder)
    const paginated = this.applyPagination(sorted, options ?? {})
    return {
      nodes: paginated,
      total: nodes.length,
      hasMore: false,
      query: { options: options ?? {} },
    }
  }

  findByTag(tag: string, options?: QueryOptions): SearchResult {
    const nodes = this.selectors.getNodesWithTag(tag)
    const sorted = this.applySort(nodes, options?.sortField, options?.sortOrder)
    const paginated = this.applyPagination(sorted, options ?? {})
    return {
      nodes: paginated,
      total: nodes.length,
      hasMore: false,
      query: { options: options ?? {} },
    }
  }

  findBySource(source: string, options?: QueryOptions): SearchResult {
    const nodes = this.selectors.getNodesFromSource(source)
    const sorted = this.applySort(nodes, options?.sortField, options?.sortOrder)
    const paginated = this.applyPagination(sorted, options ?? {})
    return {
      nodes: paginated,
      total: nodes.length,
      hasMore: false,
      query: { options: options ?? {} },
    }
  }

  searchByKeyword(keyword: string, options?: QueryOptions): SearchResult {
    if (!keyword.trim()) {
      return { nodes: [], total: 0, hasMore: false, query: { options: options ?? {} } }
    }
    const nodes = this.selectors.search(keyword)
    const sorted = this.applySort(nodes, options?.sortField, options?.sortOrder)
    const paginated = this.applyPagination(sorted, options ?? {})
    return {
      nodes: paginated,
      total: nodes.length,
      hasMore: false,
      query: { options: options ?? {} },
    }
  }

  private applyKeywordFilter(nodes: readonly MemoryNode[], keyword?: string): MemoryNode[] {
    if (keyword === undefined) return [...nodes]
    if (!keyword.trim()) return []
    const lower = keyword.toLowerCase().trim()

    return nodes.filter((n) => {
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

  private applyFilters(nodes: readonly MemoryNode[], filters?: SearchFilters): MemoryNode[] {
    if (!filters) return [...nodes]

    let result = [...nodes]

    if (filters.types && filters.types.length > 0) {
      result = result.filter((n) => filters.types!.includes(n.type))
    }

    if (filters.superTypes && filters.superTypes.length > 0) {
      result = result.filter((n) => {
        const superType = n.type.split(":")[0]
        return filters.superTypes!.includes(superType as never)
      })
    }

    if (filters.tags && filters.tags.length > 0) {
      result = result.filter((n) => filters.tags!.some((t) => n.tags.includes(t)))
    }

    if (filters.statuses && filters.statuses.length > 0) {
      result = result.filter((n) => filters.statuses!.includes(n.status))
    }

    if (filters.sources && filters.sources.length > 0) {
      result = result.filter((n) => filters.sources!.includes(n.source))
    }

    if (filters.dateFrom !== undefined) {
      result = result.filter((n) => n.createdAt >= filters.dateFrom!)
    }

    if (filters.dateTo !== undefined) {
      result = result.filter((n) => n.createdAt <= filters.dateTo!)
    }

    if (filters.importanceMin !== undefined) {
      result = result.filter((n) => n.importance >= filters.importanceMin!)
    }

    if (filters.importanceMax !== undefined) {
      result = result.filter((n) => n.importance <= filters.importanceMax!)
    }

    if (filters.confidenceMin !== undefined) {
      result = result.filter((n) => n.confidence >= filters.confidenceMin!)
    }

    if (filters.confidenceMax !== undefined) {
      result = result.filter((n) => n.confidence <= filters.confidenceMax!)
    }

    if (filters.pinned !== undefined) {
      result = result.filter((n) => n.pinned === filters.pinned)
    }

    if (filters.archived !== undefined) {
      result = result.filter((n) => n.archived === filters.archived)
    }

    return result
  }

  private applyTraversal(result: readonly MemoryNode[], query: SearchQuery): MemoryNode[] {
    if (!query.relationship?.seedNodeId) return [...result]
    const seedNodeId = query.relationship.seedNodeId
    const seedNode = this.graph.getNodeById(seedNodeId)
    if (!seedNode) return [...result]

    const traversalResult = this.traversal.bfs(seedNodeId, {
      maxDepth: query.relationship.filter.maxDepth ?? 3,
      edgeTypes: query.relationship.filter.edgeTypes,
    })

    const traversalKeys = new Set(traversalResult.nodes.map((n) => `${n.id.type}:${n.id.value}`))
    return result.filter((n) => traversalKeys.has(`${n.id.type}:${n.id.value}`))
  }

  private applySort(
    nodes: readonly MemoryNode[],
    sortField?: SortField,
    sortOrder: SortOrder = "desc",
  ): MemoryNode[] {
    if (!sortField) return [...nodes]

    return [...nodes].sort((a, b) => {
      const aVal = a[sortField] as number
      const bVal = b[sortField] as number
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortOrder === "desc" ? bVal - aVal : aVal - bVal
      }
      const aStr = String(a[sortField as keyof MemoryNode] ?? "")
      const bStr = String(b[sortField as keyof MemoryNode] ?? "")
      return sortOrder === "desc"
        ? bStr.localeCompare(aStr)
        : aStr.localeCompare(bStr)
    })
  }

  private applyPagination(
    nodes: readonly MemoryNode[],
    options: QueryOptions,
  ): MemoryNode[] {
    const offset = options.offset ?? 0
    const limit = options.limit ?? nodes.length
    return nodes.slice(offset, offset + limit)
  }
}
