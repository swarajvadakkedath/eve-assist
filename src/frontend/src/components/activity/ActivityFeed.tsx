import { useMemo } from "react";
import type { ExecutionSession } from "../execution/session/types";
import type { ActivityFilter as ActivityFilterType } from "./types";
import { getStatusGroup } from "./types";
import ActivityItem from "./ActivityItem";

export interface ActivityFeedProps {
  sessions: ExecutionSession[];
  filter: ActivityFilterType;
  onSelectSession?: (sessionId: string) => void;
}

function matchesFilter(session: ExecutionSession, filter: ActivityFilterType): boolean {
  if (filter === "all") return true;
  if (filter === "running" || filter === "completed" || filter === "failed") {
    return getStatusGroup(session.status) === filter;
  }
  const cap = filter === "files" ? "file" : filter === "plugins" ? "plugin" : filter;
  return session.steps.some(s => s.capability.toLowerCase().startsWith(cap));
}

function ActivityFeed({ sessions, filter, onSelectSession }: ActivityFeedProps) {
  const filtered = useMemo(
    () => sessions.filter(s => matchesFilter(s, filter)),
    [sessions, filter],
  );

  return (
    <div className="pr-activity-feed" role="list" aria-label="Activity feed">
      {filtered.map(session => (
        <ActivityItem
          key={session.id}
          session={session}
          onSelect={onSelectSession}
        />
      ))}
    </div>
  );
}

export default ActivityFeed;
