import { useState, useCallback } from "react";
import type { SessionLogEntry } from "./types";

export interface SessionLogsProps {
  logs: SessionLogEntry[];
  maxHeight?: string;
}

function SessionLogs({ logs, maxHeight = "240px" }: SessionLogsProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    const text = logs.map(l => `[${l.timestamp}] [${l.level.toUpperCase()}]${l.source ? ` [${l.source}]` : ""} ${l.message}`).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable
    }
  }, [logs]);

  if (logs.length === 0) return null;

  return (
    <div className="pr-session-logs" role="log" aria-label="Execution logs">
      <div className="pr-session-logs-header">
        <button
          className="pr-session-logs-toggle"
          onClick={() => setCollapsed(c => !c)}
          aria-expanded={!collapsed}
          aria-controls="session-logs-content"
        >
          {collapsed ? "\u25B6" : "\u25BC"} Logs ({logs.length})
        </button>
        <button
          className="pr-session-logs-copy"
          onClick={handleCopy}
          aria-label="Copy logs to clipboard"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      {!collapsed && (
        <div
          id="session-logs-content"
          className="pr-session-logs-content"
          style={{ maxHeight }}
          role="list"
        >
          {logs.map((entry, i) => (
            <div
              key={i}
              className={`pr-session-log-entry pr-session-log-${entry.level}`}
              role="listitem"
            >
              <span className="pr-session-log-time">{entry.timestamp}</span>
              <span className="pr-session-log-level">{entry.level.toUpperCase()}</span>
              {entry.source && <span className="pr-session-log-source">[{entry.source}]</span>}
              <span className="pr-session-log-msg">{entry.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default SessionLogs;
