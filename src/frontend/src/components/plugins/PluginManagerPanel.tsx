import { useState, useEffect, useCallback } from "react";
import { api } from "../../services/api";

interface Plugin {
  id: string;
  scope: string;
  source: string;
  state: {
    status: string;
    health: {
      status: string;
      startup_time_ms: number;
      memory_usage_mb: number;
      error_count: number;
      restart_count: number;
      last_error: string;
      last_heartbeat: string | null;
      uptime_seconds: number;
    };
    error: string | null;
    started_at: string | null;
    stopped_at: string | null;
  };
  metadata: {
    id: string;
    name: string;
    version: string;
    author: string;
    description: string;
    license: string;
    homepage: string;
    repository: string;
    platforms: string[];
    tags: string[];
    category: string;
    icon: string;
    documentation: string;
  };
  capabilities: Array<{
    id: string;
    name: string;
    description: string;
    permission_level: number;
    timeout: number;
  }>;
  dependencies: Array<{
    plugin_id: string;
    version_spec: string;
    optional: boolean;
    resolved: boolean;
  }>;
}

interface PluginManagerPanelProps {
  onClose: () => void;
}

type ViewMode = "list" | "detail";

const STATUS_COLORS: Record<string, string> = {
  active: "#22c55e",
  degraded: "#f59e0b",
  failed: "#ef4444",
  stopped: "#6b7280",
  loading: "#3b82f6",
  loaded: "#3b82f6",
  disabled: "#9ca3af",
  discovered: "#8b5cf6",
  validated: "#8b5cf6",
  verified: "#8b5cf6",
  initializing: "#3b82f6",
  starting: "#3b82f6",
  stopping: "#f97316",
  unloaded: "#6b7280",
  removed: "#6b7280",
};

export default function PluginManagerPanel({ onClose }: PluginManagerPanelProps) {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [view, setView] = useState<ViewMode>("list");
  const [selectedPlugin, setSelectedPlugin] = useState<Plugin | null>(null);
  const [healthSummary, setHealthSummary] = useState<any>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchPlugins = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.plugins.list(search || undefined);
      setPlugins(res.plugins || []);
      const health = await api.plugins.health();
      setHealthSummary(health);
    } catch (err: any) {
      setError(err.message || "Failed to load plugins");
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchPlugins();
  }, [fetchPlugins]);

  const handleAction = async (action: string, id: string) => {
    setActionLoading(`${action}:${id}`);
    try {
      switch (action) {
        case "enable":
          await api.plugins.enable(id);
          break;
        case "disable":
          await api.plugins.disable(id);
          break;
        case "reload":
          await api.plugins.reload(id);
          break;
        case "remove":
          await api.plugins.remove(id);
          break;
      }
      await fetchPlugins();
      if (selectedPlugin?.id === id) {
        const updated = await api.plugins.get(id);
        setSelectedPlugin(updated);
      }
    } catch (err: any) {
      setError(`${action} failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const showDetail = async (plugin: Plugin) => {
    try {
      const detail = await api.plugins.get(plugin.id);
      setSelectedPlugin(detail);
      setView("detail");
    } catch {
      setSelectedPlugin(plugin);
      setView("detail");
    }
  };

  const getStatusColor = (status: string) => STATUS_COLORS[status.toLowerCase()] || "#6b7280";

  const formatUptime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
  };

  if (view === "detail" && selectedPlugin) {
    const p = selectedPlugin;
    const isActive = p.state?.status === "active";
    return (
      <div className="settings-panel-overlay" onClick={onClose}>
        <div className="settings-panel settings-panel-wide" onClick={(e) => e.stopPropagation()}>
          <div className="settings-header">
            <button className="btn btn-secondary" onClick={() => { setView("list"); setSelectedPlugin(null); }}>
              ← Back
            </button>
            <h2>{p.metadata?.name || p.id}</h2>
            <button className="btn-close" onClick={onClose}>×</button>
          </div>
          <div className="settings-body">
            <div className="plugin-detail-header">
              <span className="plugin-status-badge" style={{ backgroundColor: getStatusColor(p.state?.status || "") }}>
                {p.state?.status || "unknown"}
              </span>
              <span className="plugin-version">v{p.metadata?.version}</span>
              <span className="plugin-author">by {p.metadata?.author}</span>
            </div>

            {p.metadata?.description && (
              <div className="setting-group">
                <label>Description</label>
                <p className="plugin-description">{p.metadata.description}</p>
              </div>
            )}

            <div className="setting-group">
              <label>Plugin ID</label>
              <code className="plugin-id-display">{p.id}</code>
            </div>

            {p.metadata?.homepage && (
              <div className="setting-group">
                <label>Homepage</label>
                <a href={p.metadata.homepage} target="_blank" rel="noreferrer">{p.metadata.homepage}</a>
              </div>
            )}

            <div className="setting-group">
              <label>Health</label>
              <div className="plugin-health-stats">
                <div className="health-stat">
                  <span className="health-stat-label">Status</span>
                  <span className="health-stat-value" style={{ color: getStatusColor(p.state?.health?.status || "") }}>
                    {p.state?.health?.status || "N/A"}
                  </span>
                </div>
                <div className="health-stat">
                  <span className="health-stat-label">Uptime</span>
                  <span className="health-stat-value">{formatUptime(p.state?.health?.uptime_seconds || 0)}</span>
                </div>
                <div className="health-stat">
                  <span className="health-stat-label">Errors</span>
                  <span className="health-stat-value">{p.state?.health?.error_count || 0}</span>
                </div>
                <div className="health-stat">
                  <span className="health-stat-label">Restarts</span>
                  <span className="health-stat-value">{p.state?.health?.restart_count || 0}</span>
                </div>
                <div className="health-stat">
                  <span className="health-stat-label">Startup</span>
                  <span className="health-stat-value">{Math.round(p.state?.health?.startup_time_ms || 0)}ms</span>
                </div>
              </div>
            </div>

            {p.capabilities && p.capabilities.length > 0 && (
              <div className="setting-group">
                <label>Capabilities ({p.capabilities.length})</label>
                <div className="capability-list">
                  {p.capabilities.map((cap: any) => (
                    <div key={cap.id} className="capability-item">
                      <strong>{cap.name}</strong>
                      <span className="capability-perm">L{cap.permission_level}</span>
                      {cap.description && <p>{cap.description}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {p.dependencies && p.dependencies.length > 0 && (
              <div className="setting-group">
                <label>Dependencies ({p.dependencies.length})</label>
                <div className="dependency-list">
                  {p.dependencies.map((dep: any) => (
                    <div key={dep.plugin_id} className="dependency-item">
                      <span>{dep.plugin_id}</span>
                      {dep.version_spec && <code>{dep.version_spec}</code>}
                      <span className={`dep-status ${dep.resolved ? "resolved" : "unresolved"}`}>
                        {dep.resolved ? "✓" : "✗"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {p.metadata?.tags && p.metadata.tags.length > 0 && (
              <div className="setting-group">
                <label>Tags</label>
                <div className="tag-list">
                  {p.metadata.tags.map((tag: string) => (
                    <span key={tag} className="tag-badge">{tag}</span>
                  ))}
                </div>
              </div>
            )}

            {p.metadata?.license && (
              <div className="setting-group">
                <label>License</label>
                <span>{p.metadata.license}</span>
              </div>
            )}
          </div>
          <div className="settings-footer">
            <button
              className="btn btn-primary"
              onClick={() => handleAction(isActive ? "disable" : "enable", p.id)}
              disabled={actionLoading === `${isActive ? "disable" : "enable"}:${p.id}`}
            >
              {isActive ? "Disable" : "Enable"}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => handleAction("reload", p.id)}
              disabled={actionLoading === `reload:${p.id}`}
            >
              Reload
            </button>
            <button
              className="btn btn-danger"
              onClick={() => { if (confirm(`Remove plugin "${p.metadata?.name || p.id}"?`)) handleAction("remove", p.id); }}
              disabled={actionLoading === `remove:${p.id}`}
            >
              Remove
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="settings-panel-overlay" onClick={onClose}>
      <div className="settings-panel settings-panel-wide" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Plugin Manager</h2>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        <div className="plugin-manager-toolbar">
          <input
            type="text"
            className="plugin-search-input"
            placeholder="Search plugins by id, name, description, tags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {healthSummary && (
            <div className="health-summary">
              <span className="health-total">{healthSummary.total} total</span>
              <span className="health-active" style={{ color: "#22c55e" }}>{healthSummary.active} active</span>
              <span className="health-failed" style={{ color: "#ef4444" }}>{healthSummary.failed} failed</span>
              <span className="health-degraded" style={{ color: "#f59e0b" }}>{healthSummary.degraded} degraded</span>
              <span className="health-disabled" style={{ color: "#9ca3af" }}>{healthSummary.disabled} disabled</span>
            </div>
          )}
        </div>

        <div className="settings-body">
          {error && <div className="plugin-error">{error}</div>}

          {loading ? (
            <div className="loading-skeleton">Loading plugins...</div>
          ) : plugins.length === 0 ? (
            <div className="empty-state">
              <h3>No plugins installed</h3>
              <p>Install plugins by placing them in the plugins directory.</p>
            </div>
          ) : (
            <div className="plugin-list">
              {plugins.map((plugin) => {
                const isActionLoading = actionLoading?.endsWith(`:${plugin.id}`);
                return (
                  <div key={plugin.id} className="plugin-card" onClick={() => showDetail(plugin)}>
                    <div className="plugin-card-header">
                      <span
                        className="plugin-status-dot"
                        style={{ backgroundColor: getStatusColor(plugin.state?.status || "") }}
                      />
                      <div className="plugin-card-info">
                        <strong className="plugin-name">{plugin.metadata?.name || plugin.id}</strong>
                        <span className="plugin-id-label">{plugin.id}</span>
                      </div>
                      <span className="plugin-version-badge">v{plugin.metadata?.version}</span>
                    </div>
                    {plugin.metadata?.description && (
                      <p className="plugin-card-desc">{plugin.metadata.description}</p>
                    )}
                    <div className="plugin-card-meta">
                      <span>{plugin.metadata?.author}</span>
                      <span>{plugin.scope}</span>
                      {plugin.capabilities && <span>{plugin.capabilities.length} cap(s)</span>}
                    </div>
                    <div className="plugin-card-actions" onClick={(e) => e.stopPropagation()}>
                      {plugin.state?.status === "active" ? (
                        <button
                          className="btn btn-sm btn-secondary"
                          onClick={() => handleAction("disable", plugin.id)}
                          disabled={!!isActionLoading}
                        >
                          {isActionLoading ? "..." : "Disable"}
                        </button>
                      ) : plugin.state?.status === "disabled" ? (
                        <button
                          className="btn btn-sm btn-primary"
                          onClick={() => handleAction("enable", plugin.id)}
                          disabled={!!isActionLoading}
                        >
                          {isActionLoading ? "..." : "Enable"}
                        </button>
                      ) : null}
                      <button
                        className="btn btn-sm btn-secondary"
                        onClick={() => handleAction("reload", plugin.id)}
                        disabled={!!isActionLoading}
                      >
                        Reload
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}