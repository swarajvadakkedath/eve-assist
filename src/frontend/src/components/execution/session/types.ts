import type { ExecutionLogEntry, ExecutionNodeStatus, ExecutionResultData, ExecutionProgress } from "../types";

export type ExecutionSessionStatus =
  | "planning" | "running" | "waiting" | "permission" | "retrying"
  | "paused" | "completed" | "failed" | "cancelled" | "background";

export interface ExecutionStep {
  id: string;
  capability: string;
  label: string;
  status: ExecutionNodeStatus;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  error?: string;
}

export interface SessionLogEntry {
  timestamp: string;
  level: "info" | "warn" | "error" | "debug";
  message: string;
  source?: string;
}

export interface SessionMetadata {
  toolCount: number;
  fileCount: number;
  filesCreated: number;
  filesRead: number;
  filesModified: number;
  filesDeleted: number;
  tokensUsed: number;
  retryCount: number;
  permissionRequests: number;
}

export interface SessionResult {
  success: boolean;
  summary: string;
  durationMs: number;
  toolCount: number;
  completedCount: number;
  failedCount: number;
  output?: string;
  warnings?: string[];
  errors?: string[];
  toolsExecuted?: string[];
  capabilitiesUsed?: string[];
  filesAffected?: string[];
}

export interface ExecutionSession {
  id: string;
  conversationId: string;
  requestId: string;
  title: string;
  status: ExecutionSessionStatus;
  startedAt: string;
  completedAt?: string;
  durationMs?: number;
  steps: ExecutionStep[];
  logs: SessionLogEntry[];
  metadata: SessionMetadata;
  result?: SessionResult;
  error?: string;
  collapsed?: boolean;
}

export type ExecutionSessionEvent =
  | { type: "ExecutionStarted"; sessionId: string; request: string; conversationId: string; requestId: string }
  | { type: "PlanningStarted"; sessionId: string }
  | { type: "PlanningCompleted"; sessionId: string; steps: number }
  | { type: "StepScheduled"; sessionId: string; toolName: string; capability: string }
  | { type: "StepStarted"; sessionId: string; toolName: string }
  | { type: "StepUpdated"; sessionId: string; toolName: string; progress: number }
  | { type: "StepCompleted"; sessionId: string; toolName: string; success: boolean; duration: number }
  | { type: "PermissionRequested"; sessionId: string; capability: string; level: number }
  | { type: "PermissionGranted"; sessionId: string }
  | { type: "ExecutionCompleted"; sessionId: string; success: boolean; summary: string; durationMs: number }
  | { type: "ExecutionFailed"; sessionId: string; error: string }
  | { type: "ExecutionCancelled"; sessionId: string };

export const SESSION_STATUS_ORDER: ExecutionSessionStatus[] = [
  "planning", "running", "waiting", "permission", "retrying",
  "paused", "completed", "failed", "cancelled", "background",
];

export function mapNodeStatusToSessionStatus(status: ExecutionNodeStatus): ExecutionSessionStatus {
  switch (status) {
    case "planning": return "planning";
    case "running": case "streaming": case "queued": return "running";
    case "waiting": return "waiting";
    case "waiting_for_permission": return "permission";
    case "retrying": return "retrying";
    case "paused": return "paused";
    case "completed": return "completed";
    case "failed": return "failed";
    case "cancelled": return "cancelled";
    case "skipped": case "partial_success": return "background";
    default: return "running";
  }
}

export function shouldAutoCollapse(status: ExecutionSessionStatus): boolean {
  return status === "completed";
}

export function isSessionTerminal(status: ExecutionSessionStatus): boolean {
  return status === "completed" || status === "failed" || status === "cancelled";
}
