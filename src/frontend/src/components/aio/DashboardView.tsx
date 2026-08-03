import { useMemo } from "react";
import { useAioStore } from "./AioStore";
import StatCard from "./StatCard";

function formatRelativeTime(ts: number): string {
  if (ts === 0) return "never";
  const diff = Date.now() - ts;
  if (diff < 60_000) return `${Math.round(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
  return `${Math.round(diff / 86_400_000)}d ago`;
}

function DashboardView() {
  const store = useAioStore();

  const stats = useMemo(() => {
    const { providers, health, freeModels, lastRefresh } = store;

    const healthEntries = Object.values(health);

    const configuredProviders = providers.length;

    const healthyProviders = healthEntries.filter(
      (h) => h.state === "healthy"
    ).length;

    const offlineProviders = healthEntries.filter((h) =>
      ["unreachable", "invalid_key", "quota_exceeded", "offline"].includes(
        h.state
      )
    ).length;

    const totalModels = providers.reduce(
      (sum, p) => sum + p.models.length,
      0
    );

    const freeModelCount = freeModels.length;

    const reasoningModels = providers.reduce(
      (sum, p) => sum + p.models.filter((m) => m.supportsReasoning).length,
      0
    );

    const visionModels = providers.reduce(
      (sum, p) => sum + p.models.filter((m) => m.supportsVision).length,
      0
    );

    const embeddingModels = providers.reduce(
      (sum, p) =>
        sum + p.models.filter((m) => m.supportsEmbeddings).length,
      0
    );

    const streamingProviders = providers.filter((p) =>
      p.models.some((m) => m.supportsStreaming)
    ).length;

    const avgLatency =
      healthEntries.length > 0
        ? Math.round(
            healthEntries.reduce((s, h) => s + h.latency_ms, 0) /
              healthEntries.length
          )
        : 0;

    const avgHealth =
      healthEntries.length > 0
        ? Math.round(
            (healthEntries.reduce((s, h) => s + h.health_score, 0) /
              healthEntries.length) *
              100
          ) / 100
        : 0;

    return {
      configuredProviders,
      healthyProviders,
      offlineProviders,
      totalModels,
      freeModelCount,
      reasoningModels,
      visionModels,
      embeddingModels,
      streamingProviders,
      avgLatency,
      avgHealth,
      lastRefresh: formatRelativeTime(lastRefresh),
    };
  }, [store]);

  return (
    <div className="aio-stats-grid">
      <StatCard
        label="Configured Providers"
        value={stats.configuredProviders}
        sub="across all types"
        color="var(--accent)"
      />
      <StatCard
        label="Healthy Providers"
        value={stats.healthyProviders}
        sub={`${stats.configuredProviders - stats.healthyProviders} need attention`}
        color="var(--success)"
      />
      <StatCard
        label="Offline Providers"
        value={stats.offlineProviders}
        sub={stats.offlineProviders === 0 ? "all systems operational" : "action required"}
        color={stats.offlineProviders > 0 ? "var(--error)" : "var(--success)"}
      />
      <StatCard
        label="Total Models"
        value={stats.totalModels}
        sub={`across ${stats.configuredProviders} providers`}
      />
      <StatCard
        label="Free Models"
        value={stats.freeModelCount}
        sub="no cost to use"
        color="var(--success)"
      />
      <StatCard
        label="Reasoning Models"
        value={stats.reasoningModels}
        sub="chain-of-thought capable"
        color="var(--accent)"
      />
      <StatCard
        label="Vision Models"
        value={stats.visionModels}
        sub="image understanding"
        color="var(--accent)"
      />
      <StatCard
        label="Embedding Models"
        value={stats.embeddingModels}
        sub="vector generation"
      />
      <StatCard
        label="Streaming Providers"
        value={stats.streamingProviders}
        sub="real-time response"
        color="var(--success)"
      />
      <StatCard
        label="Avg Latency"
        value={`${stats.avgLatency}ms`}
        sub="across all providers"
        color={stats.avgLatency > 500 ? "var(--warning)" : "var(--success)"}
      />
      <StatCard
        label="Avg Health Score"
        value={stats.avgHealth}
        sub={stats.avgHealth >= 0.8 ? "excellent" : stats.avgHealth >= 0.5 ? "fair" : "poor"}
        color={stats.avgHealth >= 0.8 ? "var(--success)" : stats.avgHealth >= 0.5 ? "var(--warning)" : "var(--error)"}
      />
      <StatCard
        label="Last Refresh"
        value={stats.lastRefresh}
        sub="auto-polling active"
      />
    </div>
  );
}

export default DashboardView;
