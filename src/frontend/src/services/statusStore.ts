import { useSyncExternalStore } from "react";

const isTauri =
  typeof window !== "undefined" &&
  (!!(window as any).__TAURI_INTERNALS__ || !!(window as any).__TAURI__);
const BACKEND_PORT = 8456;
const STATUS_BASE = isTauri
  ? `http://127.0.0.1:${BACKEND_PORT}/api/v1`
  : "/api/v1";

const POLL_MS = 1000;
const READY_SET = new Set(["ready", "degraded"]);

type Status =
  | "starting"
  | "initializing"
  | "ready"
  | "listening"
  | "thinking"
  | "planning"
  | "executing"
  | "waiting"
  | "updating"
  | "offline"
  | "degraded"
  | "error";

interface BackendStatus {
  status: Status;
  ready: boolean;
}

type Listener = () => void;

let status: BackendStatus = { status: "starting", ready: false };
const listeners = new Set<Listener>();
let pollTimer: ReturnType<typeof setInterval> | null = null;
let polling = false;

// Shared deferred: all callers of waitForReady() share one promise.
let readyResolve: (() => void) | null = null;
let readyReject: ((err: Error) => void) | null = null;
let readyPromise: Promise<void> | null = null;
let readyFulfilled = false;

function notify() {
  listeners.forEach((l) => {
    try {
      l();
    } catch {}
  });
}

function createReadyPromise(timeoutMs: number): Promise<void> {
  if (readyPromise && !readyFulfilled) return readyPromise;
  readyFulfilled = false;
  readyPromise = new Promise<void>((resolve, reject) => {
    readyResolve = resolve;
    readyReject = reject;
    if (status.ready) {
      readyFulfilled = true;
      resolve();
    }
  });
  if (timeoutMs > 0) {
    const timer = setTimeout(() => {
      if (!readyFulfilled) {
        readyFulfilled = true;
        readyReject?.(
          new Error(`Backend not ready after ${timeoutMs}ms — status: ${status.status}`),
        );
        // Reset so a future call creates a fresh promise.
        readyPromise = null;
        readyResolve = null;
        readyReject = null;
      }
    }, timeoutMs);
    readyPromise.finally(() => clearTimeout(timer));
  }
  return readyPromise;
}

async function pollOnce() {
  try {
    const res = await fetch(`${STATUS_BASE}/desktop/status`);
    if (res.ok) {
      const data = await res.json();
      const newStatus: Status = data.status;
      const newReady = READY_SET.has(newStatus);
      const wasReady = status.ready;
      status = { status: newStatus, ready: newReady };

      // If we were ready and now we're not, re-arm the gate for
      // callers waiting on the next ready (backend restart).
      if (wasReady && !newReady) {
        readyPromise = null;
        readyResolve = null;
        readyReject = null;
        readyFulfilled = false;
      }

      // If we just became ready and there's an unfulfilled promise, resolve it.
      if (newReady && !wasReady && readyResolve && !readyFulfilled) {
        readyFulfilled = true;
        readyResolve();
        readyPromise = null;
        readyResolve = null;
        readyReject = null;
      }

      notify();
    }
  } catch {
    // Network error during poll — status stays as-is; next poll will retry.
  }
}

function startPolling() {
  if (polling) return;
  polling = true;
  pollOnce(); // immediate first poll
  pollTimer = setInterval(pollOnce, POLL_MS);
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  polling = false;
}

function subscribe(l: Listener): () => void {
  listeners.add(l);
  return () => {
    listeners.delete(l);
    if (listeners.size === 0) stopPolling();
  };
}

function getStatus(): BackendStatus {
  return status;
}

/**
 * Wait until the backend is ready or the timeout fires.
 * Returns immediately if already ready.
 * Calls that arrive before start() will see status="starting" and await normally.
 */
export function waitForReady(timeoutMs = 30_000): Promise<void> {
  if (status.ready) return Promise.resolve();
  return createReadyPromise(timeoutMs);
}

/**
 * Start polling /desktop/status.  Call once at App mount.
 * Safe to call multiple times (idempotent).
 */
export function startStatusPolling() {
  startPolling();
}

/**
 * Stop polling.  Called at App teardown.
 */
export function stopStatusPolling() {
  stopPolling();
}

/**
 * React hook — re-renders on status change.
 */
export function useBackendStatus(): BackendStatus {
  return useSyncExternalStore(subscribe, getStatus);
}

/**
 * Reset all internal state.  Used by tests.
 */
export function _resetForTests() {
  status = { status: "starting", ready: false };
  readyPromise = null;
  readyResolve = null;
  readyReject = null;
  readyFulfilled = false;
  stopPolling();
}

/**
 * Non-hook accessor for components that don't need re-render.
 */
export { getStatus as getStatusSnapshot };

/**
 * Subscribe to backend status changes.
 * Returns an unsubscribe function.
 * Used by AioStore to detect ready→not-ready→ready transitions.
 */
export { subscribe as subscribeStatusChange };
