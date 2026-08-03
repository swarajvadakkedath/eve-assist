import { useAioStore } from "./AioStore";

function formatRelativeTime(ts: number): string {
  if (ts === 0) return "never";
  const diff = Date.now() - ts;
  if (diff < 60_000) return `${Math.round(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
  return `${Math.round(diff / 86_400_000)}d ago`;
}

function ActivityView() {
  const { activity } = useAioStore();

  if (activity.length === 0) {
    return (
      <div className="aio-empty">
        <div className="aio-empty-icon">📋</div>
        <div>No activity yet</div>
      </div>
    );
  }

  return (
    <div>
      <div className="aio-section-title">Activity Timeline</div>
      <div className="aio-section-sub">{activity.length} events</div>
      <div className="aio-activity-list">
        {activity.map((event) => (
          <div key={event.id} className="aio-activity-item">
            <div className={`aio-activity-dot ${event.severity}`} />
            <div className="aio-activity-msg">{event.message}</div>
            <div className="aio-activity-time">{formatRelativeTime(event.timestamp)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ActivityView;
