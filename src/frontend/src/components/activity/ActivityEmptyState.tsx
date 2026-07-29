export interface ActivityEmptyStateProps {
  filter?: string;
}

function ActivityEmptyState({ filter }: ActivityEmptyStateProps) {
  return (
    <div className="pr-activity-empty" role="status">
      <div className="pr-activity-empty-icon" aria-hidden="true">{'\uD83D\uDCCB'}</div>
      <p className="pr-activity-empty-title">
        {filter && filter !== "all" ? `No ${filter} activity` : "No activity yet"}
      </p>
      <p className="pr-activity-empty-desc">
        {filter && filter !== "all"
          ? `No execution sessions match the "${filter}" filter.`
          : "Execution sessions will appear here when Eve performs tasks."}
      </p>
    </div>
  );
}

export default ActivityEmptyState;
