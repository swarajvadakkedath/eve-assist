import type { ExecutionNodeStatus } from "./types";
import { getNodeLabel } from "./nodeConfig";

export interface ExecutionBadgeProps {
  status: ExecutionNodeStatus;
  compact?: boolean;
}

const badgeClass: Record<string, string> = {
  planning: "pr-exec-badge-planning",
  queued: "pr-exec-badge-queued",
  running: "pr-exec-badge-running",
  streaming: "pr-exec-badge-streaming",
  waiting: "pr-exec-badge-waiting",
  waiting_for_permission: "pr-exec-badge-permission",
  retrying: "pr-exec-badge-retrying",
  paused: "pr-exec-badge-paused",
  cancelled: "pr-exec-badge-cancelled",
  completed: "pr-exec-badge-completed",
  failed: "pr-exec-badge-failed",
  skipped: "pr-exec-badge-skipped",
  partial_success: "pr-exec-badge-partial",
  pending: "pr-exec-badge-pending",
};

function ExecutionBadge({ status, compact }: ExecutionBadgeProps) {
  const cls = `pr-exec-badge ${badgeClass[status] || "pr-exec-badge-pending"} ${compact ? "pr-exec-badge-compact" : ""}`;
  const label = getNodeLabel(status);

  return (
    <span className={cls} role="status" aria-label={label}>
      {compact ? null : label}
    </span>
  );
}

export default ExecutionBadge;
