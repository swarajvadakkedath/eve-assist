import type { ExecutionSessionStatus } from "../execution/session/types";

export interface ActivityBadgeProps {
  status: ExecutionSessionStatus;
  count?: number;
}

const STATUS_LABELS: Record<string, string> = {
  planning: "Planning",
  running: "Running",
  waiting: "Waiting",
  permission: "Permission",
  retrying: "Retrying",
  paused: "Paused",
  completed: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
  background: "BG",
};

function ActivityBadge({ status, count }: ActivityBadgeProps) {
  return (
    <span
      className={`pr-activity-badge pr-activity-badge-${status}`}
      role="status"
      aria-label={`Status: ${STATUS_LABELS[status] || status}`}
    >
      {count !== undefined ? (
        <span className="pr-activity-badge-count">{count}</span>
      ) : (
        <span className="pr-activity-badge-dot" aria-hidden="true" />
      )}
      <span className="pr-activity-badge-label">{STATUS_LABELS[status] || status}</span>
    </span>
  );
}

export default ActivityBadge;
