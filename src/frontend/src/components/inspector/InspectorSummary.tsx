import type { ExecutionSession } from "../execution/session/types";
import { isSessionTerminal } from "../execution/session/types";

export interface InspectorSummaryProps {
  session: ExecutionSession;
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString();
}

function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return "-";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = ((ms % 60000) / 1000).toFixed(0);
  return `${m}m ${s}s`;
}

const STATUS_LABELS: Record<string, string> = {
  planning: "Planning",
  running: "Running",
  waiting: "Waiting",
  permission: "Permission Required",
  retrying: "Retrying",
  paused: "Paused",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  background: "Background",
};

function InspectorSummary({ session }: InspectorSummaryProps) {
  const terminal = isSessionTerminal(session.status);
  const completedCount = session.steps.filter(s => s.status === "completed" || s.status === "success").length;
  const failedCount = session.steps.filter(s => s.status === "failed").length;

  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Summary">
      <div className="pr-inspector-summary-header">
        <h3 className="pr-inspector-summary-title">{session.title}</h3>
        <span className={`pr-inspector-status-badge pr-inspector-status-${session.status}`}>
          {STATUS_LABELS[session.status] || session.status}
        </span>
      </div>

      <div className="pr-inspector-summary-grid">
        <div className="pr-inspector-summary-item">
          <span className="pr-inspector-summary-label">Started</span>
          <span className="pr-inspector-summary-value">{formatDateTime(session.startedAt)}</span>
        </div>
        {session.completedAt && (
          <div className="pr-inspector-summary-item">
            <span className="pr-inspector-summary-label">Finished</span>
            <span className="pr-inspector-summary-value">{formatDateTime(session.completedAt)}</span>
          </div>
        )}
        <div className="pr-inspector-summary-item">
          <span className="pr-inspector-summary-label">Duration</span>
          <span className="pr-inspector-summary-value">{formatDuration(session.durationMs)}</span>
        </div>
        <div className="pr-inspector-summary-item">
          <span className="pr-inspector-summary-label">Tools</span>
          <span className="pr-inspector-summary-value">{session.steps.length}</span>
        </div>
        <div className="pr-inspector-summary-item">
          <span className="pr-inspector-summary-label">Capabilities</span>
          <span className="pr-inspector-summary-value">
            {[...new Set(session.steps.map(s => s.capability.split(".")[0]))].join(", ") || "-"}
          </span>
        </div>
        <div className="pr-inspector-summary-item">
          <span className="pr-inspector-summary-label">Files Changed</span>
          <span className="pr-inspector-summary-value">{session.metadata.fileCount}</span>
        </div>
      </div>

      {terminal && session.result && (
        <div className="pr-inspector-summary-result">
          <div className={`pr-inspector-summary-outcome ${session.result.success ? "pr-inspector-success" : "pr-inspector-failed"}`}>
            {session.result.success ? "Completed Successfully" : "Failed"}
          </div>
          {completedCount > 0 && <span>{completedCount} steps completed</span>}
          {failedCount > 0 && <span className="pr-inspector-failed">, {failedCount} failed</span>}
        </div>
      )}

      {session.error && (
        <div className="pr-inspector-error" role="alert">
          <span className="pr-inspector-error-label">Error:</span> {session.error}
        </div>
      )}
    </div>
  );
}

export default InspectorSummary;
