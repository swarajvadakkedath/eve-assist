"""MemoryValidation — validate nodes, edges, inputs, graph constraints."""

from aios.models.memory import (
    MemoryNode,
    MemoryEdge,
    NodeId,
    NodeInput,
    EdgeInput,
    ValidationError,
    CircularDependency,
)
from .graph import MemoryGraph
from .traversal import GraphTraversal


class MemoryValidation:
    def __init__(self, graph: MemoryGraph):
        self._graph = graph

    def validate_node_input(self, input: NodeInput) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if not input.type:
            errors.append(ValidationError(code="MISSING_TYPE", message="Node type is required", field="type"))
        if not input.title:
            errors.append(ValidationError(code="MISSING_TITLE", message="Node title is required", field="title"))
        if input.importance is not None and (input.importance < 0 or input.importance > 10):
            errors.append(ValidationError(code="INVALID_IMPORTANCE", message="Importance must be between 0 and 10", field="importance"))
        if input.confidence is not None and (input.confidence < 0 or input.confidence > 1):
            errors.append(ValidationError(code="INVALID_CONFIDENCE", message="Confidence must be between 0 and 1", field="confidence"))
        return errors

    def validate_edge_input(self, input: EdgeInput) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if not input.type:
            errors.append(ValidationError(code="MISSING_EDGE_TYPE", message="Edge type is required", field="type"))
        if input.strength is not None and (input.strength < 0 or input.strength > 1):
            errors.append(ValidationError(code="INVALID_STRENGTH", message="Edge strength must be between 0 and 1", field="strength"))
        if input.weight is not None and (input.weight < 0 or input.weight > 1):
            errors.append(ValidationError(code="INVALID_WEIGHT", message="Edge weight must be between 0 and 1", field="weight"))
        return errors

    def validate_node(self, node: MemoryNode) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if not node.type:
            errors.append(ValidationError(code="INVALID_TYPE", message="Node type is empty", nodeId=node.id, field="type"))
        if node.importance < 0 or node.importance > 10:
            errors.append(ValidationError(code="INVALID_IMPORTANCE", message=f"Importance {node.importance} out of range [0, 10]", nodeId=node.id, field="importance"))
        if node.confidence < 0 or node.confidence > 1:
            errors.append(ValidationError(code="INVALID_CONFIDENCE", message=f"Confidence {node.confidence} out of range [0, 1]", nodeId=node.id, field="confidence"))
        if not node.id.value or not node.id.type:
            errors.append(ValidationError(code="INVALID_ID", message="Node ID is incomplete", nodeId=node.id))
        return errors

    def validate_edge(self, edge: MemoryEdge) -> list[ValidationError]:
        errors: list[ValidationError] = []
        if not edge.type:
            errors.append(ValidationError(code="INVALID_EDGE_TYPE", message="Edge type is empty", edgeId=edge.id, field="type"))
        if edge.strength < 0 or edge.strength > 1:
            errors.append(ValidationError(code="INVALID_STRENGTH", message=f"Strength {edge.strength} out of range [0, 1]", edgeId=edge.id, field="strength"))
        if edge.weight < 0 or edge.weight > 1:
            errors.append(ValidationError(code="INVALID_WEIGHT", message=f"Weight {edge.weight} out of range [0, 1]", edgeId=edge.id, field="weight"))
        source_node = self._graph.get_node_by_id(edge.sourceNodeId)
        target_node = self._graph.get_node_by_id(edge.targetNodeId)
        if not source_node:
            errors.append(ValidationError(code="SOURCE_NOT_FOUND", message=f"Source node {edge.sourceNodeId} not found", edgeId=edge.id))
        if not target_node:
            errors.append(ValidationError(code="TARGET_NOT_FOUND", message=f"Target node {edge.targetNodeId} not found", edgeId=edge.id))
        return errors

    def validate_graph(self) -> list[ValidationError]:
        errors: list[ValidationError] = []
        for node in self._graph.get_all_nodes():
            errors.extend(self.validate_node(node))
        for edge in list(self._graph._edges.values()):
            errors.extend(self.validate_edge(edge))
        cycles = self.find_cycles()
        for cycle in cycles:
            errors.append(ValidationError(
                code="CIRCULAR_DEPENDENCY",
                message="Circular dependency detected",
                nodeId=cycle.path[0] if cycle.path else None,
                edgeId=cycle.edge.id if cycle.edge else None,
            ))
        return errors

    def find_cycles(self) -> list[CircularDependency]:
        cycles: list[CircularDependency] = []
        visited: set[str] = set()
        in_stack: set[str] = set()
        nodes = self._graph.get_all_nodes()

        def _dfs(node_id: NodeId, path: list[NodeId]):
            key = f"{node_id.type}:{node_id.value}"
            if key in in_stack:
                cycle_start = -1
                for i, n in enumerate(path):
                    if f"{n.type}:{n.value}" == key:
                        cycle_start = i
                        break
                if cycle_start >= 0:
                    cycle_path = path[cycle_start:]
                    edges = _get_path_edges(cycle_path)
                    cycles.append(CircularDependency(path=cycle_path, edge=edges[0] if edges else None))
                return
            if key in visited:
                return
            visited.add(key)
            in_stack.add(key)
            for neighbor in self._graph.get_outgoing_neighbors(node_id):
                _dfs(neighbor.id, path + [neighbor.id])
            in_stack.discard(key)

        def _get_path_edges(path: list[NodeId]) -> list[MemoryEdge]:
            edge_list: list[MemoryEdge] = []
            for i in range(len(path) - 1):
                outgoing = self._graph.get_outgoing_edges(path[i])
                match = next((e for e in outgoing if f"{e.targetNodeId.type}:{e.targetNodeId.value}" == f"{path[i+1].type}:{path[i+1].value}"), None)
                if match:
                    edge_list.append(match)
            return edge_list

        for node in nodes:
            if f"{node.id.type}:{node.id.value}" not in visited:
                _dfs(node.id, [node.id])
        return cycles

    def would_create_cycle(self, source_id: NodeId, target_id: NodeId) -> CircularDependency | None:
        if f"{source_id.type}:{source_id.value}" == f"{target_id.type}:{target_id.value}":
            return CircularDependency(path=[source_id])
        traversal = GraphTraversal(self._graph)
        paths = traversal.find_paths(target_id, source_id, max_depth=50)
        if paths:
            first = paths[0]
            return CircularDependency(path=first.path or [], edge=first.edges[0] if first.edges else None)
        return None
