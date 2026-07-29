import type { HTMLAttributes } from "react";
import type { MemoryNode } from "@/memory/core";

export interface MemoryActionsProps extends HTMLAttributes<HTMLDivElement> {
  node: MemoryNode;
  onPin?: (node: MemoryNode) => void;
  onArchive?: (node: MemoryNode) => void;
  onDelete?: (node: MemoryNode) => void;
  onEdit?: (node: MemoryNode) => void;
}

export function MemoryActions({
  node,
  onPin,
  onArchive,
  onDelete,
  onEdit,
  className = "",
  ...rest
}: MemoryActionsProps) {
  const classes = ["mw-actions", className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="toolbar" aria-label="Node actions" {...rest}>
      {onPin && (
        <button
          className="pr-btn pr-btn-ghost pr-btn-sm"
          onClick={() => onPin(node)}
          aria-label={node.pinned ? "Unpin node" : "Pin node"}
          title={node.pinned ? "Unpin" : "Pin"}
        >
          {node.pinned ? "📌" : "📍"}
        </button>
      )}
      {onEdit && (
        <button
          className="pr-btn pr-btn-ghost pr-btn-sm"
          onClick={() => onEdit(node)}
          aria-label="Edit node"
          title="Edit"
        >
          ✏️
        </button>
      )}
      {onArchive && (
        <button
          className="pr-btn pr-btn-ghost pr-btn-sm"
          onClick={() => onArchive(node)}
          aria-label={node.archived ? "Restore node" : "Archive node"}
          title={node.archived ? "Restore" : "Archive"}
        >
          {node.archived ? "📂" : "📦"}
        </button>
      )}
      {onDelete && (
        <button
          className="pr-btn pr-btn-ghost pr-btn-sm"
          onClick={() => onDelete(node)}
          aria-label="Delete node"
          title="Delete"
          style={{ color: "var(--color-error)" }}
        >
          🗑
        </button>
      )}
    </div>
  );
}
