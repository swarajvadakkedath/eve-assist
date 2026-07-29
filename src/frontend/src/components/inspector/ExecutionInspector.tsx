import { useState, useEffect, useCallback } from "react";
import type { InspectorTab } from "./types";
import type { ExecutionSession } from "../execution/session/types";
import { getSessionStore } from "../execution/session";
import InspectorTabs from "./InspectorTabs";
import InspectorSummary from "./InspectorSummary";
import InspectorTimeline from "./InspectorTimeline";
import InspectorLogs from "./InspectorLogs";
import InspectorTools from "./InspectorTools";
import InspectorFiles from "./InspectorFiles";
import InspectorPermissions from "./InspectorPermissions";
import InspectorPerformance from "./InspectorPerformance";
import InspectorMetadata from "./InspectorMetadata";
import InspectorJsonView from "./InspectorJsonView";
import InspectorActions from "./InspectorActions";

export interface ExecutionInspectorProps {
  sessionId: string;
  onClose: () => void;
}

function ExecutionInspector({ sessionId, onClose }: ExecutionInspectorProps) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("summary");
  const [session, setSession] = useState<ExecutionSession | null>(null);
  const store = getSessionStore();

  useEffect(() => {
    setSession(store.getSession(sessionId) || null);
    return store.subscribe(() => {
      setSession(store.getSession(sessionId) || null);
    });
  }, [sessionId, store]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    }
  }, [onClose]);

  if (!session) {
    return (
      <div className="pr-inspector" role="dialog" aria-label="Execution inspector" aria-modal="true">
        <div className="pr-inspector-header">
          <h2 className="pr-inspector-title">Inspector</h2>
          <button className="pr-inspector-close" onClick={onClose} aria-label="Close inspector">&times;</button>
        </div>
        <div className="pr-inspector-body">
          <p className="pr-inspector-empty">Session not found.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="pr-inspector"
      role="dialog"
      aria-label={`Inspector: ${session.title}`}
      aria-modal="true"
      onKeyDown={handleKeyDown}
    >
      <div className="pr-inspector-header">
        <h2 className="pr-inspector-title">Inspector</h2>
        <span className="pr-inspector-session-title">{session.title}</span>
        <button className="pr-inspector-close" onClick={onClose} aria-label="Close inspector">&times;</button>
      </div>

      <InspectorTabs active={activeTab} onChange={setActiveTab} />

      <div className="pr-inspector-body">
        {activeTab === "summary" && <InspectorSummary session={session} />}
        {activeTab === "timeline" && <InspectorTimeline session={session} />}
        {activeTab === "logs" && <InspectorLogs session={session} />}
        {activeTab === "tools" && <InspectorTools session={session} />}
        {activeTab === "files" && <InspectorFiles session={session} />}
        {activeTab === "permissions" && <InspectorPermissions session={session} />}
        {activeTab === "performance" && <InspectorPerformance session={session} />}
        {activeTab === "metadata" && <InspectorMetadata session={session} />}
        {activeTab === "raw" && <InspectorJsonView session={session} />}
      </div>

      <InspectorActions session={session} onClose={onClose} />
    </div>
  );
}

export default ExecutionInspector;
