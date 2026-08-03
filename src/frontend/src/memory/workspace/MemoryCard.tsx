import { useId } from "react";
import type { HTMLAttributes } from "react";
import type { MemoryNode } from "@/memory/core";

export interface MemoryCardProps extends HTMLAttributes<HTMLDivElement> {
  node: MemoryNode;
  selected?: boolean;
  showTags?: boolean;
  showMeta?: boolean;
  compact?: boolean;
}

function formatTimestamp(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return new Date(ts).toLocaleDateString();
}

export function MemoryCard({
  node,
  selected = false,
  showTags = true,
  showMeta = true,
  compact = false,
  className = "",
  onClick,
  onKeyDown,
  ...rest
}: MemoryCardProps) {
  const titleId = useId();

  const classes = [
    "mw-card",
    selected ? "selected" : "",
    className,
  ].filter(Boolean).join(" ");

  return (
    <div
      className={classes}
      role="button"
      tabIndex={0}
      aria-selected={selected}
      aria-labelledby={titleId}
      onClick={onClick}
      onKeyDown={onKeyDown}
      {...rest}
    >
      <div className="mw-card-header">
        <span className="mw-badge mw-badge-entity">
          {node.subtype || node.type}
        </span>
        {node.pinned && <span aria-label="Pinned">📌</span>}
      </div>

      <div className="mw-card-title" id={titleId}>
        {node.title}
      </div>

      {!compact && node.summary && (
        <div className="mw-card-summary">{node.summary}</div>
      )}

      <div className="mw-card-footer">
        {showTags && node.tags.length > 0 && (
          <div className="mw-card-tags" role="list" aria-label="Tags">
            {node.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="mw-badge mw-badge-meta" role="listitem">
                {tag}
              </span>
            ))}
            {node.tags.length > 3 && (
              <span className="mw-badge mw-badge-meta" role="listitem">
                +{node.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {showMeta && (
          <div className="mw-card-meta">
            <span>{formatTimestamp(node.updatedAt)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
