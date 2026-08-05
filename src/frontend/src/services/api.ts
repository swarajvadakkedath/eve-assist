import { waitForReady } from "./statusStore";

const isTauri = typeof window !== "undefined" && (!!(window as any).__TAURI_INTERNALS__ || !!(window as any).__TAURI__);
const BACKEND_PORT = 8456;
const API_BASE = isTauri
  ? `http://127.0.0.1:${BACKEND_PORT}/api/v1`
  : "/api/v1";

const BYPASS_PATHS = new Set([
  "/system/health",
  "/system/readiness",
  "/desktop/status",
  "/desktop/status/history",
  "/auth/token",
]);

export { API_BASE };

let _authToken: string | null = null;

async function getAuthToken(): Promise<string | null> {
  if (_authToken) return _authToken;
  try {
    const res = await fetch(`${API_BASE}/auth/token`);
    if (res.ok) {
      const data = await res.json();
      _authToken = data.token;
      return _authToken;
    }
  } catch {
    // Token fetch failed — server may not require auth yet
  }
  return null;
}

async function gateFor(path: string): Promise<void> {
  if (!BYPASS_PATHS.has(path)) {
    await waitForReady();
  }
}

export async function fetchApi(path: string, init?: RequestInit): Promise<Response> {
  await gateFor(path);
  const token = await getAuthToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (init?.headers) Object.assign(headers, init.headers);
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

async function request<T = any>(path: string, options?: RequestInit): Promise<T> {
  await gateFor(path);
  const token = await getAuthToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options?.headers) Object.assign(headers, options.headers);
  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  chat: {
    send: (content: string, conversationId?: string) =>
      request("/chat/message", {
        method: "POST",
        body: JSON.stringify({ content, conversation_id: conversationId }),
      }),
    history: (conversationId: string) =>
      request(`/chat/history?conversation_id=${conversationId}`),
    createConversation: (title?: string) =>
      request("/chat/conversation", {
        method: "POST",
        body: JSON.stringify({ title }),
      }),
    deleteConversation: (id: string) =>
      request(`/chat/conversation/${id}`, { method: "DELETE" }),
  },
  tools: {
    list: (category?: string) =>
      request(`/tools${category ? `?category=${category}` : ""}`),
    execute: (toolId: string, params: Record<string, unknown> = {}) =>
      request("/tools/execute", {
        method: "POST",
        body: JSON.stringify({ tool_id: toolId, params }),
      }),
    get: (toolId: string) => request(`/tools/${toolId}`),
    search: (query: string) => request(`/tools/search/${query}`),
  },
  capabilities: {
    list: (tag?: string) =>
      request(`/capabilities${tag ? `?tag=${tag}` : ""}`),
    search: (query: string, limit = 10) =>
      request("/capabilities/search", {
        method: "POST",
        body: JSON.stringify({ query, limit }),
      }),
    get: (id: string) => request(`/capabilities/${id}`),
    rank: (query: string, limit = 10) =>
      request("/capabilities/rank", {
        method: "POST",
        body: JSON.stringify({ query, limit }),
      }),
    recommend: (id: string, maxResults = 5) =>
      request(`/capabilities/${id}/recommend?max_results=${maxResults}`),
    filterByInterface: (interfaceName: string) =>
      request(`/capabilities/filter/by-interface/${interfaceName}`),
    filterByPermission: (minLevel = 0, maxLevel?: number) =>
      request(`/capabilities/filter/by-permission?min_level=${minLevel}${maxLevel !== undefined ? `&max_level=${maxLevel}` : ""}`),
  },
  settings: {
    get: () => request("/settings"),
    update: (settings: Record<string, unknown>) =>
      request("/settings", {
        method: "PUT",
        body: JSON.stringify({ settings }),
      }),
  },
  permissions: {
    pending: () => request("/permissions/pending"),
    grant: (requestId: string) =>
      request("/permissions/grant", {
        method: "POST",
        body: JSON.stringify({ request_id: requestId }),
      }),
    deny: (requestId: string, reason = "") =>
      request("/permissions/deny", {
        method: "POST",
        body: JSON.stringify({ request_id: requestId, reason }),
      }),
  },
  plugins: {
    list: (search?: string) =>
      request(`/plugins${search ? `?search=${encodeURIComponent(search)}` : ""}`),
    get: (id: string) => request(`/plugins/${id}`),
    install: (path: string, enable = true) =>
      request("/plugins/install", {
        method: "POST",
        body: JSON.stringify({ path, enable }),
      }),
    enable: (id: string) =>
      request(`/plugins/${id}/enable`, { method: "POST" }),
    disable: (id: string) =>
      request(`/plugins/${id}/disable`, { method: "POST" }),
    reload: (id: string) =>
      request(`/plugins/${id}/reload`, { method: "POST" }),
    remove: (id: string) =>
      request(`/plugins/${id}`, { method: "DELETE" }),
    health: () => request("/plugins/health"),
    getHealth: (id: string) => request(`/plugins/${id}/health`),
    getManifest: (id: string) => request(`/plugins/${id}/manifest`),
    getCapabilities: (id: string) => request(`/plugins/${id}/capabilities`),
    getPermissions: (id: string) => request(`/plugins/${id}/permissions`),
    getConfig: (id: string) => request(`/plugins/${id}/config`),
    updateConfig: (id: string, config: Record<string, unknown>) =>
      request(`/plugins/${id}/config`, {
        method: "PUT",
        body: JSON.stringify({ config }),
      }),
  },
  system: {
    health: () => request("/system/health"),
    status: () => request("/system/status"),
  },
  voice: {
    state: () => request("/voice/state"),
    config: () => request("/voice/config"),
    updateConfig: (config: Record<string, unknown>) =>
      request("/voice/config", {
        method: "PUT",
        body: JSON.stringify({ config }),
      }),
    startSession: (conversationId?: string) =>
      request("/voice/session/start", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId }),
      }),
    stopSession: () =>
      request("/voice/session/stop", { method: "POST" }),
    startListening: (language?: string) =>
      request("/voice/listen/start", {
        method: "POST",
        body: JSON.stringify({ language }),
      }),
    stopListening: () =>
      request("/voice/listen/stop", { method: "POST" }),
    speak: (text: string) =>
      request("/voice/speak", {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
    stopSpeaking: () =>
      request("/voice/speak/stop", { method: "POST" }),
    bargeIn: () =>
      request("/voice/barge-in", { method: "POST" }),
    inputDevices: () => request("/voice/devices/input"),
    outputDevices: () => request("/voice/devices/output"),
    voices: () => request("/voice/voices"),
  },
  vision: {
    capture: (target = "full_screen", monitorId = 0, region?: number[]) =>
      request("/vision/capture", {
        method: "POST",
        body: JSON.stringify({ target, monitor_id: monitorId, region }),
      }),
    analyze: (target = "full_screen") =>
      request("/vision/analyze", {
        method: "POST",
        body: JSON.stringify({ target }),
      }),
    analyzeUpload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return fetch(`${API_BASE}/vision/analyze-upload`, {
        method: "POST",
        body: formData,
      }).then((r) => {
        if (!r.ok) throw new Error(r.statusText);
        return r.json();
      });
    },
    observation: () => request("/vision/observation/latest"),
    startSession: () =>
      request("/vision/session/start", { method: "POST" }),
    stopSession: () =>
      request("/vision/session/stop", { method: "POST" }),
    config: () => request("/vision/config"),
    updateConfig: (config: Record<string, unknown>) =>
      request("/vision/config", {
        method: "PUT",
        body: JSON.stringify(config),
      }),
    providers: () => request("/vision/providers"),
    monitors: () => request("/vision/monitors"),
  },
  providers: {
    list: () => request("/providers"),
    get: (id: string) => request(`/providers/${id}`),
    availableTypes: () => request("/providers/available-types"),
    onboard: (data: { provider_type: string; api_key?: string; endpoint_url?: string; organization?: string; name?: string }) =>
      request("/providers/onboard", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    add: (data: Record<string, unknown>) =>
      request("/providers", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Record<string, unknown>) =>
      request(`/providers/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    remove: (id: string) =>
      request(`/providers/${id}`, { method: "DELETE" }),
    test: (id: string) =>
      request(`/providers/${id}/test`, { method: "POST" }),
    testAll: () =>
      request("/providers/test-all", { method: "POST" }),
    setDefault: (id: string) =>
      request(`/providers/${id}/default`, { method: "PUT" }),
    reorder: (ids: string[]) =>
      request("/providers/reorder", {
        method: "PUT",
        body: JSON.stringify({ provider_ids: ids }),
      }),
    models: {
      list: (id: string) => request(`/providers/${id}/models`),
      toggle: (id: string, modelId: string, enabled: boolean) =>
        request(`/providers/${id}/models`, {
          method: "PUT",
          body: JSON.stringify({ model_id: modelId, enabled }),
        }),
      refresh: (id: string) =>
        request(`/providers/${id}/models/refresh`, { method: "POST" }),
    },
  },
  routing: {
    get: () => request("/routing"),
    set: (routing: Record<string, unknown>[]) =>
      request("/routing", {
        method: "PUT",
        body: JSON.stringify({ routing }),
      }),
    diagnostics: () => request("/routing/diagnostics"),
    getCommercialPolicy: () => request("/routing/commercial-policy"),
    setCommercialPolicy: (policy: string) =>
      request("/routing/commercial-policy", {
        method: "PUT",
        body: JSON.stringify({ policy }),
      }),
  },
  desktop: {
    status: () => request("/desktop/status"),
    statusHistory: (limit = 50) => request(`/desktop/status/history?limit=${limit}`),
    settings: {
      get: () => request("/desktop/settings"),
      update: (settings: Record<string, unknown>) =>
        request("/desktop/settings", {
          method: "PUT",
          body: JSON.stringify({ settings }),
        }),
    },
    hotkeys: {
      get: () => request("/desktop/hotkeys"),
      update: (action: string, combination: string) =>
        request("/desktop/hotkeys", {
          method: "PUT",
          body: JSON.stringify({ action, combination }),
        }),
    },
    notifications: {
      history: (limit = 50) => request(`/desktop/notifications/history?limit=${limit}`),
      clear: () => request("/desktop/notifications/history", { method: "DELETE" }),
    },
    window: {
      state: () => request("/desktop/window/state"),
      show: () => request("/desktop/window/show", { method: "POST" }),
      hide: () => request("/desktop/window/hide", { method: "POST" }),
      minimize: () => request("/desktop/window/minimize", { method: "POST" }),
      restore: () => request("/desktop/window/restore", { method: "POST" }),
    },
    startup: {
      status: () => request("/desktop/startup"),
      enable: () => request("/desktop/startup/enable", { method: "POST" }),
      disable: () => request("/desktop/startup/disable", { method: "POST" }),
    },
  },
};
