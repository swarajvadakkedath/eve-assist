import type { HTMLAttributes } from "react";
import type { MemoryNode } from "@/memory/core";

export interface MemoryListProps extends Omit<HTMLAttributes<HTMLDivElement>, "onSelect"> {
  nodes: readonly MemoryNode[];
  selectedId?: string;
  onSelect?: (node: MemoryNode) => void;
  emptyMessage?: string;
}

function formatTimestamp(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return new Date(ts).toLocaleDateString();
}

export function MemoryList({
  nodes,
  selectedId,
  onSelect,
  emptyMessage = "No items to display",
  className = "",
  ...rest
}: MemoryListProps) {
  if (nodes.length === 0) {
    return (
      <div className="mw-empty-state" role="status">
        <div className="mw-empty-state-icon" aria-hidden="true">📭</div>
        <div className="mw-empty-state-text">{emptyMessage}</div>
      </div>
    );
  }

  const classes = ["mw-list", className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="list" aria-label="Memory items list" {...rest}>
      {nodes.map((node) => {
        const nodeKey = `${node.id.type}:${node.id.value}`;
        const isSelected = selectedId === nodeKey;

        return (
          <div
            key={nodeKey}
            className={`mw-list-item${isSelected ? " selected" : ""}`}
            role="listitem"
            tabIndex={0}
            aria-selected={isSelected}
            onClick={() => onSelect?.(node)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect?.(node);
              }
            }}
          >
            <span className="mw-badge mw-badge-entity mw-list-item-type">
              {node.subtype || node.type}
            </span>
            <span className="mw-list-item-title">{node.title}</span>
            <span className="mw-list-item-meta">
              {formatTimestamp(node.updatedAt)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
