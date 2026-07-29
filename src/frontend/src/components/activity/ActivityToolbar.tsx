export interface ActivityToolbarProps {
  totalCount: number;
  onClear?: () => void;
}

function ActivityToolbar({ totalCount, onClear }: ActivityToolbarProps) {
  return (
    <div className="pr-activity-toolbar">
      <span className="pr-activity-toolbar-count">{totalCount} session{totalCount !== 1 ? "s" : ""}</span>
      {onClear && totalCount > 0 && (
        <button className="pr-activity-toolbar-clear" onClick={onClear} aria-label="Clear all activity">
          Clear All
        </button>
      )}
    </div>
  );
}

export default ActivityToolbar;
