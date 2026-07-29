import { useState, useCallback } from "react";
import type { ExecutionSession } from "../execution/session/types";

export interface InspectorJsonViewProps {
  session: ExecutionSession;
}

function InspectorJsonView({ session }: InspectorJsonViewProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(session, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard unavailable */ }
  }, [session]);

  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Raw event data">
      <div className="pr-inspector-json-toolbar">
        <h3 className="pr-inspector-section-title">Raw Event Data</h3>
        <div className="pr-inspector-json-actions">
          <button
            className="pr-inspector-json-toggle"
            onClick={() => setCollapsed(c => !c)}
            aria-expanded={!collapsed}
          >
            {collapsed ? "Expand" : "Collapse"}
          </button>
          <button className="pr-inspector-json-copy" onClick={handleCopy} aria-label="Copy raw JSON">
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      <pre className="pr-inspector-json-pre" role="code" aria-label="Session JSON">
        <code>
          {collapsed
            ? JSON.stringify({ id: session.id, status: session.status, steps: session.steps.length }, null, 2)
            : JSON.stringify(session, null, 2)
          }
        </code>
      </pre>
    </div>
  );
}

export default InspectorJsonView;
