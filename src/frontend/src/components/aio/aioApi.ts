import { fetchApi } from "../../services/api";
import type {
  AioProvider, AioModel, AioHealthEntry, AioHealthSnapshot, AioRoutingEntry,
  AioRoutingCategory, AioDiagnostics,
} from "./aioTypes";

async function get<T>(path: string): Promise<T> {
  const res = await fetchApi(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetchApi(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function put<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetchApi(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function fetchProviders(): Promise<AioProvider[]> {
  const data = await get<{ providers: AioProvider[] }>("/providers");
  return data.providers || [];
}

export async function fetchProviderHealth(): Promise<Record<string, AioHealthEntry>> {
  const data = await get<{ health: Record<string, AioHealthEntry> }>("/providers/health");
  return data.health || {};
}

export async function fetchHealthHistory(limit = 60): Promise<Record<string, AioHealthSnapshot[]>> {
  type HistoryResponse = { history: Record<string, AioHealthSnapshot[]> };
  const data = await get<HistoryResponse>(
    `/providers/health/history?limit=${limit}`
  );
  return data.history || {};
}

export async function fetchDiagnostics(): Promise<AioDiagnostics> {
  return get<AioDiagnostics>("/routing/diagnostics");
}

export async function fetchRouting(): Promise<AioRoutingEntry[]> {
  const data = await get<{ routing: AioRoutingEntry[] }>("/routing");
  return data.routing || [];
}

export async function fetchCategories(): Promise<AioRoutingCategory[]> {
  const data = await get<{ categories: AioRoutingCategory[] }>("/routing/categories");
  return data.categories || [];
}

export async function fetchCommercialPolicy(): Promise<string> {
  const data = await get<{ policy: string }>("/routing/commercial-policy");
  return data.policy || "allow_paid";
}

export async function fetchFreeModels(): Promise<AioModel[]> {
  const data = await get<{ models: AioModel[] }>("/providers/models/free");
  return data.models || [];
}

export async function testProvider(providerId: string) {
  return post<{ success: boolean; status?: string; latency_ms?: number; error?: string }>(
    `/providers/${providerId}/test`
  );
}

export async function testAllProviders() {
  return post<unknown>("/providers/test-all");
}

export async function refreshProviderModels(providerId: string) {
  return post<{ models: AioModel[] }>(`/providers/${providerId}/models/refresh`);
}

export async function refreshAllModels() {
  return post<unknown>("/providers/refresh-all-models");
}

export async function setCommercialPolicy(policy: string) {
  return put<{ policy: string }>("/routing/commercial-policy", { policy });
}

export async function setRouting(routing: AioRoutingEntry[]) {
  return put<{ routing: AioRoutingEntry[] }>("/routing", { routing });
}

export async function fetchSystemHealth() {
  return get<{ version?: string; status?: string; modules?: Record<string, string> }>("/system/health");
}
