import { useState, useEffect, useCallback } from "react";
import { api } from "../../services/api";

interface ToolInfo {
  id: string;
  name: string;
  description: string;
  permission_level: number;
  parameters: Record<string, unknown>;
  requires_confirmation?: boolean;
  tags?: string[];
  capabilities?: string[];
}

interface ToolCenterPanelProps {
  onClose: () => void;
}

const CATEGORY_ICONS: Record<string, string> = {
  filesystem: "📁",
  search: "🔍",
  clipboard: "📋",
  archive: "📦",
  system: "⚙",
  general: "🔧",
};

const CATEGORY_LABELS: Record<string, string> = {
  filesystem: "File Toolkit",
  search: "Search Toolkit",
  clipboard: "Clipboard Toolkit",
  archive: "Archive Toolkit",
  system: "System",
  general: "General",
};

const PERMISSION_LABELS: Record<number, string> = {
  0: "Read",
  1: "Safe",
  2: "Workspace",
  3: "Sensitive",
};

const PERMISSION_COLORS: Record<number, string> = {
  0: "#22c55e",
  1: "#3b82f6",
  2: "#f59e0b",
  3: "#ef4444",
};

export default function ToolCenterPanel({ onClose }: ToolCenterPanelProps) {
  const [categories, setCategories] = useState<Record<string, ToolInfo[]>>({});
  const [totalTools, setTotalTools] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCat, setExpandedCat] = useState<string | null>(null);
  const [executeResult, setExecuteResult] = useState<{ toolId: string; result: any; error?: string } | null>(null);
  const [executing, setExecuting] = useState<string | null>(null);

  const fetchTools = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.tools.list();
      const tools: ToolInfo[] = res.tools || [];
      const grouped: Record<string, ToolInfo[]> = {};
      for (const t of tools) {
        const cat = t.category || "general";
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push(t);
      }
      setCategories(grouped);
      setTotalTools(tools.length);
    } catch (err: any) {
      setError(err.message || "Failed to load tools");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  const handleExecute = async (toolId: string) => {
    setExecuting(toolId);
    setExecuteResult(null);
    try {
      const result = await api.tools.execute(toolId, {});
      setExecuteResult({ toolId, result });
    } catch (err: any) {
      setExecuteResult({ toolId, result: null, error: err.message });
    } finally {
      setExecuting(null);
    }
  };

  const sortedCategories = Object.entries(categories).sort(
    ([a], [b]) => {
      const order = ["filesystem", "search", "clipboard", "archive", "system", "general"];
      return order.indexOf(a) - order.indexOf(b);
    }
  );

  return (
    <div className="settings-panel-overlay" onClick={onClose}>
      <div className="settings-panel settings-panel-wide" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Tool Center</h2>
          <span className="tool-count-badge">{totalTools} tools</span>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>

        <div className="settings-body">
          {error && <div className="plugin-error">{error}</div>}

          {loading ? (
            <div className="loading-skeleton">Loading tools...</div>
          ) : totalTools === 0 ? (
            <div className="empty-state">
              <h3>No tools available</h3>
              <p>Tools are registered by built-in and plugin systems.</p>
            </div>
          ) : (
            <div className="tool-categories">
              {sortedCategories.map(([cat, tools]) => (
                <div key={cat} className="tool-category">
                  <div
                    className="tool-category-header"
                    onClick={() => setExpandedCat(expandedCat === cat ? null : cat)}
                  >
                    <span className="tool-category-icon">
                      {CATEGORY_ICONS[cat] || "🔧"}
                    </span>
                    <span className="tool-category-name">
                      {CATEGORY_LABELS[cat] || cat}
                    </span>
                    <span className="tool-category-count">{tools.length}</span>
                    <span className="tool-category-expand">
                      {expandedCat === cat ? "▼" : "▶"}
                    </span>
                  </div>

                  {expandedCat === cat && (
                    <div className="tool-list">
                      {tools.map((tool) => (
                        <div key={tool.id} className="tool-card">
                          <div className="tool-card-header">
                            <div className="tool-card-info">
                              <strong className="tool-name">{tool.name}</strong>
                              <code className="tool-id">{tool.id}</code>
                            </div>
                            <span
                              className="tool-permission-badge"
                              style={{
                                backgroundColor: PERMISSION_COLORS[tool.permission_level] || "#6b7280",
                              }}
                              title={`Permission: ${PERMISSION_LABELS[tool.permission_level] || tool.permission_level}`}
                            >
                              {PERMISSION_LABELS[tool.permission_level] || `L${tool.permission_level}`}
                            </span>
                          </div>

                          {tool.description && (
                            <p className="tool-card-desc">{tool.description}</p>
                          )}

                          {tool.tags && tool.tags.length > 0 && (
                            <div className="tool-tags">
                              {tool.tags.map((tag) => (
                                <span key={tag} className="tag-badge">{tag}</span>
                              ))}
                            </div>
                          )}

                          {tool.parameters && Object.keys(tool.parameters).length > 0 && (
                            <div className="tool-params">
                              <details>
                                <summary>Parameters ({Object.keys(tool.parameters).length})</summary>
                                <div className="tool-params-list">
                                  {Object.entries(tool.parameters).map(([key, val]: any) => (
                                    <div key={key} className="tool-param-item">
                                      <code>{key}</code>
                                      <span className="tool-param-type">{val.type}</span>
                                      {val.description && (
                                        <span className="tool-param-desc">{val.description}</span>
                                      )}
                                      {val.default !== undefined && (
                                        <span className="tool-param-default">
                                          = {String(val.default)}
                                        </span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </details>
                            </div>
                          )}

                          {tool.capabilities && tool.capabilities.length > 0 && (
                            <div className="tool-capabilities">
                              {tool.capabilities.map((cap: string) => (
                                <span key={cap} className="capability-pill">{cap}</span>
                              ))}
                            </div>
                          )}

                          <div className="tool-card-actions">
                            <button
                              className="btn btn-sm btn-primary"
                              onClick={() => handleExecute(tool.id)}
                              disabled={executing === tool.id}
                            >
                              {executing === tool.id ? "..." : "Execute"}
                            </button>
                          </div>

                          {executeResult && executeResult.toolId === tool.id && (
                            <div className={`tool-execute-result ${executeResult.error ? "result-error" : "result-success"}`}>
                              {executeResult.error ? (
                                <span>Error: {executeResult.error}</span>
                              ) : (
                                <pre>{JSON.stringify(executeResult.result, null, 2)}</pre>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
