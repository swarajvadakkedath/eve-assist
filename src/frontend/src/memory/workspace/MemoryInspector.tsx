import { useMemo } from "react";
import type { HTMLAttributes } from "react";
import type { MemoryNode, MemoryEdge } from "@/memory/core";
import { getMemoryStore } from "@/memory/core";
import { MemoryPreview } from "./MemoryPreview";
import { MemoryActions } from "./MemoryActions";
import type { MemoryActionsProps } from "./MemoryActions";

export interface MemoryInspectorProps extends HTMLAttributes<HTMLDivElement> {
  node: MemoryNode;
  onClose?: () => void;
  actions?: Pick<MemoryActionsProps, "onPin" | "onArchive" | "onDelete" | "onEdit">;
}

function formatTimestamp(ts: number): string {
  return new Date(ts).toLocaleString();
}

function renderEdgeList(edges: readonly MemoryEdge[], label: string) {
  if (edges.length === 0) return null;

  return (
    <div className="mw-inspector-section">
      <div className="mw-inspector-section-title">{label}</div>
      {edges.map((edge) => (
        <div key={edge.id.value} className="mw-inspector-row">
          <span className="mw-inspector-label">{edge.type}</span>
          <span className="mw-inspector-value" style={{ fontSize: "var(--text-xs)" }}>
            {edge.sourceNodeId.type}:{edge.sourceNodeId.value} → {edge.targetNodeId.type}:{edge.targetNodeId.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export function MemoryInspector({
  node,
  onClose,
  actions,
  className = "",
  ...rest
}: MemoryInspectorProps) {
  const store = useMemo(() => getMemoryStore(), []);

  const edges = useMemo(() => store.graph.getConnectedEdges(node.id), [store.graph, node.id]);

  const outgoingNeighbors = useMemo(
    () => store.graph.getOutgoingNeighbors(node.id),
    [store.graph, node.id]
  );

  const incomingNeighbors = useMemo(
    () => store.graph.getIncomingNeighbors(node.id),
    [store.graph, node.id]
  );

  const classes = ["mw-inspector", className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="complementary" aria-label="Node inspector" {...rest}>
      <div className="mw-inspector-header">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>Inspector</span>
          {onClose && (
            <button
              className="pr-btn pr-btn-ghost pr-btn-sm"
              onClick={onClose}
              aria-label="Close inspector"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      <div className="mw-inspector-body">
        <MemoryPreview node={node} />

        <div className="mw-inspector-section">
          <div className="mw-inspector-section-title">Importance</div>
          <div className="mw-progress-bar" role="progressbar" aria-valuenow={Math.round(node.importance * 100)} aria-valuemin={0} aria-valuemax={100} aria-label={`Importance: ${Math.round(node.importance * 100)}%`}>
            <div className="mw-progress-bar-fill importance" style={{ width: `${node.importance * 100}%` }} />
          </div>
          <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-1)" }}>
            {Math.round(node.importance * 100)}%
          </div>
        </div>

        <div className="mw-inspector-section">
          <div className="mw-inspector-section-title">Confidence</div>
          <div className="mw-progress-bar" role="progressbar" aria-valuenow={Math.round(node.confidence * 100)} aria-valuemin={0} aria-valuemax={100} aria-label={`Confidence: ${Math.round(node.confidence * 100)}%`}>
            <div className="mw-progress-bar-fill confidence" style={{ width: `${node.confidence * 100}%` }} />
          </div>
          <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: "var(--space-1)" }}>
            {Math.round(node.confidence * 100)}%
          </div>
        </div>

        <div className="mw-inspector-section">
          <div className="mw-inspector-section-title">Access</div>
          <div className="mw-inspector-row">
            <span className="mw-inspector-label">Access Count</span>
            <span className="mw-inspector-value">{node.accessCount}</span>
          </div>
          <div className="mw-inspector-row">
            <span className="mw-inspector-label">Last Accessed</span>
            <span className="mw-inspector-value">{formatTimestamp(node.lastAccessed)}</span>
          </div>
        </div>

        {outgoingNeighbors.length > 0 && (
          <div className="mw-inspector-section">
            <div className="mw-inspector-section-title">
              Children ({outgoingNeighbors.length})
            </div>
            {outgoingNeighbors.map((n) => (
              <div key={`${n.id.type}:${n.id.value}`} className="mw-inspector-row">
                <span className="mw-inspector-label">{n.subtype || n.type}</span>
                <span className="mw-inspector-value" style={{ fontSize: "var(--text-xs)" }}>
                  {n.title}
                </span>
              </div>
            ))}
          </div>
        )}

        {incomingNeighbors.length > 0 && (
          <div className="mw-inspector-section">
            <div className="mw-inspector-section-title">
              Parents ({incomingNeighbors.length})
            </div>
            {incomingNeighbors.map((n) => (
              <div key={`${n.id.type}:${n.id.value}`} className="mw-inspector-row">
                <span className="mw-inspector-label">{n.subtype || n.type}</span>
                <span className="mw-inspector-value" style={{ fontSize: "var(--text-xs)" }}>
                  {n.title}
                </span>
              </div>
            ))}
          </div>
        )}

        {renderEdgeList(edges.outgoing, `Outgoing Edges (${edges.outgoing.length})`)}
        {renderEdgeList(edges.incoming, `Incoming Edges (${edges.incoming.length})`)}
      </div>

      {actions && <MemoryActions node={node} {...actions} />}
    </div>
  );
}
