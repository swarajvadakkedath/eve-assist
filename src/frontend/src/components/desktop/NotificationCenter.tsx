import { useState, useEffect, useRef } from "react";
import { fetchApi } from "../../services/api";

interface Notification {
  title: string;
  message: string;
  type: string;
  timestamp: string;
}

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchApi("/desktop/notifications/history")
      .then((r) => r.json())
      .then((data) => {
        setNotifications(data.notifications || []);
        setUnread(data.notifications?.length || 0);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const clearHistory = async () => {
    await fetchApi("/desktop/notifications/history", { method: "DELETE" });
    setUnread(0);
  };

  return (
    <div className="notification-center">
      <button className="notification-bell" onClick={() => setOpen(!open)}>
        🔔
        {unread > 0 && <span className="notification-badge">{unread}</span>}
      </button>
      {open && (
        <div className="notification-panel" ref={panelRef}>
          <div className="notification-panel-header">
            <h3>Notifications</h3>
            <button className="btn-text" onClick={clearHistory}>Clear</button>
          </div>
          <div className="notification-list">
            {notifications.length === 0 ? (
              <div className="notification-empty">No notifications</div>
            ) : (
              notifications.map((n, i) => (
                <div key={i} className={`notification-item notification-${n.type}`}>
                  <div className="notification-title">{n.title}</div>
                  <div className="notification-message">{n.message}</div>
                  <div className="notification-time">
                    {new Date(n.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
