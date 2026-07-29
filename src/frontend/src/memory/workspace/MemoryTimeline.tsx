import { useMemo } from "react";
import type { HTMLAttributes } from "react";
import type { MemoryNode } from "@/memory/core";

export interface TimelineGroup {
  label: string;
  nodes: MemoryNode[];
}

export interface MemoryTimelineProps extends HTMLAttributes<HTMLDivElement> {
  nodes: readonly MemoryNode[];
  onSelect?: (node: MemoryNode) => void;
  emptyMessage?: string;
}

function getDateLabel(timestamp: number): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / 86400000);

  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return "This Week";
  if (days < 14) return "Last Week";
  if (days < 30) return "This Month";
  if (days < 60) return "Last Month";
  return date.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function groupByTime(nodes: readonly MemoryNode[]): TimelineGroup[] {
  const groups = new Map<string, MemoryNode[]>();

  for (const node of nodes) {
    const label = getDateLabel(node.updatedAt);
    const existing = groups.get(label) || [];
    existing.push(node);
    groups.set(label, existing);
  }

  const order = ["Today", "Yesterday", "This Week", "Last Week", "This Month", "Last Month"];

  return [...groups.entries()]
    .sort(([a], [b]) => {
      const ai = order.indexOf(a);
      const bi = order.indexOf(b);
      if (ai !== -1 && bi !== -1) return ai - bi;
      if (ai !== -1) return -1;
      if (bi !== -1) return 1;
      return 0;
    })
    .map(([label, groupNodes]) => ({
      label,
      nodes: groupNodes.sort((a, b) => b.updatedAt - a.updatedAt),
    }));
}

export function MemoryTimeline({
  nodes,
  onSelect,
  emptyMessage = "No timeline items",
  className = "",
  ...rest
}: MemoryTimelineProps) {
  const groups = useMemo(() => groupByTime(nodes), [nodes]);

  if (nodes.length === 0) {
    return (
      <div className="mw-empty-state" role="status">
        <div className="mw-empty-state-icon" aria-hidden="true">📅</div>
        <div className="mw-empty-state-text">{emptyMessage}</div>
      </div>
    );
  }

  const classes = ["mw-timeline", className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="list" aria-label="Timeline" {...rest}>
      {groups.map((group) => (
        <div key={group.label} className="mw-timeline-group">
          <div className="mw-timeline-group-header" role="heading" aria-level={3}>
            {group.label}
            <span style={{ fontWeight: "var(--weight-normal)", marginLeft: "var(--space-1)" }}>
              ({group.nodes.length})
            </span>
          </div>
          <div className="mw-timeline-items">
            {group.nodes.map((node) => (
              <div
                key={`${node.id.type}:${node.id.value}`}
                className="mw-list-item"
                role="listitem"
                tabIndex={0}
                onClick={() => onSelect?.(node)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect?.(node);
                  }
                }}
              >
                <span className="mw-badge mw-badge-entity">
                  {node.subtype || node.type}
                </span>
                <span className="mw-list-item-title">{node.title}</span>
                <span className="mw-list-item-meta">
                  {new Date(node.updatedAt).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
