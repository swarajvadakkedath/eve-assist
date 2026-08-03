import { useState } from "react";
import { useAioStore } from "./AioStore";
import FallbackGraph from "./FallbackGraph";
import { PROVIDER_ICONS, STATE_COLORS } from "./aioTypes";

function SmartRouterView() {
  const { routing, categories, policy, diagnostics, providers, health } = useAioStore();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  function getProviderName(providerId: string | null): string {
    if (!providerId) return "Auto";
    const p = providers.find((pr) => pr.id === providerId);
    return p?.name ?? providerId;
  }

  function getProviderIcon(providerId: string | null): string {
    if (!providerId) return "🧭";
    const p = providers.find((pr) => pr.id === providerId);
    return PROVIDER_ICONS[p?.type ?? ""] ?? "❓";
  }

  function getRoutingEntry(categoryId: string) {
    return routing.find((r) => r.id === categoryId);
  }

  function getCapabilitiesForCategory(categoryId: string): string[] {
    const cat = categories.find((c) => c.id === categoryId);
    return cat?.capabilities ?? [];
  }

  function getDiagnosticCount(categoryId: string): number | null {
    if (!diagnostics?.capabilities) return null;
    const entry = diagnostics.capabilities[categoryId];
    return entry?.models?.length ?? null;
  }

  return (
    <div>
      <div className="aio-section-title">SmartRouter</div>

      <div className="aio-routing-card" style={{ marginBottom: 20 }}>
        <div className="aio-routing-label">Commercial Policy</div>
        <span
          className="aio-provider-badge"
          style={{
            background: policy === "free_only" ? "rgba(34,197,94,0.15)" : "rgba(255,255,255,0.06)",
            color: policy === "free_only" ? "#22c55e" : "var(--text-primary)",
          }}
        >
          {policy.toUpperCase().replace("_", " ")}
        </span>
      </div>

      <div className="aio-section-sub">Routing Categories</div>
      {categories.map((cat) => {
        const entry = getRoutingEntry(cat.id);
        const caps = getCapabilitiesForCategory(cat.id);
        const modelCount = getDiagnosticCount(cat.id);
        const isSelected = selectedCategory === cat.id;

        return (
          <div
            key={cat.id}
            className="aio-routing-card"
            style={{ cursor: "pointer", borderColor: isSelected ? "var(--accent)" : undefined }}
            onClick={() => setSelectedCategory(isSelected ? null : cat.id)}
          >
            <div className="aio-routing-label">{cat.label}</div>
            {entry ? (
              <div className="aio-routing-target">
                <span style={{ marginRight: 6 }}>{getProviderIcon(entry.provider_id)}</span>
                {entry.provider_id ? getProviderName(entry.provider_id) : "Auto"}
                {entry.model_id && (
                  <span style={{ fontFamily: "monospace", fontSize: 12, marginLeft: 6 }}>
                    → {entry.model_id}
                  </span>
                )}
              </div>
            ) : (
              <div className="aio-routing-target" style={{ opacity: 0.5 }}>No routing configured</div>
            )}
            <div className="aio-routing-caps">
              {caps.map((cap) => (
                <span key={cap} className="aio-cap-tag">{cap}</span>
              ))}
            </div>
            {modelCount !== null && isSelected && (
              <div style={{ marginTop: 8, fontSize: 12, color: "var(--text-secondary)" }}>
                {modelCount} eligible model{modelCount !== 1 ? "s" : ""}
              </div>
            )}
          </div>
        );
      })}

      {categories.length === 0 && (
        <div className="aio-empty">
          <div className="aio-empty-icon">🧭</div>
          <div>No routing categories configured.</div>
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <div className="aio-section-title">Fallback Chain</div>
        <div className="aio-routing-card">
          <FallbackGraph />
        </div>
      </div>

      {diagnostics && (
        <div style={{ marginTop: 24 }}>
          <div className="aio-section-title">Routing Diagnostics</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
            {Object.entries(health).map(([pid, h]) => {
              const provider = providers.find((p) => p.id === pid);
              const color = STATE_COLORS[h.state] ?? "#6b7280";
              return (
                <div
                  key={pid}
                  className="aio-routing-card"
                  style={{ padding: 12 }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background: color,
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontWeight: 600, fontSize: 13 }}>
                      {PROVIDER_ICONS[provider?.type ?? ""] ?? "❓"} {provider?.name ?? pid}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                    <div>State: {h.state}</div>
                    <div>Latency: {h.latency_ms > 0 ? `${h.latency_ms.toFixed(0)}ms` : "—"}</div>
                    <div>Score: {h.health_score.toFixed(0)}</div>
                    {h.rate_limit.state !== "ok" && (
                      <div style={{ color: STATE_COLORS[h.rate_limit.state] ?? "#f97316" }}>
                        Rate: {h.rate_limit.state}
                        {h.rate_limit.cooldown_remaining > 0 && (
                          <span> ({Math.ceil(h.rate_limit.cooldown_remaining)}s)</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default SmartRouterView;
