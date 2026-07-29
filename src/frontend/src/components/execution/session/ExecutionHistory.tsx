import { useState, useEffect } from "react";
import type { ExecutionSession } from "./types";
import { getSessionStore } from "./ExecutionSessionStore";
import ExecutionSessionCard from "./ExecutionSessionCard";

export interface ExecutionHistoryProps {
  conversationId: string;
  filter?: string;
}

function ExecutionHistory({ conversationId }: ExecutionHistoryProps) {
  const store = getSessionStore();
  const [, setTick] = useState(0);

  useEffect(() => {
    return store.subscribe(() => setTick(t => t + 1));
  }, [store]);

  const sessions = store.getAllSessions(conversationId);

  if (sessions.length === 0) return null;

  return (
    <div className="pr-session-history" role="feed" aria-label="Execution history">
      {sessions.map(session => (
        <div key={session.id} className="pr-session-history-item">
          <ExecutionSessionCard session={session} />
        </div>
      ))}
    </div>
  );
}

export default ExecutionHistory;
