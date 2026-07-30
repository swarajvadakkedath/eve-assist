import { useState, useEffect, useRef } from "react";
import { fetchApi } from "../../services/api";
import type { ProviderInfo, Model, RoutingPolicy } from "../providers/types";
import { ROUTING_POLICY_OPTIONS } from "../providers/types";

interface ConversationHeaderProps {
  currentProviderId?: string;
  currentModelId?: string;
  currentRoutingPolicy?: RoutingPolicy;
  onProviderChange: (providerId: string) => void;
  onModelChange: (modelId: string) => void;
  onRoutingPolicyChange?: (policy: RoutingPolicy) => void;
}

export default function ConversationHeader({
  currentProviderId,
  currentModelId,
  currentRoutingPolicy = "auto",
  onProviderChange,
  onModelChange,
  onRoutingPolicyChange,
}: ConversationHeaderProps) {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetchedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    fetchApi("/providers")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        const all = (data.providers || []) as ProviderInfo[];
        setProviders(all);
        setLoading(false);
        fetchedRef.current = true;
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const activeProvider = providers.find((p) => p.id === currentProviderId);
  const enabledModels = (activeProvider?.models || []).filter((m) => m.enabled);
  const hasActiveModel = enabledModels.some((m) => m.id === currentModelId);

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const pid = e.target.value;
    const prov = providers.find((p) => p.id === pid);
    const firstEnabled = prov?.models.find((m: Model) => m.enabled);
    onProviderChange(pid);
    if (firstEnabled) {
      onModelChange(firstEnabled.id);
    } else {
      onModelChange("");
    }
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onModelChange(e.target.value);
  };

  const handleRoutingPolicyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onRoutingPolicyChange?.(e.target.value as RoutingPolicy);
  };

  if (loading) {
    return (
      <div className="conversation-header">
        <div className="conversation-header-skeleton" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="conversation-header">
        <span className="conversation-header-error">Failed to load providers: {error}</span>
      </div>
    );
  }

  const connectedProviders = providers.filter(
    (p) => p.status === "connected" && p.models?.length > 0
  );

  if (connectedProviders.length === 0) {
    return (
      <div className="conversation-header">
        <span className="conversation-header-empty">
          No providers connected — add one in Settings to start chatting.
        </span>
      </div>
    );
  }

  const currentPolicy = ROUTING_POLICY_OPTIONS.find(o => o.value === currentRoutingPolicy) || ROUTING_POLICY_OPTIONS[0];

  return (
    <div className="conversation-header">
      <div className="conversation-header-group">
        <label className="conversation-header-label">Provider</label>
        <select
          className="conversation-header-select"
          value={currentProviderId || ""}
          onChange={handleProviderChange}
        >
          {connectedProviders.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
      {activeProvider && (
        <div className="conversation-header-group">
          <label className="conversation-header-label">Model</label>
          <select
            className="conversation-header-select"
            value={hasActiveModel ? (currentModelId || "") : ""}
            onChange={handleModelChange}
          >
            {!hasActiveModel && currentModelId && (
              <option value="" disabled>
                {currentModelId} (unavailable)
              </option>
            )}
            {enabledModels.map((m) => (
              <option key={m.id} value={m.id}>
                {m.displayName}
                {m.isFree ? " (Free)" : ""}
              </option>
            ))}
          </select>
        </div>
      )}
      {onRoutingPolicyChange && (
        <div className="conversation-header-group">
          <label className="conversation-header-label">Routing</label>
          <select
            className="conversation-header-select conversation-header-routing"
            value={currentRoutingPolicy}
            onChange={handleRoutingPolicyChange}
            title={currentPolicy.description}
          >
            {ROUTING_POLICY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
