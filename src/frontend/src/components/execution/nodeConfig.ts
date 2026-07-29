import type { ExecutionNodeStatus } from "./types";

export interface NodeVisualConfig {
  label: string;
  animate: boolean;
}

export function getNodeLabel(status: ExecutionNodeStatus): string {
  const map: Record<string, string> = {
    planning: "Planning",
    queued: "Queued",
    running: "Running",
    streaming: "Streaming",
    waiting: "Waiting",
    waiting_for_permission: "Permission Required",
    retrying: "Retrying",
    paused: "Paused",
    cancelled: "Cancelled",
    completed: "Completed",
    failed: "Failed",
    skipped: "Skipped",
    partial_success: "Partial Success",
    pending: "Pending",
  };
  return map[status] || status;
}

export function getNodeAriaLabel(status: ExecutionNodeStatus, label: string): string {
  return `${label}: ${getNodeLabel(status)}`;
}
