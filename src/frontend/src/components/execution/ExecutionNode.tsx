import type { ExecutionNode as NodeData } from "./types";
import { getNodeAriaLabel } from "./nodeConfig";
import ExecutionProgress from "./ExecutionProgress";

export interface ExecutionNodeProps {
  node: NodeData;
  isLast?: boolean;
}

const nodeClass: Record<string, string> = {
  planning: "pr-exec-node-planning",
  queued: "pr-exec-node-queued",
  running: "pr-exec-node-running",
  streaming: "pr-exec-node-streaming",
  waiting: "pr-exec-node-waiting",
  waiting_for_permission: "pr-exec-node-permission",
  retrying: "pr-exec-node-retrying",
  paused: "pr-exec-node-paused",
  cancelled: "pr-exec-node-cancelled",
  completed: "pr-exec-node-completed",
  success: "pr-exec-node-completed",
  failed: "pr-exec-node-failed",
  skipped: "pr-exec-node-skipped",
  partial_success: "pr-exec-node-partial",
  pending: "pr-exec-node-pending",
};

function renderIcon(status: string) {
  const cls = "pr-exec-node-icon";
  switch (status) {
    case "completed":
    case "success":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="2" fill="transparent" />
          <path d="M6 10l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "failed":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="2" fill="transparent" />
          <path d="M7 7l6 6M13 7l-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
    case "running":
    case "streaming":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="4" fill="currentColor">
            <animate attributeName="r" values="3;5;3" dur="1.5s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite" />
          </circle>
          <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" opacity="0.3" />
        </svg>
      );
    case "pending":
    case "queued":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      );
    case "planning":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 2" />
        </svg>
      );
    case "waiting_for_permission":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <rect x="5" y="8" width="10" height="9" rx="2" stroke="currentColor" strokeWidth="1.5" />
          <path d="M7 8V6a3 3 0 016 0v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="10" cy="13" r="1.5" fill="currentColor" />
        </svg>
      );
    case "retrying":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M14 6a5 5 0 10-4 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M14 2v4h-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "paused":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <rect x="6" y="4" width="2" height="12" rx="1" fill="currentColor" />
          <rect x="12" y="4" width="2" height="12" rx="1" fill="currentColor" />
        </svg>
      );
    case "cancelled":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" />
          <path d="M7 7l6 6M13 7l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
    case "skipped":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M8 6l5 4-5 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "partial_success":
      return (
        <svg className={cls} width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" />
          <path d="M10 6v5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          <circle cx="10" cy="14" r="1" fill="currentColor" />
        </svg>
      );
    default:
      return <span className={cls} aria-hidden="true">&bull;</span>;
  }
}

function ExecutionNode({ node, isLast }: ExecutionNodeProps) {
  const cls = `pr-exec-node ${nodeClass[node.status] || "pr-exec-node-pending"} ${isLast ? "pr-exec-node-last" : ""}`;
  const ariaLabel = getNodeAriaLabel(node.status, node.label);

  return (
    <div className={cls} role="listitem" aria-label={ariaLabel}>
      <div className="pr-exec-node-connector" aria-hidden="true">
        {!isLast && <div className="pr-exec-node-line" />}
      </div>
      {renderIcon(node.status)}
      <div className="pr-exec-node-body">
        <div className="pr-exec-node-label">{node.label}</div>
        {node.error && <div className="pr-exec-node-error">{node.error}</div>}
        {node.progress && <ExecutionProgress progress={node.progress} />}
      </div>
    </div>
  );
}

export default ExecutionNode;
