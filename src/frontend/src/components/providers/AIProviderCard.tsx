import { useState } from "react";
import ProviderStatusBadge from "./ProviderStatusBadge";
import ProviderConfigurationDialog from "./ProviderConfigurationDialog";
import { fetchApi } from "../../services/api";
import type { ProviderInfo, Model } from "./types";

interface AIProviderCardProps {
  provider: ProviderInfo;
  onUpdate: () => void;
  onRemove: (id: string) => void;
}

export default function AIProviderCard({ provider, onUpdate, onRemove }: AIProviderCardProps) {
  const [configOpen, setConfigOpen] = useState(false);
  const [testing, setTesting] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [showFreeOnly, setShowFreeOnly] = useState(true);

  const handleTest = async () => {
    setTesting(true);
    try {
      await fetchApi(`/providers/${provider.id}/test`, { method: "POST" });
      onUpdate();
    } catch {} finally {
      setTesting(false);
    }
  };

  const handleSetDefault = async () => {
    try {
      await fetchApi(`/providers/${provider.id}/default`, { method: "PUT" });
      onUpdate();
    } catch {}
  };

  const handleRemove = async () => {
    if (!window.confirm("Remove this provider?")) return;
    setRemoving(true);
    try {
      await fetchApi(`/providers/${provider.id}`, { method: "DELETE" });
      onRemove(provider.id);
    } catch {} finally {
      setRemoving(false);
    }
  };

  const handleToggleModel = async (modelId: string, enabled: boolean) => {
    try {
      await fetchApi(`/providers/${provider.id}/models`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId, enabled }),
      });
      onUpdate();
    } catch {}
  };

  const handleRefreshModels = async () => {
    setRefreshing(true);
    try {
      await fetchApi(`/providers/${provider.id}/models/refresh`, { method: "POST" });
      onUpdate();
    } catch {} finally {
      setRefreshing(false);
    }
  };

  const handleConfigSave = () => {
    setConfigOpen(false);
    onUpdate();
  };

  const models: Model[] = provider.models || [];
  const filteredModels = showFreeOnly ? models.filter((m) => m.isFree) : models;

  return (
    <>
      <div className="pr-provider-card">
        <div className="pr-provider-card-top">
          <div className="pr-provider-card-info">
            <div className="pr-provider-card-name">{provider.name}</div>
            <ProviderStatusBadge status={provider.status} latencyMs={provider.latency_ms} />
          </div>
          {provider.is_default && (
            <div className="pr-provider-default-badge">Default</div>
          )}
        </div>

        {provider.has_api_key && (
          <div className="pr-provider-api-key-indicator">
            <span className="pr-dot pr-dot-green" /> API Key Configured
          </div>
        )}

        <div className="pr-provider-card-meta">
          <div className="pr-provider-card-meta-item">
            <span className="pr-provider-card-meta-label">Type</span>
            <span className="pr-provider-card-meta-value">{provider.type}</span>
          </div>
          <div className="pr-provider-card-meta-item">
            <span className="pr-provider-card-meta-label">Models</span>
            <span className="pr-provider-card-meta-value">
              {models.filter((m) => m.enabled).length} / {models.length} enabled
            </span>
          </div>
          <div className="pr-provider-card-meta-item">
            <span className="pr-provider-card-meta-label">Health</span>
            <span className="pr-provider-card-meta-value">
              <span className={`pr-health-dot ${provider.status === "healthy" ? "healthy" : provider.status === "degraded" ? "degraded" : provider.status === "rate_limited" ? "rate-limited" : provider.status === "quota_exhausted" ? "quota-exhausted" : provider.status === "offline" ? "offline" : provider.status === "invalid_key" ? "invalid-key" : "unknown"}`} />
              {" "}{provider.status === "healthy" ? "Healthy" : provider.status === "degraded" ? "Degraded" : provider.status === "rate_limited" ? "Rate Limited" : provider.status === "quota_exhausted" ? "Quota Exhausted" : provider.status === "offline" ? "Offline" : provider.status === "invalid_key" ? "Invalid Key" : provider.status === "not_configured" ? "Not Configured" : "Unknown"}
            </span>
          </div>
          {provider.last_checked && (
            <div className="pr-provider-card-meta-item">
              <span className="pr-provider-card-meta-label">Last Checked</span>
              <span className="pr-provider-card-meta-value">
                {formatRelativeTime(provider.last_checked)}
              </span>
            </div>
          )}
        </div>

        {models.length > 0 && (
          <div className="pr-provider-card-models">
            <div className="pr-provider-card-models-header">
              <span className="pr-provider-card-models-title">Available Models</span>
              <label className="pr-free-toggle">
                <input
                  type="checkbox"
                  checked={showFreeOnly}
                  onChange={(e) => setShowFreeOnly(e.target.checked)}
                />
                <span>Show free only</span>
              </label>
            </div>
            <div className="pr-provider-card-models-list">
              {filteredModels.map((m) => (
                <label key={m.id} className="pr-model-checkbox">
                  <input
                    type="checkbox"
                    checked={m.enabled}
                    onChange={(e) => handleToggleModel(m.id, e.target.checked)}
                    disabled={m.deprecated}
                  />
                  <span className="pr-model-checkbox-name">
                    {m.displayName}
                    {m.recommended && <span className="pr-model-badge pr-model-badge-rec">Recommended</span>}
                    {m.deprecated && <span className="pr-model-badge pr-model-badge-dep">Deprecated</span>}
                    {m.isFree && <span className="pr-model-badge pr-model-badge-free">Free</span>}
                    {!m.isFree && m.costPer1kInput === 0 && m.costPer1kOutput === 0 && (
                      <span className="pr-commercial-badge local">Local</span>
                    )}
                    {!m.isFree && (m.costPer1kInput > 0 || m.costPer1kOutput > 0) && (
                      <span className="pr-commercial-badge paid">Paid</span>
                    )}
                  </span>
                  <span className="pr-model-checkbox-meta">
                    {m.contextLength.toLocaleString()} ctx
                    {m.supportsVision && " \u{1F5BC}"}
                    {m.supportsReasoning && " \u{1F9E0}"}
                  </span>
                </label>
              ))}
            </div>
            {filteredModels.length === 0 && (
              <div className="pr-provider-card-models-empty">
                {showFreeOnly ? "No free models available. Toggle \"Show free only\" off." : "No models available."}
              </div>
            )}
          </div>
        )}

        <div className="pr-provider-card-actions">
          <button className="btn btn-primary" onClick={() => setConfigOpen(true)}>
            Configure
          </button>

          <button
            className="btn btn-secondary"
            onClick={handleRefreshModels}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing..." : "Refresh Models"}
          </button>

          {provider.status !== "not_configured" && (
            <button
              className="btn btn-secondary"
              onClick={handleTest}
              disabled={testing}
            >
              {testing ? "Testing..." : "Test"}
            </button>
          )}

          {!provider.is_default && (
            <button className="btn btn-secondary" onClick={handleSetDefault}>
              Set Default
            </button>
          )}

          <button
            className="btn btn-secondary pr-remove-btn"
            onClick={handleRemove}
            disabled={removing}
          >
            {removing ? "Removing..." : "Remove"}
          </button>
        </div>
      </div>

      {configOpen && (
        <ProviderConfigurationDialog
          provider={provider}
          onSave={handleConfigSave}
          onClose={() => setConfigOpen(false)}
        />
      )}
    </>
  );
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
