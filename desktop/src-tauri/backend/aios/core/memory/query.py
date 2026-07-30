"""QueryParser and QueryEngine — search, filter, sort, paginate."""

from aios.models.memory import (
    MemoryNode,
    SearchQuery,
    SearchResult,
    SearchFilters,
    QueryOptions,
    SortField,
    SortOrder,
)
from .graph import MemoryGraph
from .traversal import GraphTraversal


class QueryParser:
    def parse(self, query: SearchQuery) -> dict:
        filters = query.filters or SearchFilters()
        options = query.options or QueryOptions()
        return {
            "keyword": query.keyword,
            "filters": {
                "types": list(filters.types) if filters.types else None,
                "superTypes": list(filters.superTypes) if filters.superTypes else None,
                "tags": list(filters.tags) if filters.tags else None,
                "statuses": list(filters.statuses) if filters.statuses else None,
                "sources": list(filters.sources) if filters.sources else None,
                "dateFrom": filters.dateFrom,
                "dateTo": filters.dateTo,
                "importanceMin": filters.importanceMin,
                "importanceMax": filters.importanceMax,
                "confidenceMin": filters.confidenceMin,
                "confidenceMax": filters.confidenceMax,
                "pinned": filters.pinned,
                "archived": filters.archived,
            },
            "options": {
                "sortField": options.sortField or "updatedAt",
                "sortOrder": options.sortOrder or "desc",
                "limit": options.limit,
                "offset": options.offset or 0,
            },
            "relationship": query.relationship,
        }


class QueryEngine:
    def __init__(self, graph: MemoryGraph, traversal: GraphTraversal):
        self._graph = graph
        self._traversal = traversal
        self._parser = QueryParser()

    def execute(self, query: SearchQuery) -> SearchResult:
        parsed = self._parser.parse(query)
        results = list(self._graph.get_all_nodes())

        if parsed["keyword"] is None:
            results = self._apply_filters(results, parsed["filters"])
        else:
            results = self._apply_keyword_filter(results, parsed["keyword"])
            results = self._apply_filters(results, parsed["filters"])

        results = self._apply_traversal(results, query)
        results = self._apply_sort(results, parsed["options"]["sortField"], parsed["options"]["sortOrder"])
        total = len(results)
        results = self._apply_pagination(results, parsed["options"])

        return SearchResult(
            nodes=results,
            total=total,
            hasMore=(parsed["options"]["offset"] + parsed["options"]["limit"] < total) if parsed["options"]["limit"] else False,
            query=query,
        )

    def find_all(self, options: QueryOptions | None = None) -> SearchResult:
        opts = options or QueryOptions()
        nodes = self._graph.get_all_nodes()
        sorted_nodes = self._apply_sort(list(nodes), opts.sortField, opts.sortOrder)
        paginated = self._apply_pagination(sorted_nodes, {"sortField": opts.sortField, "sortOrder": opts.sortOrder, "limit": opts.limit, "offset": opts.offset})
        return SearchResult(nodes=paginated, total=len(nodes), query=SearchQuery(options=opts))

    def find_by_type(self, type_str: str, options: QueryOptions | None = None) -> SearchResult:
        opts = options or QueryOptions()
        nodes = self._graph.get_nodes_by_type(type_str)
        sorted_nodes = self._apply_sort(list(nodes), opts.sortField, opts.sortOrder)
        paginated = self._apply_pagination(sorted_nodes, {"sortField": opts.sortField, "sortOrder": opts.sortOrder, "limit": opts.limit, "offset": opts.offset})
        return SearchResult(nodes=paginated, total=len(nodes), query=SearchQuery(options=opts))

    def find_by_super_type(self, super_type: str, options: QueryOptions | None = None) -> SearchResult:
        opts = options or QueryOptions()
        nodes = self._graph.get_nodes_by_super_type(super_type)
        sorted_nodes = self._apply_sort(list(nodes), opts.sortField, opts.sortOrder)
        paginated = self._apply_pagination(sorted_nodes, {"sortField": opts.sortField, "sortOrder": opts.sortOrder, "limit": opts.limit, "offset": opts.offset})
        return SearchResult(nodes=paginated, total=len(nodes), query=SearchQuery(options=opts))

    def search_by_keyword(self, keyword: str, options: QueryOptions | None = None) -> SearchResult:
        opts = options or QueryOptions()
        if not keyword.strip():
            return SearchResult(nodes=[], total=0, query=SearchQuery(options=opts))
        nodes = [n for n in self._graph.get_all_nodes() if not n.archived and self._matches_keyword(n, keyword)]
        sorted_nodes = self._apply_sort(list(nodes), opts.sortField, opts.sortOrder)
        paginated = self._apply_pagination(sorted_nodes, {"sortField": opts.sortField, "sortOrder": opts.sortOrder, "limit": opts.limit, "offset": opts.offset})
        return SearchResult(nodes=paginated, total=len(nodes), query=SearchQuery(options=opts))

    def _matches_keyword(self, node: MemoryNode, keyword: str) -> bool:
        lower = keyword.lower().strip()
        return (
            lower in node.title.lower()
            or lower in node.summary.lower()
            or any(lower in t.lower() for t in node.tags)
            or lower in node.type.lower()
            or lower in node.subtype.lower()
        )

    def _apply_keyword_filter(self, nodes: list[MemoryNode], keyword: str | None) -> list[MemoryNode]:
        if keyword is None:
            return nodes
        if not keyword.strip():
            return []
        lower = keyword.lower().strip()
        return [
            n for n in nodes if not n.archived and (
                lower in n.title.lower()
                or lower in n.summary.lower()
                or any(lower in t.lower() for t in n.tags)
                or lower in n.type.lower()
                or lower in n.subtype.lower()
            )
        ]

    def _apply_filters(self, nodes: list[MemoryNode], filters: dict) -> list[MemoryNode]:
        result = list(nodes)
        if filters.get("types"):
            result = [n for n in result if n.type in filters["types"]]
        if filters.get("superTypes"):
            st_set = set(filters["superTypes"])
            result = [n for n in result if n.type.split(":")[0] in st_set]
        if filters.get("tags"):
            tag_set = set(filters["tags"])
            result = [n for n in result if tag_set.intersection(n.tags)]
        if filters.get("statuses"):
            result = [n for n in result if n.status in filters["statuses"]]
        if filters.get("sources"):
            result = [n for n in result if n.source in filters["sources"]]
        if filters.get("dateFrom") is not None:
            result = [n for n in result if n.createdAt >= filters["dateFrom"]]
        if filters.get("dateTo") is not None:
            result = [n for n in result if n.createdAt <= filters["dateTo"]]
        if filters.get("importanceMin") is not None:
            result = [n for n in result if n.importance >= filters["importanceMin"]]
        if filters.get("importanceMax") is not None:
            result = [n for n in result if n.importance <= filters["importanceMax"]]
        if filters.get("confidenceMin") is not None:
            result = [n for n in result if n.confidence >= filters["confidenceMin"]]
        if filters.get("confidenceMax") is not None:
            result = [n for n in result if n.confidence <= filters["confidenceMax"]]
        if filters.get("pinned") is not None:
            result = [n for n in result if n.pinned == filters["pinned"]]
        if filters.get("archived") is not None:
            result = [n for n in result if n.archived == filters["archived"]]
        return result

    def _apply_traversal(self, results: list[MemoryNode], query: SearchQuery) -> list[MemoryNode]:
        if not query.relationship:
            return results
        rel = query.relationship
        seed_node_id = rel.get("seedNodeId")
        if not seed_node_id:
            return results
        seed_node = self._graph.get_node_by_id(seed_node_id)
        if not seed_node:
            return results
        rf = rel.get("filter", {})
        traversal_result = self._traversal.bfs(
            seed_node_id,
            max_depth=rf.get("maxDepth", 3),
            edge_types=rf.get("edgeTypes"),
        )
        traversal_keys = {self._traversal._node_key(n.id) for n in traversal_result.nodes}
        return [n for n in results if self._traversal._node_key(n.id) in traversal_keys]

    def _apply_sort(self, nodes: list[MemoryNode], sort_field: SortField | None, sort_order: SortOrder = "desc") -> list[MemoryNode]:
        if not sort_field:
            return nodes
        def _key(n: MemoryNode):
            val = getattr(n, sort_field, None)
            if val is None:
                return ""
            return val
        return sorted(nodes, key=_key, reverse=(sort_order == "desc"))

    def _apply_pagination(self, nodes: list[MemoryNode], options: dict) -> list[MemoryNode]:
        offset = options.get("offset", 0)
        limit = options.get("limit")
        if limit is None:
            return nodes[offset:]
        return nodes[offset:offset + limit]
