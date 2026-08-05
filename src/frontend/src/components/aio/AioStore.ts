import { useSyncExternalStore } from "react";
import {
  fetchProviders, fetchProviderHealth, fetchHealthHistory, fetchDiagnostics,
  fetchRouting, fetchCategories, fetchCommercialPolicy, fetchFreeModels,
  fetchErrors, fetchErrorStats, fetchErrorTimeline,
  testProvider, testAllProviders, refreshProviderModels,
} from "./aioApi";
import { waitForReady, getStatusSnapshot, subscribeStatusChange } from "../../services/statusStore";
import type {
  AioProvider, AioHealthEntry, AioHealthSnapshot, AioDiagnostics,
  AioRoutingEntry, AioRoutingCategory, AioActivityEvent, AioModel,
  AioErrorEvent, AioErrorStats, AioTimelineEvent,
} from "./aioTypes";

type Listener = () => void;

interface AioState {
  providers: AioProvider[];
  health: Record<string, AioHealthEntry>;
  healthHistory: Record<string, AioHealthSnapshot[]>;
  diagnostics: AioDiagnostics | null;
  routing: AioRoutingEntry[];
  categories: AioRoutingCategory[];
  policy: string;
  freeModels: AioModel[];
  activity: AioActivityEvent[];
  errors: AioErrorEvent[];
  errorStats: AioErrorStats | null;
  errorTimeline: AioTimelineEvent[];
  lastRefresh: number;
  lastHealthCheck: number;
  loading: boolean;
  error: string | null;
  version: number;
}

const MAX_ACTIVITY = 200;

let state: AioState = {
  providers: [],
  health: {},
  healthHistory: {},
  diagnostics: null,
  routing: [],
  categories: [],
  policy: "allow_paid",
  freeModels: [],
  activity: [],
  errors: [],
  errorStats: null,
  errorTimeline: [],
  lastRefresh: 0,
  lastHealthCheck: 0,
  loading: true,
  error: null,
  version: 0,
};

const listeners = new Set<Listener>();
let intervals: ReturnType<typeof setInterval>[] = [];
let activityId = 0;

function notify() {
  state = { ...state, version: state.version + 1 };
  listeners.forEach((l) => l());
}

function addActivity(
  type: AioActivityEvent["type"],
  message: string,
  severity: AioActivityEvent["severity"] = "info",
  provider_id?: string,
) {
  const event: AioActivityEvent = {
    id: `act-${++activityId}`,
    timestamp: Date.now(),
    type,
    message,
    severity,
    provider_id,
  };
  state.activity = [event, ...state.activity].slice(0, MAX_ACTIVITY);
}

function settled<T>(results: readonly PromiseSettledResult<unknown>[], idx: number, fallback: T): T {
  const r = results[idx];
  if (r && r.status === "fulfilled") return (r as PromiseFulfilledResult<T>).value;
  return fallback;
}

async function loadAll() {
  try {
    state.loading = true;
    notify();
    const results = await Promise.allSettled([
      fetchProviders(),
      fetchProviderHealth(),
      fetchHealthHistory(60),
      fetchDiagnostics(),
      fetchRouting(),
      fetchCategories(),
      fetchCommercialPolicy(),
      fetchFreeModels(),
      fetchErrors(100),
      fetchErrorStats(),
      fetchErrorTimeline(100),
    ]);
    const providers = settled(results, 0, []);
    const health = settled(results, 1, {});
    const history = settled(results, 2, {});
    const diagnostics = settled(results, 3, null);
    const routing = settled(results, 4, []);
    const categories = settled(results, 5, []);
    const policy = settled(results, 6, "allow_paid");
    const freeModels = settled(results, 7, []);
    const errorsResult = settled(results, 8, { errors: [], count: 0 });
    const errorStats = settled(results, 9, null);
    const timelineResult = settled(results, 10, { timeline: [] });
    const failures = results.filter((r) => r.status === "rejected").map((r) => (r as PromiseRejectedResult).reason);
    state = {
      ...state, providers, health, healthHistory: history, diagnostics,
      routing, categories, policy, freeModels,
      errors: errorsResult.errors || [],
      errorStats,
      errorTimeline: timelineResult.timeline || [],
      loading: false, error: failures.length > 0 ? `Partial load failure: ${failures.length} endpoint(s)` : null,
      lastRefresh: Date.now(), lastHealthCheck: Date.now(),
      version: state.version + 1,
    };
    if (failures.length > 0) {
      addActivity("warning", `Dashboard loaded with ${failures.length} degraded endpoint(s)`, "warning");
    } else {
      addActivity("background_task", "Dashboard initialized", "success");
    }
    notify();
  } catch (e) {
    state = { ...state, loading: false, error: String(e), version: state.version + 1 };
    addActivity("error", `Init failed: ${e}`, "error");
    notify();
  }
}

async function pollHealth() {
  try {
    const [health, history] = await Promise.all([fetchProviderHealth(), fetchHealthHistory(60)]);
    const prev = state.health;
    state.health = health;
    state.healthHistory = history;
    state.lastHealthCheck = Date.now();
    for (const [pid, h] of Object.entries(health)) {
      const old = prev[pid];
      if (old && old.state !== h.state) {
        if (h.state === "healthy" && old.state !== "healthy") {
          addActivity("provider_recovery", `${pid} recovered`, "success", pid);
        } else if (h.state !== "healthy" && old.state === "healthy") {
          addActivity("error", `${pid} health changed: ${h.state}`, "warning", pid);
        }
      }
    }
    notify();
  } catch {}
}

async function pollProviders() {
  try {
    state.providers = await fetchProviders();
    state.version++;
    notify();
  } catch {}
}

async function pollModels() {
  try {
    state.freeModels = await fetchFreeModels();
    state.version++;
    notify();
  } catch {}
}

async function pollDiagnostics() {
  try {
    state.diagnostics = await fetchDiagnostics();
    state.version++;
    notify();
  } catch {}
}

async function pollErrors() {
  try {
    const [errorsResult, errorStats, timelineResult] = await Promise.all([
      fetchErrors(100),
      fetchErrorStats(),
      fetchErrorTimeline(100),
    ]);
    state.errors = errorsResult.errors || [];
    state.errorStats = errorStats;
    state.errorTimeline = timelineResult.timeline || [];
    state.version++;
    notify();
  } catch {}
}

let statusUnsubscribe: (() => void) | null = null;
let lastStatusReady = false;

async function start() {
  if (intervals.length > 0) return;
  await waitForReady();
  loadAll();
  intervals = [
    setInterval(pollHealth, 10_000),
    setInterval(pollDiagnostics, 15_000),
    setInterval(pollProviders, 30_000),
    setInterval(pollErrors, 30_000),
    setInterval(pollModels, 60_000),
  ];
  // Re-run loadAll when the backend transitions back to ready after a restart.
  lastStatusReady = true;
  statusUnsubscribe = subscribeStatusChange(() => {
    const snap = getStatusSnapshot();
    if (snap.ready && !lastStatusReady) {
      loadAll(); // backend came back
    }
    lastStatusReady = snap.ready;
  });
}

function stop() {
  intervals.forEach(clearInterval);
  intervals = [];
  if (statusUnsubscribe) {
    statusUnsubscribe();
    statusUnsubscribe = null;
  }
  lastStatusReady = false;
}

function subscribe(l: Listener) {
  listeners.add(l);
  return () => listeners.delete(l);
}

function getState() {
  return state;
}

async function doTestProvider(pid: string) {
  addActivity("health_check", `Testing ${pid}...`, "info", pid);
  try {
    const r = await testProvider(pid);
    if (r.success) {
      addActivity("health_check", `${pid} connected (${r.latency_ms}ms)`, "success", pid);
    } else {
      addActivity("error", `${pid} failed: ${r.error}`, "error", pid);
    }
    await pollHealth();
    return r;
  } catch (e) {
    addActivity("error", `${pid} test error: ${e}`, "error", pid);
    return { success: false, error: String(e) };
  }
}

async function doTestAll() {
  addActivity("health_check", "Testing all providers...", "info");
  try {
    await testAllProviders();
    addActivity("health_check", "All providers tested", "success");
    await Promise.all([pollHealth(), pollProviders()]);
  } catch (e) {
    addActivity("error", `Test-all failed: ${e}`, "error");
  }
}

async function doRefreshModels(pid: string) {
  addActivity("model_refresh", `Refreshing models for ${pid}...`, "info", pid);
  try {
    await refreshProviderModels(pid);
    addActivity("model_refresh", `Models refreshed for ${pid}`, "success", pid);
    await pollProviders();
    await pollModels();
  } catch (e) {
    addActivity("error", `Model refresh failed for ${pid}: ${e}`, "error", pid);
  }
}

export const aioStore = {
  start,
  stop,
  subscribe,
  getState,
  testProvider: doTestProvider,
  testAll: doTestAll,
  refreshModels: doRefreshModels,
  forceRefresh: loadAll,
};

export function useAioStore(): AioState {
  return useSyncExternalStore(subscribe, getState);
}
