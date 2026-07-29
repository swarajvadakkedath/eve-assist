import type { EdgeTypeDefinition } from "../types"

export class EdgeTypeRegistry {
  private types = new Map<string, EdgeTypeDefinition>()

  register(def: EdgeTypeDefinition): this {
    if (this.types.has(def.name)) {
      return this
    }
    this.types.set(def.name, Object.freeze({ ...def }))
    return this
  }

  registerMany(defs: readonly EdgeTypeDefinition[]): this {
    for (const def of defs) {
      this.register(def)
    }
    return this
  }

  get(name: string): EdgeTypeDefinition | undefined {
    return this.types.get(name)
  }

  has(name: string): boolean {
    return this.types.has(name)
  }

  getAll(): readonly EdgeTypeDefinition[] {
    return [...this.types.values()]
  }

  canConnect(sourceType: string, edgeType: string, targetType: string): boolean {
    const def = this.types.get(edgeType)
    if (!def) return false
    return def.allowedSourceTypes.includes(sourceType) && def.allowedTargetTypes.includes(targetType)
  }

  getAllowedSourceTypes(edgeType: string): readonly string[] {
    return this.types.get(edgeType)?.allowedSourceTypes ?? []
  }

  getAllowedTargetTypes(edgeType: string): readonly string[] {
    return this.types.get(edgeType)?.allowedTargetTypes ?? []
  }

  isDirectional(edgeType: string): boolean {
    return this.types.get(edgeType)?.directional ?? true
  }

  getDefaultMetadata(edgeType: string): Record<string, unknown> {
    return { ...(this.types.get(edgeType)?.defaultMetadata ?? {}) }
  }

  count(): number {
    return this.types.size
  }

  clear(): void {
    this.types.clear()
  }
}
