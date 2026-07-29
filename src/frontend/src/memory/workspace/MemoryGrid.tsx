import type { HTMLAttributes } from "react";
import type { MemoryNode } from "@/memory/core";
import { MemoryCard } from "./MemoryCard";

export interface MemoryGridProps extends HTMLAttributes<HTMLDivElement> {
  nodes: readonly MemoryNode[];
  selectedId?: string;
  onSelect?: (node: MemoryNode) => void;
  emptyMessage?: string;
}

export function MemoryGrid({
  nodes,
  selectedId,
  onSelect,
  emptyMessage = "No items to display",
  className = "",
  ...rest
}: MemoryGridProps) {
  if (nodes.length === 0) {
    return (
      <div className="mw-empty-state" role="status">
        <div className="mw-empty-state-icon" aria-hidden="true">📭</div>
        <div className="mw-empty-state-text">{emptyMessage}</div>
      </div>
    );
  }

  const classes = ["mw-grid", className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="list" aria-label="Memory items grid" {...rest}>
      {nodes.map((node) => (
        <MemoryCard
          key={`${node.id.type}:${node.id.value}`}
          node={node}
          selected={selectedId === `${node.id.type}:${node.id.value}`}
          onClick={() => onSelect?.(node)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onSelect?.(node);
            }
          }}
        />
      ))}
    </div>
  );
}
