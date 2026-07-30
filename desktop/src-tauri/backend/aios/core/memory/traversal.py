"""GraphTraversal — BFS, DFS, path finding."""

from aios.models.memory import (
    MemoryNode,
    MemoryEdge,
    NodeId,
    EdgeDirection,
    TraversalResult,
)
from .graph import MemoryGraph


class GraphTraversal:
    def __init__(self, graph: MemoryGraph):
        self._graph = graph

    def _node_key(self, node_id: NodeId) -> str:
        return f"{node_id.type}:{node_id.value}"

    def bfs(self, start_id: NodeId, max_depth: int = 10, edge_types: list[str] | None = None) -> TraversalResult:
        visited: set[str] = set()
        nodes: list[MemoryNode] = []
        edges: list[MemoryEdge] = []
        queue: list[dict] = []
        start_key = self._node_key(start_id)
        start_node = self._graph.get_node(start_id)
        if not start_node:
            return TraversalResult(nodes=[], edges=[], depth=0)
        visited.add(start_key)
        queue.append({"id": start_id, "depth": 0, "path": [start_id]})
        nodes.append(start_node)
        while queue:
            current = queue.pop(0)
            if current["depth"] >= max_depth:
                continue
            all_edges = list(self._graph.get_outgoing_edges(current["id"]))
            all_edges.extend(self._graph.get_incoming_edges(current["id"]))
            for edge in all_edges:
                if edge_types and edge.type not in edge_types:
                    continue
                neighbor_id = edge.targetNodeId if self._node_key(edge.sourceNodeId) == self._node_key(current["id"]) else edge.sourceNodeId
                neighbor_key = self._node_key(neighbor_id)
                if neighbor_key in visited:
                    continue
                visited.add(neighbor_key)
                edges.append(edge)
                neighbor = self._graph.get_node_by_id(neighbor_id)
                if neighbor:
                    nodes.append(neighbor)
                    queue.append({"id": neighbor_id, "depth": current["depth"] + 1, "path": current["path"] + [neighbor_id]})
        return TraversalResult(nodes=nodes, edges=edges, depth=min(max_depth, 1 if len(nodes) > 1 else 0))

    def dfs(self, start_id: NodeId, max_depth: int = 10, edge_types: list[str] | None = None) -> TraversalResult:
        visited: set[str] = set()
        nodes: list[MemoryNode] = []
        edges: list[MemoryEdge] = []
        start_node = self._graph.get_node(start_id)
        if not start_node:
            return TraversalResult(nodes=[], edges=[], depth=0)
        stack: list[dict] = [{"id": start_id, "depth": 0, "path": [start_id]}]
        visited.add(self._node_key(start_id))
        nodes.append(start_node)
        while stack:
            current = stack.pop()
            if current["depth"] >= max_depth:
                continue
            all_edges = list(self._graph.get_outgoing_edges(current["id"]))
            all_edges.extend(self._graph.get_incoming_edges(current["id"]))
            for edge in all_edges:
                if edge_types and edge.type not in edge_types:
                    continue
                neighbor_id = edge.targetNodeId if self._node_key(edge.sourceNodeId) == self._node_key(current["id"]) else edge.sourceNodeId
                neighbor_key = self._node_key(neighbor_id)
                if neighbor_key in visited:
                    continue
                visited.add(neighbor_key)
                edges.append(edge)
                neighbor = self._graph.get_node_by_id(neighbor_id)
                if neighbor:
                    nodes.append(neighbor)
                    stack.append({"id": neighbor_id, "depth": current["depth"] + 1, "path": current["path"] + [neighbor_id]})
        return TraversalResult(nodes=nodes, edges=edges, depth=min(max_depth, 1 if len(nodes) > 1 else 0))

    def find_paths(self, start_id: NodeId, end_id: NodeId, max_depth: int = 10, edge_types: list[str] | None = None) -> list[TraversalResult]:
        results: list[TraversalResult] = []
        visited: set[str] = set()

        def _dfs(current_id: NodeId, end_id: NodeId, depth: int, path: list[NodeId], edge_path: list[MemoryEdge]):
            current_key = self._node_key(current_id)
            if depth > max_depth:
                return
            if current_key in visited:
                return
            if self._node_key(current_id) == self._node_key(end_id):
                path_nodes = [self._graph.get_node_by_id(nid) for nid in path if self._graph.get_node_by_id(nid)]
                results.append(TraversalResult(
                    nodes=[n for n in path_nodes if n is not None],
                    edges=list(edge_path),
                    depth=depth,
                    path=list(path),
                ))
                return
            visited.add(current_key)
            all_edges = list(self._graph.get_outgoing_edges(current_id))
            all_edges.extend(self._graph.get_incoming_edges(current_id))
            for edge in all_edges:
                if edge_types and edge.type not in edge_types:
                    continue
                neighbor_id = edge.targetNodeId if self._node_key(edge.sourceNodeId) == current_key else edge.sourceNodeId
                _dfs(neighbor_id, end_id, depth + 1, path + [neighbor_id], edge_path + [edge])
            visited.discard(current_key)

        _dfs(start_id, end_id, 0, [start_id], [])
        return results

    def find_shortest_path(self, start_id: NodeId, end_id: NodeId, edge_types: list[str] | None = None) -> TraversalResult | None:
        paths = self.find_paths(start_id, end_id, max_depth=10, edge_types=edge_types)
        if not paths:
            return None
        return min(paths, key=lambda r: r.depth)

    def get_connected_component(self, start_id: NodeId) -> TraversalResult:
        return self.bfs(start_id, max_depth=100)

    def get_neighbors_at_depth(self, node_id: NodeId, depth: int, edge_types: list[str] | None = None, direction: EdgeDirection = "both") -> list[MemoryNode]:
        if depth == 0:
            node = self._graph.get_node_by_id(node_id)
            return [node] if node else []
        result = self.bfs(node_id, max_depth=depth, edge_types=edge_types)
        if depth == 1:
            return [n for n in result.nodes if self._node_key(n.id) != self._node_key(node_id)]
        depth_map: dict[str, int] = {self._node_key(node_id): 0}
        queue: list[dict] = [{"id": node_id, "depth": 0}]
        while queue:
            current = queue.pop(0)
            if current["depth"] >= depth:
                continue
            for neighbor in self._graph.get_neighbors(current["id"]):
                key = self._node_key(neighbor.id)
                if key not in depth_map:
                    depth_map[key] = current["depth"] + 1
                    queue.append({"id": neighbor.id, "depth": current["depth"] + 1})
        return [n for n in result.nodes if depth_map.get(self._node_key(n.id)) == depth]
