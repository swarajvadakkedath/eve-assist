import type { MemoryEvent, EventHandler, Subscriber, Unsubscribe } from "../types"

export class MemoryEventBus {
  private subscribers = new Map<string, Set<EventHandler>>()
  private wildcardSubscribers = new Set<EventHandler>()
  private history: MemoryEvent[] = []
  private readonly maxHistory: number

  constructor(maxHistory = 1000) {
    this.maxHistory = maxHistory
  }

  emit(event: MemoryEvent): void {
    this.history.push(event)
    if (this.history.length > this.maxHistory) {
      this.history.shift()
    }

    const handlers = this.subscribers.get(event.type)
    if (handlers) {
      for (const handler of handlers) {
        handler(event)
      }
    }

    for (const handler of this.wildcardSubscribers) {
      handler(event)
    }
  }

  on(eventType: string, handler: EventHandler): Unsubscribe {
    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, new Set())
    }
    this.subscribers.get(eventType)!.add(handler)

    return () => {
      this.subscribers.get(eventType)?.delete(handler)
    }
  }

  onAny(handler: EventHandler): Unsubscribe {
    this.wildcardSubscribers.add(handler)
    return () => {
      this.wildcardSubscribers.delete(handler)
    }
  }

  once(eventType: string, handler: EventHandler): Unsubscribe {
    const wrapper: EventHandler = (event: MemoryEvent) => {
      handler(event)
      unsubscribe()
    }
    const unsubscribe = this.on(eventType, wrapper)
    return unsubscribe
  }

  subscribe(subscriber: Subscriber): Unsubscribe {
    if (subscriber.filter) {
      const filter = subscriber.filter
      const handler: EventHandler = (event) => {
        if (filter(event)) {
          subscriber.callback(event)
        }
      }
      return this.onAny(handler)
    }
    return this.on(subscriber.id, subscriber.callback)
  }

  off(eventType: string, handler: EventHandler): void {
    this.subscribers.get(eventType)?.delete(handler)
  }

  getHistory(eventType?: string): readonly MemoryEvent[] {
    if (eventType) {
      return this.history.filter((e) => e.type === eventType)
    }
    return [...this.history]
  }

  clearHistory(): void {
    this.history = []
  }

  removeAllListeners(eventType?: string): void {
    if (eventType) {
      this.subscribers.delete(eventType)
    } else {
      this.subscribers.clear()
      this.wildcardSubscribers.clear()
    }
  }

  listenerCount(eventType?: string): number {
    if (eventType) {
      return this.subscribers.get(eventType)?.size ?? 0
    }
    let count = this.wildcardSubscribers.size
    for (const handlers of this.subscribers.values()) {
      count += handlers.size
    }
    return count
  }
}

export const MemoryEventTypes = {
  NodeCreated: "node:created",
  NodeUpdated: "node:updated",
  NodeDeleted: "node:deleted",
  NodeArchived: "node:archived",
  NodeRestored: "node:restored",
  EdgeCreated: "edge:created",
  EdgeDeleted: "edge:deleted",
  RelationshipChanged: "relationship:changed",
  GraphCleared: "graph:cleared",
} as const
