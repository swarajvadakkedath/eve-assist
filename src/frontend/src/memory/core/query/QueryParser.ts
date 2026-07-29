import type { SearchQuery, SearchFilters, QueryOptions } from "../types"

export interface ParsedQuery {
  readonly keyword?: string
  readonly filters: SearchFilters
  readonly options: QueryOptions
}

export class QueryParser {
  parse(query: SearchQuery): ParsedQuery {
    return {
      keyword: query.keyword,
      filters: {
        types: query.filters?.types ? [...query.filters.types] : undefined,
        superTypes: query.filters?.superTypes ? [...query.filters.superTypes] : undefined,
        tags: query.filters?.tags ? [...query.filters.tags] : undefined,
        statuses: query.filters?.statuses ? [...query.filters.statuses] : undefined,
        sources: query.filters?.sources ? [...query.filters.sources] : undefined,
        dateFrom: query.filters?.dateFrom,
        dateTo: query.filters?.dateTo,
        importanceMin: query.filters?.importanceMin,
        importanceMax: query.filters?.importanceMax,
        confidenceMin: query.filters?.confidenceMin,
        confidenceMax: query.filters?.confidenceMax,
        pinned: query.filters?.pinned,
        archived: query.filters?.archived,
      },
      options: {
        sortField: query.options?.sortField ?? "updatedAt",
        sortOrder: query.options?.sortOrder ?? "desc",
        limit: query.options?.limit,
        offset: query.options?.offset ?? 0,
      },
    }
  }

  validate(query: unknown): query is SearchQuery {
    if (typeof query !== "object" || query === null) return false
    const q = query as Record<string, unknown>

    if (q.keyword !== undefined && typeof q.keyword !== "string") return false
    if (q.filters !== undefined && (typeof q.filters !== "object" || q.filters === null)) return false
    if (q.options !== undefined && (typeof q.options !== "object" || q.options === null)) return false
    if (q.relationship !== undefined) {
      if (typeof q.relationship !== "object" || q.relationship === null) return false
      const rel = q.relationship as Record<string, unknown>
      if (!rel.seedNodeId || typeof rel.seedNodeId !== "object") return false
    }

    return true
  }
}
