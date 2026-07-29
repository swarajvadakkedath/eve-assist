import type {
  MemoryNode,
  MemoryEdge,
  NodeInput,
  EdgeInput,
  NodeTypeDefinition,
  EdgeTypeDefinition,
  ValidationError,
} from "../types"
import type { NodeTypeRegistry } from "../registry/NodeTypeRegistry"
import type { EdgeTypeRegistry } from "../registry/EdgeTypeRegistry"

export class MemoryValidation {
  constructor(
    private readonly nodeTypeRegistry: NodeTypeRegistry,
    private readonly edgeTypeRegistry: EdgeTypeRegistry,
  ) {}

  validateNode(node: MemoryNode): readonly ValidationError[] {
    const errors: ValidationError[] = []

    if (!node.id.value || !node.id.type) {
      errors.push({ code: "INVALID_NODE_ID", message: "Node ID must have a value and type", nodeId: node.id })
    }

    if (!node.type) {
      errors.push({ code: "MISSING_TYPE", message: "Node must have a type", nodeId: node.id, field: "type" })
    } else if (!this.nodeTypeRegistry.isValidNodeType(node.type)) {
      errors.push({ code: "UNKNOWN_NODE_TYPE", message: `Node type '${node.type}' is not registered`, nodeId: node.id, field: "type" })
    }

    if (!node.title?.trim()) {
      errors.push({ code: "MISSING_TITLE", message: "Node must have a non-empty title", nodeId: node.id, field: "title" })
    }

    if (!node.source?.trim()) {
      errors.push({ code: "MISSING_SOURCE", message: "Node must have a source", nodeId: node.id, field: "source" })
    }

    if (node.importance < 0 || node.importance > 10) {
      errors.push({ code: "INVALID_IMPORTANCE", message: "Importance must be between 0 and 10", nodeId: node.id, field: "importance" })
    }

    if (node.confidence < 0 || node.confidence > 1) {
      errors.push({ code: "INVALID_CONFIDENCE", message: "Confidence must be between 0 and 1", nodeId: node.id, field: "confidence" })
    }

    if (node.createdAt > Date.now() + 1000) {
      errors.push({ code: "FUTURE_CREATED_AT", message: "CreatedAt cannot be in the future", nodeId: node.id, field: "createdAt" })
    }

    if (node.updatedAt < node.createdAt - 1000) {
      errors.push({ code: "INVALID_TIMESTAMP", message: "UpdatedAt cannot be before createdAt", nodeId: node.id, field: "updatedAt" })
    }

    if (node.archived && node.pinned) {
      errors.push({ code: "ARCHIVED_AND_PINNED", message: "Node cannot be both archived and pinned", nodeId: node.id })
    }

    return errors
  }

  validateNodeInput(input: NodeInput): readonly ValidationError[] {
    const errors: ValidationError[] = []

    if (!input.type) {
      errors.push({ code: "MISSING_TYPE", message: "Node input must have a type", field: "type" })
    }

    if (!input.title?.trim()) {
      errors.push({ code: "MISSING_TITLE", message: "Node input must have a non-empty title", field: "title" })
    }

    if (!input.source?.trim()) {
      errors.push({ code: "MISSING_SOURCE", message: "Node input must have a source", field: "source" })
    }

    if (input.importance !== undefined && (input.importance < 0 || input.importance > 10)) {
      errors.push({ code: "INVALID_IMPORTANCE", message: "Importance must be between 0 and 10", field: "importance" })
    }

    if (input.confidence !== undefined && (input.confidence < 0 || input.confidence > 1)) {
      errors.push({ code: "INVALID_CONFIDENCE", message: "Confidence must be between 0 and 1", field: "confidence" })
    }

    return errors
  }

  validateEdge(edge: MemoryEdge): readonly ValidationError[] {
    const errors: ValidationError[] = []

    if (!edge.id?.value) {
      errors.push({ code: "INVALID_EDGE_ID", message: "Edge must have an ID" })
    }

    if (!edge.type) {
      errors.push({ code: "MISSING_EDGE_TYPE", message: "Edge must have a type", field: "type" })
    } else if (!this.edgeTypeRegistry.has(edge.type)) {
      errors.push({ code: "UNKNOWN_EDGE_TYPE", message: `Edge type '${edge.type}' is not registered`, field: "type" })
    }

    if (!edge.sourceNodeId?.value) {
      errors.push({ code: "INVALID_SOURCE_NODE", message: "Edge must have a source node", edgeId: edge.id })
    }

    if (!edge.targetNodeId?.value) {
      errors.push({ code: "INVALID_TARGET_NODE", message: "Edge must have a target node", edgeId: edge.id })
    }

    if (edge.strength < 0 || edge.strength > 1) {
      errors.push({ code: "INVALID_STRENGTH", message: "Strength must be between 0 and 1", edgeId: edge.id, field: "strength" })
    }

    if (edge.weight < 0 || edge.weight > 1) {
      errors.push({ code: "INVALID_WEIGHT", message: "Weight must be between 0 and 1", edgeId: edge.id, field: "weight" })
    }

    return errors
  }

  validateEdgeInput(input: EdgeInput): readonly ValidationError[] {
    const errors: ValidationError[] = []

    if (!input.type) {
      errors.push({ code: "MISSING_EDGE_TYPE", message: "Edge input must have a type", field: "type" })
    }

    if (!input.sourceNodeId?.value) {
      errors.push({ code: "INVALID_SOURCE_NODE", message: "Edge input must have a valid source node" })
    }

    if (!input.targetNodeId?.value) {
      errors.push({ code: "INVALID_TARGET_NODE", message: "Edge input must have a valid target node" })
    }

    if (input.strength !== undefined && (input.strength < 0 || input.strength > 1)) {
      errors.push({ code: "INVALID_STRENGTH", message: "Strength must be between 0 and 1", field: "strength" })
    }

    if (input.weight !== undefined && (input.weight < 0 || input.weight > 1)) {
      errors.push({ code: "INVALID_WEIGHT", message: "Weight must be between 0 and 1", field: "weight" })
    }

    return errors
  }

  validateNodeTypeDefinition(def: NodeTypeDefinition): readonly ValidationError[] {
    const errors: ValidationError[] = []

    if (!def.name?.trim()) {
      errors.push({ code: "MISSING_DEF_NAME", message: "Node type definition must have a name", field: "name" })
    }

    if (!def.superType) {
      errors.push({ code: "MISSING_SUPER_TYPE", message: "Node type definition must have a superType", field: "superType" })
    }

    if (!def.description?.trim()) {
      errors.push({ code: "MISSING_DEF_DESCRIPTION", message: "Node type definition must have a description", field: "description" })
    }

    return errors
  }

  validateEdgeTypeDefinition(def: EdgeTypeDefinition): readonly ValidationError[] {
    const errors: ValidationError[] = []

    if (!def.name?.trim()) {
      errors.push({ code: "MISSING_DEF_NAME", message: "Edge type definition must have a name", field: "name" })
    }

    if (!def.description?.trim()) {
      errors.push({ code: "MISSING_DEF_DESCRIPTION", message: "Edge type definition must have a description", field: "description" })
    }

    return errors
  }

  isValidImportance(value: number): boolean {
    return value >= 0 && value <= 10
  }

  isValidConfidence(value: number): boolean {
    return value >= 0 && value <= 1
  }

  isValidStrength(value: number): boolean {
    return value >= 0 && value <= 1
  }

  isValidWeight(value: number): boolean {
    return value >= 0 && value <= 1
  }
}
