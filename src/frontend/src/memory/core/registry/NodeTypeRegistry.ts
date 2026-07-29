import type { NodeTypeDefinition, NodeSuperType, NodeId } from "../types"

export class NodeTypeRegistry {
  private types = new Map<string, NodeTypeDefinition>()

  register(def: NodeTypeDefinition): this {
    if (this.types.has(def.name)) {
      return this
    }
    this.types.set(def.name, Object.freeze({ ...def }))
    return this
  }

  registerMany(defs: readonly NodeTypeDefinition[]): this {
    for (const def of defs) {
      this.register(def)
    }
    return this
  }

  get(name: string): NodeTypeDefinition | undefined {
    return this.types.get(name)
  }

  has(name: string): boolean {
    return this.types.has(name)
  }

  getAll(): readonly NodeTypeDefinition[] {
    return [...this.types.values()]
  }

  getBySuperType(superType: NodeSuperType): readonly NodeTypeDefinition[] {
    return this.getAll().filter((t) => t.superType === superType)
  }

  getAllowedEdgeTypes(nodeType: string): readonly string[] {
    return this.types.get(nodeType)?.allowedEdgeTypes ?? []
  }

  isValidNodeType(nodeType: string): boolean {
    return this.types.has(nodeType)
  }

  isAllowedEdgeType(nodeType: string, edgeType: string): boolean {
    const def = this.types.get(nodeType)
    if (!def) return false
    return def.allowedEdgeTypes.includes(edgeType)
  }

  validateNodeId(nodeId: NodeId): boolean {
    return this.isValidNodeType(nodeId.type)
  }

  getDefaultMetadata(nodeType: string): Record<string, unknown> {
    return { ...(this.types.get(nodeType)?.defaultMetadata ?? {}) }
  }

  count(): number {
    return this.types.size
  }

  clear(): void {
    this.types.clear()
  }
}
