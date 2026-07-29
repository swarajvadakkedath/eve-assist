import type { ExecutionSessionEvent } from "./types";

export interface RawBackendEvent {
  type: string;
  data: Record<string, any>;
}

function normalizeSessionId(data: Record<string, any>, fallback: string): string {
  return data.session_id || data.execution_id || fallback;
}

export function adaptBackendEvent(
  raw: RawBackendEvent,
  sessionIdFallback: string,
  conversationId: string,
  requestId: string,
  requestContent: string,
): ExecutionSessionEvent | null {
  switch (raw.type) {
    case "planner_started":
      return {
        type: "ExecutionStarted",
        sessionId: sessionIdFallback,
        request: raw.data.request || requestContent,
        conversationId,
        requestId,
      };

    case "planner_completed":
      return {
        type: "PlanningCompleted",
        sessionId: sessionIdFallback,
        steps: raw.data.steps || 0,
      };

    case "tool_requested":
      return {
        type: "StepScheduled",
        sessionId: normalizeSessionId(raw.data, sessionIdFallback),
        toolName: raw.data.tool_name,
        capability: raw.data.capability || raw.data.tool_name,
      };

    case "tool_running":
      return {
        type: "StepStarted",
        sessionId: normalizeSessionId(raw.data, sessionIdFallback),
        toolName: raw.data.tool_name,
      };

    case "tool_completed":
      return {
        type: "StepCompleted",
        sessionId: normalizeSessionId(raw.data, sessionIdFallback),
        toolName: raw.data.tool_name,
        success: raw.data.success !== false,
        duration: raw.data.duration || 0,
      };

    case "status": {
      const message: string = raw.data.message || raw.data.status || "";
      if (message.includes("cancelled") || raw.data.status === "cancelled") {
        return { type: "ExecutionCancelled", sessionId: sessionIdFallback };
      }
      if (message.includes("executing") || message.includes("tool")) {
        return null;
      }
      return null;
    }

    case "error":
      return {
        type: "ExecutionFailed",
        sessionId: sessionIdFallback,
        error: raw.data.error || "Unknown error",
      };

    case "done":
      return null;

    default:
      return null;
  }
}

export function createCompletedEvent(
  sessionId: string,
  success: boolean,
  summary: string,
  durationMs: number,
): ExecutionSessionEvent {
  return {
    type: "ExecutionCompleted",
    sessionId,
    success,
    summary,
    durationMs,
  };
}
