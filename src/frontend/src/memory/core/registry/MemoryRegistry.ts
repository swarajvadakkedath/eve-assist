import type { NodeTypeDefinition, EdgeTypeDefinition, MemoryProvider, NodeId } from "../types"
import { NodeTypeRegistry } from "./NodeTypeRegistry"
import { EdgeTypeRegistry } from "./EdgeTypeRegistry"

export class MemoryRegistry {
  readonly nodeTypes: NodeTypeRegistry
  readonly edgeTypes: EdgeTypeRegistry
  private providers = new Map<string, MemoryProvider>()
  private initialized = false

  constructor(
    nodeTypes?: NodeTypeRegistry,
    edgeTypes?: EdgeTypeRegistry,
  ) {
    this.nodeTypes = nodeTypes ?? new NodeTypeRegistry()
    this.edgeTypes = edgeTypes ?? new EdgeTypeRegistry()
  }

  registerNodeType(def: NodeTypeDefinition): this {
    this.nodeTypes.register(def)
    return this
  }

  registerEdgeType(def: EdgeTypeDefinition): this {
    this.edgeTypes.register(def)
    return this
  }

  registerProvider(provider: MemoryProvider): this {
    if (this.providers.has(provider.name)) return this
    this.providers.set(provider.name, provider)
    return this
  }

  getProvider(name: string): MemoryProvider | undefined {
    return this.providers.get(name)
  }

  getProviders(): readonly MemoryProvider[] {
    return [...this.providers.values()]
  }

  initialize(): void {
    if (this.initialized) return
    for (const provider of this.providers.values()) {
      provider.registerTypes()
    }
    this.initialized = true
  }

  isInitialized(): boolean {
    return this.initialized
  }

  validateAll(): readonly string[] {
    const errors: string[] = []
    for (const provider of this.providers.values()) {
      errors.push(...provider.validate().map((e) => `[${provider.name}] ${e}`))
    }
    return errors
  }

  validateNodeType(type: string): boolean {
    if (!this.nodeTypes.isValidNodeType(type)) return false
    const def = this.nodeTypes.get(type)
    if (!def) return false
    for (const edgeType of def.allowedEdgeTypes) {
      if (!this.edgeTypes.has(edgeType)) return false
    }
    return true
  }

  canConnect(sourceNodeId: NodeId, edgeType: string, targetNodeId: NodeId): boolean {
    return this.edgeTypes.canConnect(sourceNodeId.type, edgeType, targetNodeId.type)
  }

  getProvidersForNode(type: string): readonly MemoryProvider[] {
    return this.getProviders().filter((p) => p.canHandleNode({ type } as never))
  }

  count(): { nodeTypes: number; edgeTypes: number; providers: number } {
    return {
      nodeTypes: this.nodeTypes.count(),
      edgeTypes: this.edgeTypes.count(),
      providers: this.providers.size,
    }
  }

  reset(): void {
    this.nodeTypes.clear()
    this.edgeTypes.clear()
    this.providers.clear()
    this.initialized = false
  }
}

let defaultRegistry: MemoryRegistry | undefined

export function getMemoryRegistry(): MemoryRegistry {
  if (!defaultRegistry) {
    defaultRegistry = new MemoryRegistry()
  }
  return defaultRegistry
}

export function setMemoryRegistry(registry: MemoryRegistry): void {
  defaultRegistry = registry
}

export function resetMemoryRegistry(): void {
  defaultRegistry = undefined
}
