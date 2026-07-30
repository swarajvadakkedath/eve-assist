import { useState, useEffect } from "react";
import { fetchApi } from "../../services/api";
import type { ProviderInfo, RoutingEntry, CommercialPolicy } from "./types";
import { COMMERCIAL_POLICY_OPTIONS } from "./types";

interface SmartRoutingPanelProps {
  providers: ProviderInfo[];
  onUpdate: () => void;
}

const ROUTING_CATEGORIES = [
  { id: "general_chat", label: "General Chat", desc: "Most conversations, assistant responses" },
  { id: "coding", label: "Coding", desc: "Code generation, debugging, file operations" },
  { id: "vision", label: "Vision", desc: "Image analysis, OCR, screen understanding" },
  { id: "reasoning", label: "Reasoning", desc: "Complex logic, planning, analysis" },
  { id: "fallback", label: "Fallback", desc: "Used when primary provider fails" },
];

function healthDotClass(status: string): string {
  if (status === "healthy" || status === "connected") return "healthy";
  if (status === "degraded") return "degraded";
  if (status === "rate_limited") return "rate-limited";
  if (status === "quota_exhausted") return "quota-exhausted";
  if (status === "offline") return "offline";
  if (status === "invalid_key") return "invalid-key";
  return "unknown";
}

export default function SmartRoutingPanel({ providers, onUpdate }: SmartRoutingPanelProps) {
  const [routing, setRouting] = useState<RoutingEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [commercialPolicy, setCommercialPolicy] = useState<CommercialPolicy>("allow_paid");
  const [showPaidConfirm, setShowPaidConfirm] = useState(false);
  const [pendingPolicy, setPendingPolicy] = useState<CommercialPolicy | null>(null);
  const [diagnostics, setDiagnostics] = useState<any>(null);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  useEffect(() => {
    fetchApi("/routing")
      .then((r) => r.json())
      .then((data) => {
        if (data.routing) {
          setRouting(data.routing);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));

    fetchApi("/routing/commercial-policy")
      .then((r) => r.json())
      .then((data) => {
        if (data.policy) setCommercialPolicy(data.policy);
      })
      .catch(() => {});
  }, []);

  const handleProviderChange = (categoryId: string, providerId: string) => {
    setRouting((prev) => {
      const prov = providers.find((p) => p.id === providerId);
      const firstModel = prov?.models?.find((m) => m.enabled)?.id || "";
      return prev.map((r) =>
        r.id === categoryId ? { ...r, provider_id: providerId || null, model_id: firstModel } : r
      );
    });
    setDirty(true);
  };

  const handleModelChange = (categoryId: string, modelId: string) => {
    setRouting((prev) =>
      prev.map((r) => (r.id === categoryId ? { ...r, model_id: modelId || null } : r))
    );
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetchApi("/routing", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ routing }),
      });
      setDirty(false);
      onUpdate();
    } catch {} finally {
      setSaving(false);
    }
  };

  const handlePolicyChange = async (newPolicy: CommercialPolicy) => {
    if (newPolicy === "allow_paid" && commercialPolicy !== "allow_paid") {
      setPendingPolicy(newPolicy);
      setShowPaidConfirm(true);
      return;
    }
    await savePolicy(newPolicy);
  };

  const savePolicy = async (newPolicy: CommercialPolicy) => {
    try {
      await fetchApi("/routing/commercial-policy", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ policy: newPolicy }),
      });
      setCommercialPolicy(newPolicy);
    } catch {}
  };

  const loadDiagnostics = async () => {
    try {
      const res = await fetchApi("/routing/diagnostics");
      const data = await res.json();
      setDiagnostics(data);
      setShowDiagnostics(true);
    } catch {}
  };

  if (loading) {
    return <div className="pr-loading">Loading routing...</div>;
  }

  const connectedProviders = providers.filter((p) => p.status !== "not_configured");

  return (
    <div className="pr-routing-panel">
      <div className="pr-routing-header" onClick={() => setCollapsed(!collapsed)}>
        <span className="pr-routing-title">Smart Routing</span>
        <span className="pr-routing-toggle">{collapsed ? "\u25B6" : "\u25BC"}</span>
        {dirty && <span className="pr-routing-unsaved">Unsaved changes</span>}
      </div>

      {!collapsed && (
        <div className="pr-routing-body">
          <p className="pr-routing-desc">
            Route different types of tasks to different AI providers and models.
            Each category can use a different provider and model for optimal performance.
          </p>

          {ROUTING_CATEGORIES.map((cat) => {
            const entry = routing.find((r) => r.id === cat.id);
            const selectedProvider = providers.find((p) => p.id === entry?.provider_id);
            const enabledModels = (selectedProvider?.models || []).filter((m) => m.enabled);

            return (
              <div key={cat.id} className="pr-routing-row">
                <div className="pr-routing-row-info">
                  <div className="pr-routing-row-label">{cat.label}</div>
                  <div className="pr-routing-row-desc">{cat.desc}</div>
                </div>
                <div className="pr-routing-row-controls">
                  <select
                    value={entry?.provider_id || ""}
                    onChange={(e) => handleProviderChange(cat.id, e.target.value)}
                    className="pr-routing-select"
                  >
                    <option value="">Use default provider</option>
                    {connectedProviders.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} {p.is_default ? "(Default)" : ""}
                      </option>
                    ))}
                  </select>
                  <select
                    value={entry?.model_id || ""}
                    onChange={(e) => handleModelChange(cat.id, e.target.value)}
                    className="pr-routing-select"
                    disabled={!entry?.provider_id}
                  >
                    {enabledModels.length === 0 && <option value="">No models</option>}
                    {enabledModels.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.displayName} {m.isFree ? "(Free)" : m.costPer1kInput > 0 ? "(Paid)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            );
          })}

          <div className="pr-routing-commercial">
            <label className="pr-routing-commercial-label">Cost Policy</label>
            <select
              value={commercialPolicy}
              onChange={(e) => handlePolicyChange(e.target.value as CommercialPolicy)}
              className="pr-routing-select"
            >
              {COMMERCIAL_POLICY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label} — {opt.description}
                </option>
              ))}
            </select>
          </div>

          <div className="pr-routing-diagnostics-toggle" onClick={loadDiagnostics}>
            {showDiagnostics ? "Hide Diagnostics" : "Show Diagnostics"}
          </div>

          {showDiagnostics && diagnostics && (
            <div className="pr-routing-diagnostics">
              <div className="pr-routing-diagnostics-title">Routing Diagnostics</div>
              <div className="pr-routing-diagnostics-grid">
                <div className="pr-routing-diagnostics-item">
                  <span className="pr-routing-diagnostics-label">Total Candidates</span>
                  <span className="pr-routing-diagnostics-value">{diagnostics.candidate_count ?? "N/A"}</span>
                </div>
                <div className="pr-routing-diagnostics-item">
                  <span className="pr-routing-diagnostics-label">Registered Providers</span>
                  <span className="pr-routing-diagnostics-value">{diagnostics.registered_providers ?? "N/A"}</span>
                </div>
                <div className="pr-routing-diagnostics-item">
                  <span className="pr-routing-diagnostics-label">Commercial Policy</span>
                  <span className="pr-routing-diagnostics-value">{diagnostics.commercial_policy ?? "N/A"}</span>
                </div>
              </div>
              {diagnostics.health_summary && (
                <div className="pr-routing-diagnostics-health">
                  <div className="pr-routing-diagnostics-subtitle">Provider Health</div>
                  {Object.entries(diagnostics.health_summary as Record<string, string>).map(([pid, status]) => (
                    <div key={pid} className="pr-routing-diagnostics-health-row">
                      <span className={`pr-health-dot ${healthDotClass(String(status))}`} />
                      <span>{pid}</span>
                      <span className="pr-routing-diagnostics-health-status">{String(status)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="pr-routing-footer">
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={saving || !dirty}
            >
              {saving ? "Saving..." : "Save Routing"}
            </button>
          </div>
        </div>
      )}

      {showPaidConfirm && (
        <div className="pr-settings-ai-confirm-overlay" onClick={() => setShowPaidConfirm(false)}>
          <div className="pr-settings-ai-confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>Allow paid AI routes?</h4>
            <p>
              Eve may use models that generate charges on configured provider accounts
              when free or included routes cannot satisfy a request.
            </p>
            <div className="pr-settings-ai-confirm-actions">
              <button className="btn btn-secondary" onClick={() => setShowPaidConfirm(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => { if (pendingPolicy) savePolicy(pendingPolicy); setShowPaidConfirm(false); }}>Allow Paid Routes</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
