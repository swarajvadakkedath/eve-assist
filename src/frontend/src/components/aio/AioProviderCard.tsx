import { useState, useCallback } from "react";
import type { AioProvider, AioHealthEntry } from "./aioTypes";
import { PROVIDER_ICONS, PROVIDER_DISPLAY_NAMES, STATE_COLORS } from "./aioTypes";
import { aioStore } from "./AioStore";
import ProviderDetailPanel from "./ProviderDetailPanel";

interface Props {
  provider: AioProvider;
  health?: AioHealthEntry;
}

function AioProviderCard({ provider, health }: Props) {
  const [testing, setTesting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showDetail, setShowDetail] = useState(false);

  const handleTest = useCallback(async () => {
    setTesting(true);
    try {
      await aioStore.testProvider(provider.id);
    } finally {
      setTesting(false);
    }
  }, [provider.id]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await aioStore.refreshModels(provider.id);
    } finally {
      setRefreshing(false);
    }
  }, [provider.id]);

  const handleViewModels = useCallback(() => {
    window.dispatchEvent(new CustomEvent("aios:aio-tab", { detail: "models" }));
  }, []);

  const handleToggleDetail = useCallback(() => {
    setShowDetail((v) => !v);
  }, []);

  const icon = PROVIDER_ICONS[provider.type] || "⚪";
  const displayName = PROVIDER_DISPLAY_NAMES[provider.type] || provider.name;
  const state = health?.state || "unknown";
  const enabledModels = provider.models.filter((m) => m.enabled !== false).length;
  const totalModels = provider.models.length;
  const latency = health?.latency_ms ?? provider.latency_ms ?? null;
  const healthScore = health?.health_score ?? null;
  const successRate = health?.success_rate ?? null;

  return (
    <div className="aio-provider-card" data-status={state}>
      <div className="aio-provider-header">
        <span className="aio-provider-icon">{icon}</span>
        <span className="aio-provider-name">{displayName}</span>
        <span
          className="aio-health-badge"
          style={{ backgroundColor: STATE_COLORS[state] || STATE_COLORS.unknown }}
        >
          {state}
        </span>
      </div>

      <div className="aio-provider-metrics">
        <div className="aio-metric">
          <span className="aio-metric-label">Latency</span>
          <span className="aio-metric-value">{latency != null ? `${latency}ms` : "—"}</span>
        </div>
        <div className="aio-metric">
          <span className="aio-metric-label">Health Score</span>
          <span className="aio-metric-value">{healthScore != null ? healthScore.toFixed(0) : "—"}</span>
        </div>
        <div className="aio-metric">
          <span className="aio-metric-label">Success Rate</span>
          <span className="aio-metric-value">{successRate != null ? `${(successRate * 100).toFixed(0)}%` : "—"}</span>
        </div>
        <div className="aio-metric">
          <span className="aio-metric-label">Models</span>
          <span className="aio-metric-value">{enabledModels}/{totalModels}</span>
        </div>
      </div>

      {showDetail && (
        <ProviderDetailPanel
          provider={provider}
          health={health}
          onClose={() => setShowDetail(false)}
        />
      )}

      <div className="aio-provider-actions">
        <button
          className="aio-btn aio-btn-primary"
          onClick={handleTest}
          disabled={testing}
        >
          {testing ? "Testing…" : "Test"}
        </button>
        <button
          className="aio-btn aio-btn-secondary"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? "Refreshing…" : "Refresh Models"}
        </button>
        <button className="aio-btn aio-btn-secondary" onClick={handleViewModels}>
          View Models
        </button>
        <button className="aio-btn aio-btn-ghost" onClick={handleToggleDetail}>
          {showDetail ? "Hide Details" : "Details"}
        </button>
      </div>
    </div>
  );
}

export default AioProviderCard;
