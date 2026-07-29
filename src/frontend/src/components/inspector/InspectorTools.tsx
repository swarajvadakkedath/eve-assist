import type { ExecutionSession } from "../execution/session/types";

export interface InspectorToolsProps {
  session: ExecutionSession;
}

function InspectorTools({ session }: InspectorToolsProps) {
  if (session.steps.length === 0) {
    return (
      <div className="pr-inspector-section" role="tabpanel" aria-label="Tools">
        <p className="pr-inspector-empty">No tools were executed in this session.</p>
      </div>
    );
  }

  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Tools">
      <h3 className="pr-inspector-section-title">Tools Executed ({session.metadata.toolCount})</h3>
      <div className="pr-inspector-tools-list" role="list" aria-label="Tools used">
        {session.steps.map(step => (
          <div key={step.id} className="pr-inspector-tool-card" role="listitem">
            <div className="pr-inspector-tool-header">
              <span className={`pr-inspector-tool-status pr-inspector-status-${step.status}`} aria-hidden="true" />
              <span className="pr-inspector-tool-name">{step.label}</span>
              <span className="pr-inspector-tool-capability">{step.capability}</span>
            </div>
            <div className="pr-inspector-tool-details">
              <span className="pr-inspector-tool-detail">
                Status: <strong>{step.status}</strong>
              </span>
              {step.durationMs !== undefined && (
                <span className="pr-inspector-tool-detail">
                  Duration: <strong>{step.durationMs}ms</strong>
                </span>
              )}
              {step.error && (
                <span className="pr-inspector-tool-detail pr-inspector-failed">
                  Error: {step.error}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default InspectorTools;
