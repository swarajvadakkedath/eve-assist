import type { ExecutionNodeStatus } from "./types";
import ExecutionBadge from "./ExecutionBadge";
import ExecutionDuration from "./ExecutionDuration";

export interface ExecutionHeaderProps {
  objective: string;
  status: ExecutionNodeStatus;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  running?: boolean;
  expanded: boolean;
  onToggle: () => void;
}

function ExecutionHeader({
  objective, status, startedAt, completedAt, durationMs, running, expanded, onToggle,
}: ExecutionHeaderProps) {
  return (
    <button
      className="pr-exec-card-header"
      onClick={onToggle}
      aria-expanded={expanded}
      aria-label={`${objective} - ${status}`}
    >
      <div className="pr-exec-card-header-left">
        <svg className="pr-exec-card-header-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        <span className="pr-exec-card-header-title">{objective}</span>
      </div>
      <div className="pr-exec-card-header-right">
        <ExecutionBadge status={status} compact />
        <ExecutionDuration startedAt={startedAt} completedAt={completedAt} durationMs={durationMs} running={running} />
        <svg
          className={`pr-exec-card-header-chevron ${expanded ? "pr-exec-card-header-chevron-open" : ""}`}
          width="16" height="16" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </div>
    </button>
  );
}

export default ExecutionHeader;
