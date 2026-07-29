import type { HTMLAttributes } from "react";
import type { SortField, SortOrder, MemoryNode } from "@/memory/core";

export type ViewMode = "grid" | "list";

export interface MemoryToolbarProps extends HTMLAttributes<HTMLDivElement> {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  sortField: SortField;
  sortOrder: SortOrder;
  onSortChange: (field: SortField, order: SortOrder) => void;
  onNewNode?: () => void;
  totalCount: number;
  showFilters?: boolean;
  onToggleFilters?: () => void;
}

const sortOptions: { field: SortField; label: string }[] = [
  { field: "updatedAt", label: "Updated" },
  { field: "createdAt", label: "Created" },
  { field: "importance", label: "Importance" },
  { field: "confidence", label: "Confidence" },
  { field: "accessCount", label: "Access Count" },
  { field: "title", label: "Title" },
];

export function MemoryToolbar({
  viewMode,
  onViewModeChange,
  sortField,
  sortOrder,
  onSortChange,
  onNewNode,
  totalCount,
  showFilters = false,
  onToggleFilters,
  className = "",
  ...rest
}: MemoryToolbarProps) {
  const classes = ["mw-toolbar", className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="toolbar" aria-label="Memory toolbar" {...rest}>
      <div className="mw-toolbar-group">
        <button
          className={`pr-btn pr-btn-ghost pr-btn-sm${viewMode === "grid" ? " active" : ""}`}
          onClick={() => onViewModeChange("grid")}
          aria-pressed={viewMode === "grid"}
          aria-label="Grid view"
          title="Grid view"
        >
          ▦
        </button>
        <button
          className={`pr-btn pr-btn-ghost pr-btn-sm${viewMode === "list" ? " active" : ""}`}
          onClick={() => onViewModeChange("list")}
          aria-pressed={viewMode === "list"}
          aria-label="List view"
          title="List view"
        >
          ☰
        </button>
      </div>

      <div className="mw-toolbar-group">
        <label htmlFor="mw-sort-field" className="sr-only">Sort by</label>
        <select
          id="mw-sort-field"
          className="pr-input"
          value={sortField}
          onChange={(e) => onSortChange(e.target.value as SortField, sortOrder)}
          style={{ width: "auto", fontSize: "var(--text-xs)", padding: "2px 6px" }}
        >
          {sortOptions.map((opt) => (
            <option key={opt.field} value={opt.field}>{opt.label}</option>
          ))}
        </select>
        <button
          className="pr-btn pr-btn-ghost pr-btn-sm"
          onClick={() => onSortChange(sortField, sortOrder === "desc" ? "asc" : "desc")}
          aria-label={`Sort ${sortOrder === "desc" ? "ascending" : "descending"}`}
          title={`Sort ${sortOrder === "desc" ? "ascending" : "descending"}`}
        >
          {sortOrder === "desc" ? "↓" : "↑"}
        </button>
      </div>

      <div className="mw-toolbar-spacer" />

      {onToggleFilters && (
        <button
          className={`pr-btn pr-btn-ghost pr-btn-sm${showFilters ? " active" : ""}`}
          onClick={onToggleFilters}
          aria-pressed={showFilters}
          aria-label="Toggle filters"
          title="Toggle filters"
        >
          ⚙
        </button>
      )}

      <div className="mw-toolbar-group" role="status" aria-live="polite">
        <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
          {totalCount} item{totalCount !== 1 ? "s" : ""}
        </span>
      </div>

      {onNewNode && (
        <button
          className="pr-btn pr-btn-primary pr-btn-sm"
          onClick={onNewNode}
          aria-label="Create new node"
        >
          + New
        </button>
      )}
    </div>
  );
}
