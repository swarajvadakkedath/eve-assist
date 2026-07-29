import { useId } from "react";
import type { HTMLAttributes } from "react";
import type { NodeSuperType, NodeStatus } from "@/memory/core";

export interface MemoryFiltersState {
  superTypes: NodeSuperType[];
  statuses: NodeStatus[];
  tags: string[];
  pinned: boolean | undefined;
  dateFrom: number | undefined;
  dateTo: number | undefined;
}

export interface MemoryFiltersProps extends HTMLAttributes<HTMLDivElement> {
  filters: MemoryFiltersState;
  onChange: (filters: MemoryFiltersState) => void;
  availableTags: readonly string[];
}

const superTypeOptions: { value: NodeSuperType; label: string }[] = [
  { value: "action", label: "Action" },
  { value: "observation", label: "Observation" },
  { value: "knowledge", label: "Knowledge" },
  { value: "artifact", label: "Artifact" },
  { value: "entity", label: "Entity" },
  { value: "meta", label: "Meta" },
];

const statusOptions: { value: NodeStatus; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
  { value: "deleted", label: "Deleted" },
];

export function MemoryFilters({
  filters,
  onChange,
  availableTags,
  className = "",
  ...rest
}: MemoryFiltersProps) {
  const superTypeId = useId();
  const statusId = useId();
  const tagId = useId();
  const pinnedId = useId();

  const classes = ["mw-filters-panel", className].filter(Boolean).join(" ");

  const toggleSuperType = (value: NodeSuperType) => {
    const next = filters.superTypes.includes(value)
      ? filters.superTypes.filter((t) => t !== value)
      : [...filters.superTypes, value];
    onChange({ ...filters, superTypes: next });
  };

  const toggleStatus = (value: NodeStatus) => {
    const next = filters.statuses.includes(value)
      ? filters.statuses.filter((s) => s !== value)
      : [...filters.statuses, value];
    onChange({ ...filters, statuses: next });
  };

  const toggleTag = (value: string) => {
    const next = filters.tags.includes(value)
      ? filters.tags.filter((t) => t !== value)
      : [...filters.tags, value];
    onChange({ ...filters, tags: next });
  };

  return (
    <div className={classes} role="region" aria-label="Filters" {...rest}>
      <div className="mw-filters-row">
        <fieldset className="mw-filter-group">
          <legend className="mw-filter-label">Type</legend>
          <div style={{ display: "flex", gap: "var(--space-1)", flexWrap: "wrap" }}>
            {superTypeOptions.map((opt) => (
              <button
                key={opt.value}
                className={`pr-btn pr-btn-ghost pr-btn-sm${filters.superTypes.includes(opt.value) ? " active" : ""}`}
                onClick={() => toggleSuperType(opt.value)}
                aria-pressed={filters.superTypes.includes(opt.value)}
                aria-label={`Filter by ${opt.label}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="mw-filter-group">
          <legend className="mw-filter-label">Status</legend>
          <div style={{ display: "flex", gap: "var(--space-1)" }}>
            {statusOptions.map((opt) => (
              <button
                key={opt.value}
                className={`pr-btn pr-btn-ghost pr-btn-sm${filters.statuses.includes(opt.value) ? " active" : ""}`}
                onClick={() => toggleStatus(opt.value)}
                aria-pressed={filters.statuses.includes(opt.value)}
                aria-label={`Filter by ${opt.label}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </fieldset>

        {availableTags.length > 0 && (
          <fieldset className="mw-filter-group">
            <legend className="mw-filter-label">Tags</legend>
            <div style={{ display: "flex", gap: "var(--space-1)", flexWrap: "wrap" }}>
              {availableTags.map((tag) => (
                <button
                  key={tag}
                  className={`pr-btn pr-btn-ghost pr-btn-sm${filters.tags.includes(tag) ? " active" : ""}`}
                  onClick={() => toggleTag(tag)}
                  aria-pressed={filters.tags.includes(tag)}
                  aria-label={`Filter by tag ${tag}`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <div className="mw-filter-group">
          <button
            className={`pr-btn pr-btn-ghost pr-btn-sm${filters.pinned === true ? " active" : ""}`}
            onClick={() => onChange({ ...filters, pinned: filters.pinned === true ? undefined : true })}
            aria-pressed={filters.pinned === true}
            aria-label="Filter pinned items only"
          >
            📌 Pinned
          </button>
        </div>
      </div>
    </div>
  );
}
