import type { ExecutionSession } from "../execution/session/types";

export interface InspectorTimelineProps {
  session: ExecutionSession;
}

function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return "";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function InspectorTimeline({ session }: InspectorTimelineProps) {
  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Execution timeline">
      <h3 className="pr-inspector-section-title">Execution Graph</h3>
      <div className="pr-inspector-timeline" role="list" aria-label="Step by step timeline">
        <div className="pr-inspector-timeline-node pr-inspector-timeline-start">
          <div className="pr-inspector-timeline-icon">{'{REQUEST}'}</div>
          <div className="pr-inspector-timeline-content">
            <span className="pr-inspector-timeline-label">Request</span>
            <span className="pr-inspector-timeline-desc">{session.title}</span>
          </div>
        </div>

        {session.steps.length > 0 && (
          <div className="pr-inspector-timeline-connector" aria-hidden="true" />
        )}

        {session.steps.map((step, i) => (
          <div key={step.id}>
            <div
              className={`pr-inspector-timeline-node pr-inspector-timeline-step pr-inspector-timeline-${step.status}`}
            >
              <div className={`pr-inspector-timeline-icon pr-inspector-timeline-icon-step pr-inspector-timeline-icon-step-${step.status}`}>
                {step.status === "running" ? "{RUN}" : step.status === "completed" ? "{OK}" : step.status === "failed" ? "{FAIL}" : "{STEP}"}
              </div>
              <div className="pr-inspector-timeline-content">
                <span className="pr-inspector-timeline-label">{step.label}</span>
                {step.durationMs !== undefined && (
                  <span className="pr-inspector-timeline-duration">{formatDuration(step.durationMs)}</span>
                )}
                {step.error && (
                  <div className="pr-inspector-timeline-result">{step.error}</div>
                )}
              </div>
            </div>
            {i < session.steps.length - 1 && <div className="pr-inspector-timeline-connector" aria-hidden="true" />}
          </div>
        ))}

        {(session.status === "completed" || session.status === "failed" || session.status === "cancelled") && (
          <>
            {session.steps.length > 0 && <div className="pr-inspector-timeline-connector" aria-hidden="true" />}
            <div className="pr-inspector-timeline-node pr-inspector-timeline-end">
              <div className="pr-inspector-timeline-icon">{'{RESULT}'}</div>
              <div className="pr-inspector-timeline-content">
                <span className="pr-inspector-timeline-label">
                  {session.status === "completed" ? "Completed" : session.status === "failed" ? "Failed" : "Cancelled"}
                </span>
                {session.durationMs !== undefined && (
                  <span className="pr-inspector-timeline-duration">{formatDuration(session.durationMs)}</span>
                )}
                {session.result && (
                  <div className="pr-inspector-timeline-result">{session.result.summary}</div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default InspectorTimeline;
