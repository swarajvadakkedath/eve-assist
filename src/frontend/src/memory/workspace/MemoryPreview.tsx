import type { HTMLAttributes } from "react";
import type { MemoryNode } from "@/memory/core";

export interface MemoryPreviewProps extends HTMLAttributes<HTMLDivElement> {
  node: MemoryNode;
}

function formatTimestamp(ts: number): string {
  return new Date(ts).toLocaleString();
}

export function MemoryPreview({
  node,
  className = "",
  ...rest
}: MemoryPreviewProps) {
  const classes = ["mw-preview", className].filter(Boolean).join(" ");

  return (
    <div className={classes} {...rest}>
      <div className="mw-preview-title">{node.title}</div>

      <div className="mw-preview-meta">
        <span className="mw-inspector-label">Type</span>
        <span className="mw-inspector-value">{node.subtype || node.type}</span>

        <span className="mw-inspector-label">Source</span>
        <span className="mw-inspector-value">{node.source}</span>

        <span className="mw-inspector-label">Created</span>
        <span className="mw-inspector-value">{formatTimestamp(node.createdAt)}</span>

        <span className="mw-inspector-label">Updated</span>
        <span className="mw-inspector-value">{formatTimestamp(node.updatedAt)}</span>

        <span className="mw-inspector-label">Status</span>
        <span className="mw-inspector-value">{node.status}</span>

        <span className="mw-inspector-label">Pinned</span>
        <span className="mw-inspector-value">{node.pinned ? "Yes" : "No"}</span>

        <span className="mw-inspector-label">Archived</span>
        <span className="mw-inspector-value">{node.archived ? "Yes" : "No"}</span>

        <span className="mw-inspector-label">Verified</span>
        <span className="mw-inspector-value">{node.verified ? `Yes (${node.verificationMethod})` : "No"}</span>
      </div>

      {node.summary && (
        <div className="mw-preview-content">
          <strong style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)" }}>
            Summary
          </strong>
          <p style={{ marginTop: "var(--space-1)" }}>{node.summary}</p>
        </div>
      )}

      {node.tags.length > 0 && (
        <div style={{ marginTop: "var(--space-3)" }}>
          <strong style={{ fontSize: "var(--text-xs)", color: "var(--color-text-secondary)" }}>
            Tags
          </strong>
          <div style={{ display: "flex", gap: "var(--space-1)", marginTop: "var(--space-1)", flexWrap: "wrap" }}>
            {node.tags.map((tag) => (
              <span key={tag} className="mw-badge mw-badge-meta">{tag}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
