import { useState, useEffect, useCallback, useRef } from "react";
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

interface CommandState {
  toolId: string;
  command: string;
  status: "running" | "completed" | "failed" | "cancelled" | "timeout";
  output: string;
  error: string;
  exitCode: number | null;
  commandId: string | null;
}

const CATEGORY_ICONS: Record<string, string> = {
  filesystem: "📁",
  search: "🔍",
  clipboard: "📋",
  archive: "📦",
  developer: "💻",
  git: "🔀",
  content: "📝",
  system: "⚙",
  general: "🔧",
};

const CATEGORY_LABELS: Record<string, string> = {
  filesystem: "File Toolkit",
  search: "Search Toolkit",
  clipboard: "Clipboard Toolkit",
  archive: "Archive Toolkit",
  developer: "Developer Toolkit",
  git: "Git Toolkit",
  content: "Content Toolkit",
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

const CATEGORY_ORDER = ["filesystem", "search", "clipboard", "archive", "developer", "git", "content", "system", "general"];

export default function ToolCenterPanel({ onClose }: ToolCenterPanelProps) {
  const [categories, setCategories] = useState<Record<string, ToolInfo[]>>({});
  const [totalTools, setTotalTools] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCat, setExpandedCat] = useState<string | null>(null);
  const [executeResult, setExecuteResult] = useState<{ toolId: string; result: any; error?: string } | null>(null);
  const [executing, setExecuting] = useState<string | null>(null);
  const [commands, setCommands] = useState<Record<string, CommandState>>({});
  const [commandInputs, setCommandInputs] = useState<Record<string, string>>({});
  const [contentInputs, setContentInputs] = useState<Record<string, Record<string, string>>>({});
  const outputEndRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (outputEndRef.current) {
      outputEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [commands]);

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

  const handleContentExecute = async (toolId: string) => {
    const inputs = contentInputs[toolId] || {};
    const params: Record<string, any> = {};

    if (inputs.path) params.path = inputs.path;
    if (inputs.query) params.query = inputs.query;
    if (inputs.pattern) params.pattern = inputs.pattern;
    if (inputs.source) params.source = inputs.source;
    if (inputs.content) params.content = inputs.content;

    setExecuting(toolId);
    setExecuteResult(null);
    try {
      const result = await api.tools.execute(toolId, params);
      setExecuteResult({ toolId, result });
    } catch (err: any) {
      setExecuteResult({ toolId, result: null, error: err.message });
    } finally {
      setExecuting(null);
    }
  };

  const handleRunCommand = async (toolId: string) => {
    const command = (commandInputs[toolId] || "").trim();
    if (!command) return;

    const cmdKey = `${toolId}_${Date.now()}`;
    setCommands(prev => ({
      ...prev,
      [cmdKey]: { toolId, command, status: "running", output: "", error: "", exitCode: null, commandId: null },
    }));

    try {
      const result = await api.tools.execute(toolId, { command, timeout: 30 });
      const data = result.data || {};
      setCommands(prev => ({
        ...prev,
        [cmdKey]: {
          toolId,
          command,
          status: result.success ? "completed" : "failed",
          output: data.stdout || "",
          error: data.stderr || result.error || "",
          exitCode: data.exit_code ?? null,
          commandId: data.command_id || null,
        },
      }));
    } catch (err: any) {
      setCommands(prev => ({
        ...prev,
        [cmdKey]: { toolId, command, status: "failed", output: "", error: err.message, exitCode: null, commandId: null },
      }));
    }
  };

  const handleCancelCommand = async (commandId: string) => {
    try {
      await api.tools.execute("terminal.cancel_command", { command_id: commandId });
      setCommands(prev => {
        const updated = { ...prev };
        for (const [key, cmd] of Object.entries(updated)) {
          if (cmd.commandId === commandId && cmd.status === "running") {
            updated[key] = { ...cmd, status: "cancelled" };
          }
        }
        return updated;
      });
    } catch (err: any) {
      console.error("Cancel failed:", err);
    }
  };

  const handleCheckStatus = async (commandId: string) => {
    try {
      const result = await api.tools.execute("terminal.command_status", { command_id: commandId });
      setCommands(prev => {
        const updated = { ...prev };
        for (const [key, cmd] of Object.entries(updated)) {
          if (cmd.commandId === commandId) {
            updated[key] = { ...cmd, status: result.data?.status || cmd.status };
          }
        }
        return updated;
      });
    } catch (err: any) {
      console.error("Status check failed:", err);
    }
  };

  const isTerminalTool = (toolId: string) =>
    ["terminal.run_command", "terminal.stream_output", "powershell.run"].includes(toolId);

  const isCancelTool = (toolId: string) => toolId === "terminal.cancel_command";

  const isContentReadTool = (toolId: string) =>
    ["content.read_text", "content.read_json", "content.read_csv",
     "content.search_text", "content.search_regex",
     "content.extract_symbols", "content.list_functions",
     "content.list_classes", "content.count_lines",
     "content.detect_language", "content.parse_markdown",
     "content.markdown_outline", "content.extract_links",
     "content.search_code", "content.search_in_directory",
     "content.validate_json", "content.validate_yaml", "content.validate_xml"].includes(toolId);

  const isContentWriteTool = (toolId: string) =>
    ["content.write_text", "content.append_text", "content.replace_text",
     "content.write_json", "content.write_csv", "content.batch_replace"].includes(toolId);

  const sortedCategories = Object.entries(categories).sort(
    ([a], [b]) => CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b)
  );

  const renderCommandOutput = (cmdKey: string, cmd: CommandState) => {
    const statusColors: Record<string, string> = {
      running: "#3b82f6",
      completed: "#22c55e",
      failed: "#ef4444",
      cancelled: "#f59e0b",
      timeout: "#ef4444",
    };
    return (
      <div key={cmdKey} className="cmd-output-block">
        <div className="cmd-output-header">
          <code className="cmd-output-command">{cmd.command}</code>
          <span className="cmd-status-badge" style={{ backgroundColor: statusColors[cmd.status] || "#6b7280" }}>
            {cmd.status}
          </span>
          {cmd.status === "running" && cmd.commandId && (
            <button className="btn btn-sm btn-danger" onClick={() => handleCancelCommand(cmd.commandId!)}>
              Cancel
            </button>
          )}
          {cmd.exitCode !== null && (
            <span className="cmd-exit-code">exit: {cmd.exitCode}</span>
          )}
        </div>
        {cmd.output && (
          <pre className="cmd-output">{cmd.output}</pre>
        )}
        {cmd.error && (
          <pre className="cmd-output cmd-error">{cmd.error}</pre>
        )}
      </div>
    );
  };

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

                          {isCancelTool(tool.id) && (
                            <div className="tool-card-actions">
                              <p className="tool-usage-note">Use the Cancel button on running commands below.</p>
                            </div>
                          )}

                          {isTerminalTool(tool.id) && (
                            <div className="tool-command-input">
                              <div className="cmd-input-row">
                                <input
                                  type="text"
                                  className="cmd-input"
                                  placeholder="Enter command..."
                                  value={commandInputs[tool.id] || ""}
                                  onChange={(e) => setCommandInputs(prev => ({ ...prev, [tool.id]: e.target.value }))}
                                  onKeyDown={(e) => { if (e.key === "Enter") handleRunCommand(tool.id); }}
                                />
                                <button
                                  className="btn btn-sm btn-primary"
                                  onClick={() => handleRunCommand(tool.id)}
                                  disabled={!(commandInputs[tool.id] || "").trim()}
                                >
                                  Run
                                </button>
                              </div>
                              {Object.entries(commands)
                                .filter(([, cmd]) => cmd.toolId === tool.id)
                                .map(([key, cmd]) => renderCommandOutput(key, cmd))
                              }
                              <div ref={outputEndRef} />
                            </div>
                          )}

                          {isContentReadTool(tool.id) && (
                            <div className="tool-card-actions tool-card-inputs">
                              <div className="cmd-input-row">
                                {(tool.id.includes("_text") || tool.id.includes("_json") || tool.id.includes("_csv") || tool.id.includes("symbols") || tool.id.includes("_functions") || tool.id.includes("_classes") || tool.id.includes("count_lines") || tool.id.includes("detect_") || tool.id.includes("search_code")) && (
                                  <input
                                    type="text"
                                    className="cmd-input"
                                    placeholder="File path..."
                                    value={(contentInputs[tool.id] || {}).path || ""}
                                    onChange={(e) => setContentInputs(prev => ({ ...prev, [tool.id]: { ...prev[tool.id], path: e.target.value } }))}
                                  />
                                )}
                                {(tool.id.includes("search") || tool.id.includes("_text")) && (
                                  <input
                                    type="text"
                                    className="cmd-input"
                                    placeholder="Search query..."
                                    value={(contentInputs[tool.id] || {}).query || ""}
                                    onChange={(e) => setContentInputs(prev => ({ ...prev, [tool.id]: { ...prev[tool.id], query: e.target.value } }))}
                                  />
                                )}
                                {(tool.id.includes("validate_") || tool.id.includes("parse_") || tool.id.includes("extract_links") || tool.id.includes("outline")) && (
                                  <input
                                    type="text"
                                    className="cmd-input"
                                    placeholder="File path or source text..."
                                    value={(contentInputs[tool.id] || {}).source || ""}
                                    onChange={(e) => setContentInputs(prev => ({ ...prev, [tool.id]: { ...prev[tool.id], source: e.target.value } }))}
                                  />
                                )}
                                <button
                                  className="btn btn-sm btn-primary"
                                  onClick={() => handleContentExecute(tool.id)}
                                  disabled={executing === tool.id}
                                >
                                  {executing === tool.id ? "..." : "Run"}
                                </button>
                              </div>
                            </div>
                          )}

                          {isContentWriteTool(tool.id) && (
                            <div className="tool-card-actions">
                              <button
                                className="btn btn-sm btn-warning"
                                onClick={() => handleExecute(tool.id)}
                                disabled={executing === tool.id}
                              >
                                {executing === tool.id ? "..." : "Execute (requires confirmation)"}
                              </button>
                            </div>
                          )}

                          {!isTerminalTool(tool.id) && !isCancelTool(tool.id) && !isContentReadTool(tool.id) && !isContentWriteTool(tool.id) && (
                            <div className="tool-card-actions">
                              <button
                                className="btn btn-sm btn-primary"
                                onClick={() => handleExecute(tool.id)}
                                disabled={executing === tool.id}
                              >
                                {executing === tool.id ? "..." : "Execute"}
                              </button>
                            </div>
                          )}

                          {executeResult && executeResult.toolId === tool.id && !isTerminalTool(tool.id) && (
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
