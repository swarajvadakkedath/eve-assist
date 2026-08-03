import { useMemo } from "react";
import { useAioStore } from "./AioStore";
import StatCard from "./StatCard";
import { PROVIDER_ICONS, STATE_COLORS } from "./aioTypes";

function PerformanceView() {
  const { providers, health, freeModels } = useAioStore();

  const metrics = useMemo(() => {
    const healthEntries = Object.values(health);

    const totalRequests = healthEntries.reduce((s, h) => s + h.total_checks, 0);
    const avgLatency =
      healthEntries.length > 0
        ? Math.round(
            healthEntries.reduce((s, h) => s + h.latency_ms, 0) / healthEntries.length
          )
        : 0;
    const avgHealthScore =
      healthEntries.length > 0
        ? Math.round(
            (healthEntries.reduce((s, h) => s + h.health_score, 0) / healthEntries.length) *
              100
          ) / 100
        : 0;
    const providerCount = providers.length;
    const healthyCount = healthEntries.filter((h) => h.state === "healthy").length;
    const totalModels = providers.reduce((sum, p) => sum + p.models.length, 0);
    const freeModelCount = freeModels.length;
    const offlineCount = healthEntries.filter((h) =>
      ["unreachable", "invalid_key", "quota_exceeded"].includes(h.state)
    ).length;

    return {
      totalRequests,
      avgLatency,
      avgHealthScore,
      providerCount,
      healthyCount,
      totalModels,
      freeModelCount,
      offlineCount,
    };
  }, [providers, health, freeModels]);

  return (
    <div>
      <div className="aio-section-title">Session Metrics</div>
      <div className="aio-stats-grid">
        <StatCard
          label="Total Health Checks"
          value={metrics.totalRequests}
          sub="across all providers"
        />
        <StatCard
          label="Avg Latency"
          value={`${metrics.avgLatency}ms`}
          sub="provider response time"
          color={metrics.avgLatency > 500 ? "var(--warning)" : "var(--success)"}
        />
        <StatCard
          label="Avg Health Score"
          value={metrics.avgHealthScore}
          sub={metrics.avgHealthScore >= 0.8 ? "excellent" : metrics.avgHealthScore >= 0.5 ? "fair" : "poor"}
          color={metrics.avgHealthScore >= 0.8 ? "var(--success)" : metrics.avgHealthScore >= 0.5 ? "var(--warning)" : "var(--error)"}
        />
        <StatCard
          label="Providers"
          value={metrics.providerCount}
          sub={`${metrics.healthyCount} healthy`}
        />
        <StatCard
          label="Total Models"
          value={metrics.totalModels}
          sub={`across ${metrics.providerCount} providers`}
        />
        <StatCard
          label="Free Models"
          value={metrics.freeModelCount}
          sub="no cost to use"
          color="var(--success)"
        />
        <StatCard
          label="Offline Providers"
          value={metrics.offlineCount}
          sub={metrics.offlineCount === 0 ? "all operational" : "need attention"}
          color={metrics.offlineCount > 0 ? "var(--error)" : "var(--success)"}
        />
      </div>

      <div className="aio-section-title" style={{ marginTop: 24 }}>Provider Health Breakdown</div>
      <div className="aio-model-table-wrap">
        <table className="aio-model-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>State</th>
              <th>Score</th>
              <th>Latency</th>
              <th>Checks</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(health).map(([pid, h]) => {
              const icon = PROVIDER_ICONS[pid] || "🔗";
              const stateColor = STATE_COLORS[h.state] || "#6b7280";
              return (
                <tr key={pid}>
                  <td>
                    {icon} {pid}
                  </td>
                  <td>
                    <span style={{ color: stateColor }}>{h.state}</span>
                  </td>
                  <td>{h.health_score.toFixed(2)}</td>
                  <td>{Math.round(h.latency_ms)}ms</td>
                  <td>{h.total_checks}</td>
                </tr>
              );
            })}
            {Object.keys(health).length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", padding: 24, color: "var(--text-secondary)" }}>
                  No health data available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default PerformanceView;
