import { useCallback } from "react";
import type { ExecutionSession } from "../execution/session/types";
import { isSessionTerminal } from "../execution/session/types";

export interface InspectorActionsProps {
  session: ExecutionSession;
  onClose: () => void;
}

function InspectorActions({ session, onClose }: InspectorActionsProps) {
  const terminal = isSessionTerminal(session.status);

  const handleCopySummary = useCallback(async () => {
    const lines = [
      `Session: ${session.title}`,
      `Status: ${session.status}`,
      `Duration: ${session.durationMs ? `${(session.durationMs / 1000).toFixed(1)}s` : "-"}`,
      `Tools: ${session.steps.length}`,
      session.result ? `Result: ${session.result.summary}` : "",
    ];
    try {
      await navigator.clipboard.writeText(lines.filter(Boolean).join("\n"));
    } catch { /* clipboard unavailable */ }
  }, [session]);

  return (
    <div className="pr-inspector-actions">
      <button className="pr-inspector-action-btn" onClick={handleCopySummary} aria-label="Copy session summary">
        Copy Summary
      </button>
      {terminal && session.result?.output && (
        <button className="pr-inspector-action-btn" onClick={() => {/* future: open result */}}>
          Open Result
        </button>
      )}
      <button className="pr-inspector-action-btn pr-inspector-action-close" onClick={onClose}>
        Close Inspector
      </button>
    </div>
  );
}

export default InspectorActions;
