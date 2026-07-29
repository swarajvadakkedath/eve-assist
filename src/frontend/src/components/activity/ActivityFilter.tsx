import type { ActivityFilter as ActivityFilterType } from "./types";
import { ACTIVITY_FILTERS } from "./types";

export interface ActivityFilterProps {
  active: ActivityFilterType;
  onChange: (filter: ActivityFilterType) => void;
  counts: Record<string, number>;
}

function ActivityFilter({ active, onChange, counts }: ActivityFilterProps) {
  return (
    <div className="pr-activity-filter" role="group" aria-label="Activity filters">
      {ACTIVITY_FILTERS.map(filter => {
        const count = counts[filter.id] ?? 0;
        return (
          <button
            key={filter.id}
            className={`pr-activity-filter-btn ${active === filter.id ? "pr-activity-filter-active" : ""}`}
            onClick={() => onChange(filter.id)}
            aria-pressed={active === filter.id}
          >
            {filter.label}
            {count > 0 && <span className="pr-activity-filter-count">{count}</span>}
          </button>
        );
      })}
    </div>
  );
}

export default ActivityFilter;
