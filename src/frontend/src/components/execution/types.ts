export type ExecutionNodeStatus =
  | "pending" | "queued" | "planning" | "running" | "streaming"
  | "waiting" | "waiting_for_permission" | "retrying" | "paused"
  | "cancelled" | "completed" | "failed" | "skipped" | "partial_success";

export type ProgressType = "indeterminate" | "percentage" | "steps" | "files" | "tokens" | "bytes" | "time" | "custom";

export interface ExecutionProgress {
  type: ProgressType;
  value?: number;
  max?: number;
  current?: number;
  label?: string;
}

export interface ExecutionNode {
  id: string;
  capability: string;
  label: string;
  status: ExecutionNodeStatus;
  progress?: ExecutionProgress;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  error?: string;
  isOptional?: boolean;
}

export interface ExecutionLogEntry {
  timestamp: string;
  level: "info" | "warn" | "error" | "debug";
  message: string;
  source?: string;
}

export interface PermissionRequest {
  id: string;
  capability: string;
  description: string;
  level: number;
}

export interface ExecutionResultData {
  success: boolean;
  summary: string;
  output?: string;
  warnings?: string[];
  errors?: string[];
  durationMs: number;
  taskCount: number;
  completedCount: number;
  failedCount: number;
  toolsExecuted?: string[];
  capabilitiesUsed?: string[];
}

export interface ExecutionState {
  id: string;
  objective: string;
  status: ExecutionNodeStatus;
  nodes: ExecutionNode[];
  progress: ExecutionProgress;
  logs: ExecutionLogEntry[];
  result?: ExecutionResultData;
  permission?: PermissionRequest;
  error?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  owner?: string;
  priority?: number;
  conversationId?: string;
}
