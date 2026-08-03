import { useBackendStatus } from "../../services/statusStore";

type AppStatus =
  | "starting" | "initializing" | "ready" | "listening" | "thinking"
  | "planning" | "executing" | "waiting" | "updating"
  | "offline" | "degraded" | "error";

const STATUS_CONFIG: Record<AppStatus, { label: string; color: string; icon: string }> = {
  starting: { label: "Starting...", color: "#9ca3af", icon: "◌" },
  initializing: { label: "Initializing...", color: "#9ca3af", icon: "◌" },
  ready: { label: "Ready", color: "#6366f1", icon: "●" },
  listening: { label: "Listening", color: "#6366f1", icon: "🎤" },
  thinking: { label: "Thinking...", color: "#fbbf24", icon: "◌" },
  planning: { label: "Planning...", color: "#fbbf24", icon: "📋" },
  executing: { label: "Executing...", color: "#34d399", icon: "⚡" },
  waiting: { label: "Waiting...", color: "#9ca3af", icon: "⏳" },
  updating: { label: "Updating...", color: "#6366f1", icon: "⬆" },
  offline: { label: "Offline", color: "#9ca3af", icon: "○" },
  degraded: { label: "Degraded", color: "#f59e0b", icon: "●" },
  error: { label: "Error", color: "#ef4444", icon: "✕" },
};

export default function StatusIndicator() {
  const { status } = useBackendStatus();
  const config = STATUS_CONFIG[status as AppStatus] || STATUS_CONFIG.ready;

  return (
    <div className="status-indicator" title={config.label}>
      <span className="status-dot" style={{ backgroundColor: config.color }} />
      <span className="status-label">{config.label}</span>
    </div>
  );
}
