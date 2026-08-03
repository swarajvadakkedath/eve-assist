import { useCallback } from "react";
import type { ExecutionSession } from "./types";
import { isSessionTerminal } from "./types";
import ExecutionCard from "../ExecutionCard";
import SessionSummary from "./SessionSummary";
import SessionLogs from "./SessionLogs";
import { getSessionStore } from "./ExecutionSessionStore";
import type { ExecutionState } from "../types";

export interface ExecutionSessionCardProps {
  session: ExecutionSession;
  onInspect?: (sessionId: string) => void;
}

function sessionToExecutionState(session: ExecutionSession): ExecutionState {
  const isRunning = session.status === "running" || session.status === "planning";
  return {
    id: session.id,
    objective: session.title,
    status: session.status === "permission" ? "waiting_for_permission"
      : session.status === "background" ? "running"
      : session.status as ExecutionState["status"],
    nodes: session.steps.map(s => ({
      id: s.id,
      capability: s.capability,
      label: s.label,
      status: s.status,
      startedAt: s.startedAt,
      completedAt: s.completedAt,
      durationMs: s.durationMs,
      error: s.error,
    })),
    progress: {
      type: "steps",
      current: session.steps.filter(s => s.status === "completed" || s.status === "failed").length,
      max: Math.max(session.steps.length, 1),
      label: isRunning ? "Running..." : undefined,
    },
    logs: session.logs.map(l => ({
      timestamp: l.timestamp,
      level: l.level,
      message: l.message,
      source: l.source,
    })),
    result: session.result ? {
      success: session.result.success,
      summary: session.result.summary,
      durationMs: session.result.durationMs,
      taskCount: session.result.toolCount,
      completedCount: session.result.completedCount,
      failedCount: session.result.failedCount,
      toolsExecuted: session.result.toolsExecuted,
      capabilitiesUsed: session.result.capabilitiesUsed,
      output: session.result.output,
      warnings: session.result.warnings,
      errors: session.result.errors,
    } : undefined,
    error: session.error,
    createdAt: session.startedAt,
    startedAt: session.startedAt,
    completedAt: session.completedAt,
    durationMs: session.durationMs,
    permission: session.status === "permission" ? {
      id: `perm-${session.id}`,
      capability: session.steps[0]?.capability || "",
      description: session.title,
      level: 1,
    } : undefined,
  };
}

function ExecutionSessionCard({ session, onInspect }: ExecutionSessionCardProps) {
  const store = getSessionStore();
  const terminal = isSessionTerminal(session.status);

  const handleToggle = useCallback(() => {
    store.toggleCollapse(session.id);
  }, [store, session.id]);

  const handleInspect = useCallback(() => {
    onInspect?.(session.id);
  }, [onInspect, session.id]);

  const execState = sessionToExecutionState(session);
  const showFloatingSummary = session.collapsed && terminal && session.result;

  return (
    <div
      className={`pr-session-card ${terminal ? "pr-session-card-terminal" : "pr-session-card-active"}`}
      role="region"
      aria-label={`Execution session: ${session.title}`}
      aria-busy={!terminal}
    >
      <div className="pr-session-card-inspect-wrapper">
        <ExecutionCard
          execution={execState}
          expanded={!session.collapsed}
          onToggle={handleToggle}
        />
        {onInspect && (
          <button
            className="pr-session-inspect-btn"
            onClick={handleInspect}
            aria-label={`Inspect ${session.title}`}
            title="Open inspector"
          >
            Inspect
          </button>
        )}
      </div>

      {showFloatingSummary && (
        <div className="pr-session-summary-wrapper">
          <SessionSummary result={session.result} durationMs={session.durationMs} />
        </div>
      )}

      {!session.collapsed && session.logs.length > 0 && (
        <SessionLogs logs={session.logs} />
      )}
    </div>
  );
}

export default ExecutionSessionCard;
