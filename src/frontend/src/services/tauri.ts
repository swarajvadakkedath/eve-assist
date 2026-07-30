type TauriInvoke = (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;

export interface DesktopStatus {
  launcher_state: string;
  backend_healthy: boolean;
  backend_url: string;
  uptime: number;
}

export interface AppConfig {
  theme: string;
  backend_url: string;
  frontend_url: string;
  auto_start: boolean;
  dev_mode: boolean;
}

let _invoke: TauriInvoke | null = null;

function getInvoke(): TauriInvoke | null {
  if (_invoke) return _invoke;
  const w = window as unknown as Record<string, unknown>;
  if (w.__TAURI_INTERNALS__ || w.__TAURI__) {
    _invoke = (cmd: string, args?: Record<string, unknown>) => {
      const core = (w.__TAURI__ as Record<string, unknown>)?.core as
        | Record<string, unknown>
        | undefined;
      if (core?.invoke && typeof core.invoke === "function") {
        return (core.invoke as (cmd: string, args?: Record<string, unknown>) => Promise<unknown>)(cmd, args);
      }
      return Promise.reject(new Error("Tauri invoke not available"));
    };
  }
  return _invoke;
}

export function isTauri(): boolean {
  const w = window as unknown as Record<string, unknown>;
  return !!w.__TAURI_INTERNALS__ || !!w.__TAURI__;
}

export async function getStatus(): Promise<DesktopStatus> {
  const invoke = getInvoke();
  if (!invoke) throw new Error("not in Tauri context");
  return invoke("get_status") as Promise<DesktopStatus>;
}

export async function getHealth(): Promise<Record<string, unknown>> {
  const invoke = getInvoke();
  if (!invoke) throw new Error("not in Tauri context");
  return invoke("get_health") as Promise<Record<string, unknown>>;
}

export async function restartBackend(): Promise<boolean> {
  const invoke = getInvoke();
  if (!invoke) throw new Error("not in Tauri context");
  return invoke("restart_backend") as Promise<boolean>;
}

export async function shutdown(): Promise<void> {
  const invoke = getInvoke();
  if (!invoke) throw new Error("not in Tauri context");
  await invoke("shutdown");
}

export async function showNotification(title: string, body: string): Promise<void> {
  const invoke = getInvoke();
  if (!invoke) return;
  try {
    await invoke("show_notification", { title, body });
  } catch {
    // silently fail if not supported
  }
}

function isValidHttpUrl(s: string): boolean {
  try {
    const u = new URL(s);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch { return false; }
}

export async function openUrl(url: string): Promise<void> {
  if (!isValidHttpUrl(url)) return;
  const invoke = getInvoke();
  if (!invoke) {
    window.open(url, "_blank");
    return;
  }
  try {
    await invoke("open_url", { url });
  } catch {
    window.open(url, "_blank");
  }
}

export async function getAppConfig(): Promise<AppConfig> {
  const invoke = getInvoke();
  if (!invoke) throw new Error("not in Tauri context");
  return invoke("get_app_config") as Promise<AppConfig>;
}

export async function setAppConfig(key: string, value: unknown): Promise<boolean> {
  const invoke = getInvoke();
  if (!invoke) throw new Error("not in Tauri context");
  return invoke("set_app_config", { key, value }) as Promise<boolean>;
}
