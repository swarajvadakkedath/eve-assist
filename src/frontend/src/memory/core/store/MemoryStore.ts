import type {
  MemoryNode,
  MemoryEdge,
  NodeId,
  EdgeId,
  NodeInput,
  EdgeInput,
  MemorySnapshot,
  MemoryEvent,
  SearchQuery,
  SearchResult,
  EventHandler,
  Unsubscribe,
} from "../types"
import { MemoryGraph } from "../graph/MemoryGraph"
import { GraphTraversal } from "../graph/GraphTraversal"
import { RelationshipEngine } from "../graph/RelationshipEngine"
import { MemoryRegistry } from "../registry/MemoryRegistry"
import { MemoryEventBus } from "./MemoryEvents"
import { MemorySelectors } from "./MemorySelectors"
import { QueryEngine } from "../query/QueryEngine"

export interface MemoryStoreState {
  readonly nodeCount: number
  readonly edgeCount: number
  readonly lastEvent: MemoryEvent | null
}

export class MemoryStore {
  readonly graph: MemoryGraph
  readonly events: MemoryEventBus
  readonly selectors: MemorySelectors
  readonly query: QueryEngine
  readonly traversal: GraphTraversal
  readonly relationships: RelationshipEngine
  readonly registry: MemoryRegistry

  private listeners = new Set<() => void>()
  private state: MemoryStoreState = { nodeCount: 0, edgeCount: 0, lastEvent: null }

  constructor(registry?: MemoryRegistry) {
    this.registry = registry ?? new MemoryRegistry()
    this.graph = new MemoryGraph()
    this.events = new MemoryEventBus()
    this.selectors = new MemorySelectors(this.graph)
    this.traversal = new GraphTraversal(this.graph)
    this.relationships = new RelationshipEngine(this.graph, this.registry)
    this.query = new QueryEngine(this.graph, this.selectors)

    this.graph.onNodeChange((change) => {
      const typeMap: Record<string, MemoryEvent["type"]> = {
        created: "node:created",
        deleted: "node:deleted",
        archived: "node:archived",
        restored: "node:restored",
        updated: "node:updated",
      }
      this.events.emit({
        type: typeMap[change.type] ?? "node:updated",
        payload: { ...change, timestamp: Date.now() },
      } as MemoryEvent)
      this.refreshState()
    })

    this.graph.onEdgeChange((change) => {
      const type = change.type === "created" ? "edge:created" : "edge:deleted"
      this.events.emit({ type, payload: change } as MemoryEvent)
      this.refreshState()
    })
  }

  addNode(input: NodeInput): MemoryNode {
    return this.graph.addNode(input)
  }

  updateNode(id: NodeId, partial: Partial<MemoryNode>): MemoryNode | undefined {
    return this.graph.updateNode(id, partial)
  }

  deleteNode(id: NodeId): boolean {
    return this.relationships.deleteNodeWithEdges(id)
  }

  getNode(id: NodeId): MemoryNode | undefined {
    return this.graph.getNode(id)
  }

  addEdge(input: EdgeInput): MemoryEdge | undefined {
    return this.relationships.addEdge(input)
  }

  deleteEdge(id: EdgeId): boolean {
    return this.graph.deleteEdge(id)
  }

  search(query: SearchQuery): SearchResult {
    return this.query.execute(query)
  }

  snapshot(): MemorySnapshot {
    return this.graph.snapshot()
  }

  loadSnapshot(snapshot: MemorySnapshot): void {
    this.graph.loadSnapshot(snapshot)
    this.refreshState()
  }

  clear(): void {
    this.graph.clear()
    this.events.emit({ type: "graph:cleared", payload: { timestamp: Date.now() } })
    this.refreshState()
  }

  onNodeEvent(
    eventType: "created" | "updated" | "deleted" | "archived" | "restored",
    handler: EventHandler,
  ): Unsubscribe {
    const mappedType = `node:${eventType}` as const
    return this.events.on(mappedType, handler)
  }

  onEdgeEvent(eventType: "created" | "deleted", handler: EventHandler): Unsubscribe {
    const mappedType = `edge:${eventType}` as const
    return this.events.on(mappedType, handler)
  }

  onAnyEvent(handler: EventHandler): Unsubscribe {
    return this.events.onAny(handler)
  }

  subscribe(listener: () => void): Unsubscribe {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  getState(): MemoryStoreState {
    return { ...this.state }
  }

  getStats() {
    return this.selectors.getStats()
  }

  private refreshState(): void {
    this.state = {
      nodeCount: this.graph.nodeCount(),
      edgeCount: this.graph.edgeCount(),
      lastEvent: null,
    }
    for (const listener of this.listeners) {
      listener()
    }
  }
}

let defaultStore: MemoryStore | undefined

export function getMemoryStore(): MemoryStore {
  if (!defaultStore) {
    defaultStore = new MemoryStore()
  }
  return defaultStore
}

export function setMemoryStore(store: MemoryStore): void {
  defaultStore = store
}

export function resetMemoryStore(): void {
  defaultStore = undefined
}
