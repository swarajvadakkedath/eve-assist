import type { ExecutionSession } from "../execution/session/types";
import { getStatusGroup } from "./types";
import ActivityBadge from "./ActivityBadge";

export interface ActivityItemProps {
  session: ExecutionSession;
  onSelect?: (sessionId: string) => void;
}

function formatDuration(ms?: number): string {
  if (!ms) return "";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = ((ms % 60000) / 1000).toFixed(0);
  return `${m}m ${s}s`;
}

function ActivityItem({ session, onSelect }: ActivityItemProps) {
  const group = getStatusGroup(session.status);
  const isActive = group === "running";

  return (
    <div
      className={`pr-activity-item ${isActive ? "pr-activity-item-active" : ""} ${session.status === "failed" ? "pr-activity-item-failed" : ""}`}
      role="listitem"
      aria-label={`${session.title} - ${session.status}`}
    >
      <button
        className="pr-activity-item-main"
        onClick={() => onSelect?.(session.id)}
        aria-label={`Inspect ${session.title}`}
      >
        <div className="pr-activity-item-header">
          <ActivityBadge status={session.status} />
          <span className="pr-activity-item-title">{session.title}</span>
        </div>
        <div className="pr-activity-item-meta">
          <span className="pr-activity-item-cap">
            {[...new Set(session.steps.map(s => s.capability.split(".")[0]))].slice(0, 3).join(", ")}
          </span>
          {session.durationMs !== undefined && (
            <span className="pr-activity-item-duration">{formatDuration(session.durationMs)}</span>
          )}
          <span className="pr-activity-item-steps">{session.steps.length} step{session.steps.length !== 1 ? "s" : ""}</span>
        </div>
      </button>
    </div>
  );
}

export default ActivityItem;
