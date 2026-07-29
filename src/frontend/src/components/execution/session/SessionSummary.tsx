import type { SessionResult } from "./types";

export interface SessionSummaryProps {
  result: SessionResult;
  durationMs?: number;
}

const fileIcons: Record<string, string> = {
  created: "+",
  read: "\u2192",
  modified: "~",
  deleted: "-",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = ((ms % 60000) / 1000).toFixed(0);
  return `${m}m ${s}s`;
}

function SessionSummary({ result, durationMs }: SessionSummaryProps) {
  const duration = durationMs || result.durationMs;

  return (
    <div className="pr-session-summary" role="status" aria-label={`Session ${result.success ? "completed" : "failed"}`}>
      <div className="pr-session-summary-header">
        <span className={`pr-session-summary-icon ${result.success ? "pr-session-summary-success" : "pr-session-summary-failed"}`} aria-hidden="true">
          {result.success ? "\u2713" : "\u2716"}
        </span>
        <span className="pr-session-summary-text">{result.summary}</span>
      </div>

      <div className="pr-session-summary-stats">
        {duration > 0 && (
          <div className="pr-session-summary-stat">
            <span className="pr-session-summary-stat-label">Duration</span>
            <span className="pr-session-summary-stat-value">{formatDuration(duration)}</span>
          </div>
        )}
        <div className="pr-session-summary-stat">
          <span className="pr-session-summary-stat-label">Tools</span>
          <span className="pr-session-summary-stat-value">{result.toolCount}</span>
        </div>
        {result.completedCount > 0 && (
          <div className="pr-session-summary-stat">
            <span className="pr-session-summary-stat-label">Completed</span>
            <span className="pr-session-summary-stat-value pr-session-summary-stat-ok">{result.completedCount}</span>
          </div>
        )}
        {result.failedCount > 0 && (
          <div className="pr-session-summary-stat">
            <span className="pr-session-summary-stat-label">Failed</span>
            <span className="pr-session-summary-stat-value pr-session-summary-stat-err">{result.failedCount}</span>
          </div>
        )}
      </div>

      {result.capabilitiesUsed && result.capabilitiesUsed.length > 0 && (
        <div className="pr-session-summary-capabilities">
          {result.capabilitiesUsed.map(cap => (
            <span key={cap} className="pr-session-summary-cap">{cap}</span>
          ))}
        </div>
      )}

      {result.errors && result.errors.length > 0 && (
        <div className="pr-session-summary-errors" role="alert">
          {result.errors.map((err, i) => (
            <div key={i} className="pr-session-summary-error">{err}</div>
          ))}
        </div>
      )}
    </div>
  );
}

export default SessionSummary;
