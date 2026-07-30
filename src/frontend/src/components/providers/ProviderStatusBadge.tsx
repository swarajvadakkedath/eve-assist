const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  connected: { label: "Connected", color: "#22c55e", bg: "rgba(34,197,94,0.12)" },
  healthy: { label: "Healthy", color: "#22c55e", bg: "rgba(34,197,94,0.12)" },
  not_configured: { label: "Not Configured", color: "#6b7280", bg: "rgba(107,114,128,0.12)" },
  offline: { label: "Offline", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  degraded: { label: "Degraded", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  invalid_key: { label: "Invalid API Key", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
  rate_limited: { label: "Rate Limited", color: "#f97316", bg: "rgba(249,115,22,0.12)" },
  quota_exhausted: { label: "Quota Exhausted", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
  expired: { label: "Expired Key", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
  error: { label: "Error", color: "#ef4444", bg: "rgba(239,68,68,0.12)" },
};

interface ProviderStatusBadgeProps {
  status: string;
  latencyMs?: number | null;
}

export default function ProviderStatusBadge({ status, latencyMs }: ProviderStatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.not_configured;

  return (
    <div className="pr-status-badge" style={{ background: config.bg, color: config.color }}>
      <span className="pr-status-dot" style={{ background: config.color }} />
      <span className="pr-status-label">{config.label}</span>
      {latencyMs != null && (
        <span className="pr-status-latency" style={{ color: config.color, opacity: 0.7 }}>
          {latencyMs}ms
        </span>
      )}
    </div>
  );
}
