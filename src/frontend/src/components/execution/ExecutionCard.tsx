import { useState, useCallback } from "react";
import type { ExecutionState } from "./types";
import ExecutionHeader from "./ExecutionHeader";
import ExecutionSummary from "./ExecutionSummary";
import ExecutionThread from "./ExecutionThread";
import ExecutionLogs from "./ExecutionLogs";
import ExecutionActions from "./ExecutionActions";
import ExecutionResult from "./ExecutionResult";
import PermissionCard from "./PermissionCard";
import RecoveryCard from "./RecoveryCard";
import ExecutionFooter from "./ExecutionFooter";
import type { Action } from "./ExecutionActions";

export interface ExecutionCardProps {
  execution: ExecutionState;
  expanded?: boolean;
  onToggle?: (expanded: boolean) => void;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  onRetry?: () => void;
  onRetryAll?: () => void;
  onContinue?: () => void;
  onSkipStep?: () => void;
  onPermissionAllowOnce?: () => void;
  onPermissionAlwaysAllow?: () => void;
  onPermissionDeny?: () => void;
}

function ExecutionCard({
  execution, expanded: externalExpanded, onToggle: externalOnToggle,
  onPause, onResume, onCancel, onRetry, onRetryAll, onContinue, onSkipStep,
  onPermissionAllowOnce, onPermissionAlwaysAllow, onPermissionDeny,
}: ExecutionCardProps) {
  const [internalExpanded, setInternalExpanded] = useState(true);
  const isControlled = externalExpanded !== undefined;
  const expanded = isControlled ? externalExpanded : internalExpanded;

  const handleToggle = useCallback(() => {
    const next = !expanded;
    if (isControlled) {
      externalOnToggle?.(next);
    } else {
      setInternalExpanded(next);
    }
  }, [expanded, isControlled, externalOnToggle]);

  const isRunning = execution.status === "running" || execution.status === "streaming" || execution.status === "planning" || execution.status === "waiting" || execution.status === "retrying" || execution.status === "queued";

  const isTerminal = execution.status === "completed" || execution.status === "failed" || execution.status === "cancelled";

  const mainActions: Action[] = [];
  if (isRunning) {
    if (onPause) mainActions.push({ id: "pause", label: "Pause", onClick: onPause });
    if (onCancel) mainActions.push({ id: "cancel", label: "Cancel", variant: "danger", onClick: onCancel });
  }
  if (execution.status === "paused" && onResume) {
    mainActions.push({ id: "resume", label: "Resume", variant: "primary", onClick: onResume });
    if (onCancel) mainActions.push({ id: "cancel", label: "Cancel", variant: "danger", onClick: onCancel });
  }
  if (isTerminal && onRetry) {
    mainActions.push({ id: "retry", label: "Retry", variant: "primary", onClick: onRetry });
  }

  const durationMs = execution.durationMs || (execution.completedAt && execution.startedAt
    ? new Date(execution.completedAt).getTime() - new Date(execution.startedAt).getTime()
    : undefined);

  return (
    <div
      className={`pr-exec-card ${isRunning ? "pr-exec-card-running" : ""} ${execution.status === "completed" ? "pr-exec-card-completed" : ""} ${execution.status === "failed" ? "pr-exec-card-failed" : ""}`}
      role="region"
      aria-label={`Execution: ${execution.objective}`}
    >
      <ExecutionHeader
        objective={execution.objective}
        status={execution.status}
        startedAt={execution.startedAt}
        completedAt={execution.completedAt}
        durationMs={durationMs}
        running={isRunning}
        expanded={expanded}
        onToggle={handleToggle}
      />

      {!expanded && isTerminal && (
        <div className="pr-exec-card-summary">
          <ExecutionSummary
            objective={execution.objective}
            status={execution.status}
            durationMs={durationMs}
            result={execution.result}
          />
        </div>
      )}

      {expanded && (
        <div className="pr-exec-card-body">
          {execution.nodes.length > 0 && (
            <ExecutionThread nodes={execution.nodes} />
          )}

          {execution.permission && onPermissionAllowOnce && (
            <PermissionCard
              permission={execution.permission}
              onAllowOnce={onPermissionAllowOnce}
              onAlwaysAllow={onPermissionAlwaysAllow || onPermissionAllowOnce}
              onDeny={onPermissionDeny || (() => {})}
            />
          )}

          {execution.error && onRetry && (
            <RecoveryCard
              error={execution.error}
              onRetry={onRetry}
              onRetryAll={onRetryAll}
              onContinue={onContinue}
              onSkip={onSkipStep}
              onCancel={onCancel}
            />
          )}

          {execution.result && isTerminal && (
            <ExecutionResult result={execution.result} />
          )}

          <ExecutionActions actions={mainActions} />

          {execution.logs.length > 0 && (
            <ExecutionLogs logs={execution.logs} />
          )}
        </div>
      )}

      <ExecutionFooter />
    </div>
  );
}

export default ExecutionCard;
