import { useState, useEffect, useMemo } from "react";
import type { ActivityFilter as ActivityFilterType } from "./types";
import { getStatusGroup } from "./types";
import { getSessionStore } from "../execution/session";
import ActivityFilter from "./ActivityFilter";
import ActivityFeed from "./ActivityFeed";
import ActivityToolbar from "./ActivityToolbar";
import ActivityEmptyState from "./ActivityEmptyState";

export interface ActivityCenterProps {
  onSelectSession?: (sessionId: string) => void;
  onClear?: () => void;
}

function ActivityCenter({ onSelectSession, onClear }: ActivityCenterProps) {
  const [filter, setFilter] = useState<ActivityFilterType>("all");
  const [sessions, setSessions] = useState(getSessionStore().getAllGlobalSessions());
  const store = getSessionStore();

  useEffect(() => {
    setSessions(store.getAllGlobalSessions());
    return store.subscribe(() => {
      setSessions(store.getAllGlobalSessions());
    });
  }, [store]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: sessions.length };
    for (const s of sessions) {
      const group = getStatusGroup(s.status);
      c[group] = (c[group] || 0) + 1;
      const cap = s.steps[0]?.capability.split(".")[0] || "other";
      c[cap] = (c[cap] || 0) + 1;
    }
    return c;
  }, [sessions]);

  const filtered = useMemo(
    () => filter === "all"
      ? sessions
      : sessions.filter(s => {
          if (filter === "running" || filter === "completed" || filter === "failed") {
            return getStatusGroup(s.status) === filter;
          }
          const prefix = filter === "files" ? "file" : filter === "plugins" ? "plugin" : filter;
          return s.steps.some(step => step.capability.toLowerCase().startsWith(prefix));
        }),
    [sessions, filter],
  );

  return (
    <div className="pr-activity-center" role="region" aria-label="Global activity center">
      <div className="pr-activity-center-header">
        <h2 className="pr-activity-center-title">Activity</h2>
      </div>
      <ActivityToolbar totalCount={sessions.length} onClear={onClear} />
      <ActivityFilter active={filter} onChange={setFilter} counts={counts} />
      <div className="pr-activity-center-body">
        {filtered.length > 0 ? (
          <ActivityFeed sessions={filtered} filter={filter} onSelectSession={onSelectSession} />
        ) : (
          <ActivityEmptyState filter={filter === "all" ? undefined : filter} />
        )}
      </div>
    </div>
  );
}

export default ActivityCenter;
