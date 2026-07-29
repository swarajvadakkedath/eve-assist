import type { ExecutionSessionStatus } from "../execution/session/types";

export type ActivityFilter = "all" | "running" | "completed" | "failed" | "browser" | "memory" | "plugins" | "voice" | "vision" | "files";

export interface ActivityFilterOption {
  id: ActivityFilter;
  label: string;
}

export const ACTIVITY_FILTERS: ActivityFilterOption[] = [
  { id: "all", label: "All" },
  { id: "running", label: "Running" },
  { id: "completed", label: "Completed" },
  { id: "failed", label: "Failed" },
  { id: "browser", label: "Browser" },
  { id: "memory", label: "Memory" },
  { id: "plugins", label: "Plugins" },
  { id: "voice", label: "Voice" },
  { id: "vision", label: "Vision" },
  { id: "files", label: "Files" },
];

export const STATUS_GROUP: Record<string, ActivityFilter> = {
  planning: "running",
  running: "running",
  waiting: "running",
  permission: "running",
  retrying: "running",
  paused: "running",
  completed: "completed",
  failed: "failed",
  cancelled: "failed",
  background: "running",
};

export function getStatusGroup(status: ExecutionSessionStatus): ActivityFilter {
  return STATUS_GROUP[status] || "all";
}
