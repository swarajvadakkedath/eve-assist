import { useSyncExternalStore, useCallback, useRef } from "react";
import { getMemoryStore, type MemoryStoreState } from "@/memory/core";
import type { MemoryEvent, Unsubscribe } from "@/memory/core";

let cachedState: MemoryStoreState | null = null;

function subscribeToStore(callback: () => void): Unsubscribe {
  const store = getMemoryStore();
  return store.subscribe(callback);
}

function getSnapshot(): MemoryStoreState {
  const store = getMemoryStore();
  const state = store.getState();
  if (
    !cachedState ||
    cachedState.nodeCount !== state.nodeCount ||
    cachedState.edgeCount !== state.edgeCount ||
    cachedState.lastEvent !== state.lastEvent
  ) {
    cachedState = state;
  }
  return cachedState;
}

export function useMemoryStore(): MemoryStoreState {
  const getSnapshotRef = useRef(getSnapshot);
  return useSyncExternalStore(subscribeToStore, getSnapshotRef.current);
}

export function useMemoryEvent(eventType: string): MemoryEvent | null {
  const storeRef = useRef(getMemoryStore());
  const eventRef = useRef<MemoryEvent | null>(null);

  const subscribe = useCallback((callback: () => void) => {
    const store = storeRef.current;
    return store.onAnyEvent(() => {
      const state = store.getState();
      if (state.lastEvent && state.lastEvent.type === eventType) {
        eventRef.current = state.lastEvent;
        callback();
      }
    });
  }, [eventType]);

  const getSnapshot = useCallback(() => eventRef.current, []);

  return useSyncExternalStore(subscribe, getSnapshot);
}

export function useMemoryNodes(): { nodeCount: number; edgeCount: number } {
  const { nodeCount, edgeCount } = useMemoryStore();
  return { nodeCount, edgeCount };
}
