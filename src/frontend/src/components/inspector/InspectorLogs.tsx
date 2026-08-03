import { useState, useCallback } from "react";
import type { ExecutionSession } from "../execution/session/types";

export interface InspectorLogsProps {
  session: ExecutionSession;
}

const LEVEL_CLASS: Record<string, string> = {
  info: "pr-inspector-log-info",
  warn: "pr-inspector-log-warn",
  error: "pr-inspector-log-error",
  debug: "pr-inspector-log-debug",
};

function InspectorLogs({ session }: InspectorLogsProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [filter, setFilter] = useState<string>("all");
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    const text = session.logs.map(l =>
      `[${l.timestamp}] [${l.level.toUpperCase()}]${l.source ? ` [${l.source}]` : ""} ${l.message}`
    ).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard unavailable */ }
  }, [session.logs]);

  const filtered = filter === "all"
    ? session.logs
    : session.logs.filter(l => l.level === filter);

  if (session.logs.length === 0) {
    return (
      <div className="pr-inspector-section" role="tabpanel" aria-label="Logs">
        <p className="pr-inspector-empty">No logs recorded for this session.</p>
      </div>
    );
  }

  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Logs">
      <div className="pr-inspector-logs-toolbar">
        <button
          className="pr-inspector-logs-toggle"
          onClick={() => setCollapsed(c => !c)}
          aria-expanded={!collapsed}
        >
          {collapsed ? "\u25B6" : "\u25BC"} {session.logs.length} logs
        </button>
        <div className="pr-inspector-logs-filters" role="group" aria-label="Log level filter">
          {(["all", "info", "warn", "error", "debug"] as const).map(level => (
            <button
              key={level}
              className={`pr-inspector-log-filter ${filter === level ? "pr-inspector-log-filter-active" : ""}`}
              onClick={() => setFilter(level)}
              aria-pressed={filter === level}
            >
              {level}
            </button>
          ))}
        </div>
        <button className="pr-inspector-logs-copy" onClick={handleCopy} aria-label="Copy logs">
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {!collapsed && (
        <div className="pr-inspector-logs-list" role="log" aria-label="Session logs" style={{ maxHeight: "400px", overflowY: "auto" }}>
          {filtered.map((entry, i) => (
            <div key={i} className={`pr-inspector-log-entry ${LEVEL_CLASS[entry.level] || ""}`}>
              <span className="pr-inspector-log-time">{entry.timestamp}</span>
              <span className="pr-inspector-log-level">{entry.level.toUpperCase()}</span>
              {entry.source && <span className="pr-inspector-log-source">[{entry.source}]</span>}
              <span className="pr-inspector-log-msg">{entry.message}</span>
            </div>
          ))}
          {filtered.length === 0 && <p className="pr-inspector-empty">No {filter} logs.</p>}
        </div>
      )}
    </div>
  );
}

export default InspectorLogs;
