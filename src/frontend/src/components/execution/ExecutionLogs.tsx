import { useState, useRef, useEffect, useCallback } from "react";
import type { ExecutionLogEntry } from "./types";

export interface ExecutionLogsProps {
  logs: ExecutionLogEntry[];
  maxHeight?: number;
  defaultCollapsed?: boolean;
}

const levelClass: Record<string, string> = {
  info: "pr-exec-log-info",
  warn: "pr-exec-log-warn",
  error: "pr-exec-log-error",
  debug: "pr-exec-log-debug",
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

function ExecutionLogs({ logs, maxHeight = 200, defaultCollapsed = true }: ExecutionLogsProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [copied, setCopied] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length, collapsed]);

  const handleCopy = useCallback(async () => {
    try {
      const text = logs
        .map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`)
        .join("\n");
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  }, [logs]);

  const logCount = logs.length;

  return (
    <div className="pr-exec-logs">
      <button
        className="pr-exec-logs-toggle"
        onClick={() => setCollapsed((c) => !c)}
        aria-expanded={!collapsed}
        aria-controls="exec-logs-content"
      >
        <span>Logs ({logCount})</span>
        <span className="pr-exec-logs-toggle-icon">{collapsed ? "+" : "-"}</span>
      </button>
      {!collapsed && (
        <div className="pr-exec-logs-content" id="exec-logs-content" style={{ maxHeight }}>
          <button className="pr-exec-logs-copy" onClick={handleCopy} aria-label="Copy logs">
            {copied ? "Copied!" : "Copy"}
          </button>
          <div className="pr-exec-logs-list">
            {logs.map((entry, i) => (
              <div key={i} className={`pr-exec-log-entry ${levelClass[entry.level] || "pr-exec-log-info"}`}>
                <span className="pr-exec-log-time">{formatTime(entry.timestamp)}</span>
                <span className="pr-exec-log-level">{entry.level.toUpperCase()}</span>
                <span className="pr-exec-log-message">{entry.message}</span>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        </div>
      )}
    </div>
  );
}

export default ExecutionLogs;
