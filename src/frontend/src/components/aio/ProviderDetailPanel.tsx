import type { AioProvider, AioHealthEntry } from "./aioTypes";
import { useAioStore } from "./AioStore";

interface Props {
  provider: AioProvider;
  health?: AioHealthEntry;
  onClose: () => void;
}

function featureLine(label: string, supported: boolean | undefined) {
  return (
    <div className="aio-detail-feature">
      <span>{supported ? "✓" : "✗"}</span>
      <span>{label}</span>
    </div>
  );
}

function ProviderDetailPanel({ provider, health, onClose }: Props) {
  const { diagnostics } = useAioStore();

  const providerDiag = diagnostics?.capabilities?.[provider.id];
  const capabilities = providerDiag?.capabilities ?? [];
  const diagModels = providerDiag?.models ?? [];
  const freeCount = diagModels.filter((m) => m.isFree === true).length;

  const enabledModels = provider.models.filter((m) => m.enabled !== false).length;
  const totalModels = provider.models.length;

  const rateLimit = health?.rate_limit;

  const firstModel = diagModels.length > 0 ? diagModels[0] : provider.models[0];

  return (
    <div className="aio-provider-detail">
      <section className="aio-detail-section">
        <h4>Auth & Endpoint</h4>
        <div>
          {provider.has_api_key ? "✓ API key configured" : "✗ No API key"}
        </div>
        {provider.endpoint_url && (
          <div className="aio-detail-endpoint">{provider.endpoint_url}</div>
        )}
      </section>

      <section className="aio-detail-section">
        <h4>Health</h4>
        <div className="aio-detail-kv">
          <span>State:</span>
          <span>{health?.state ?? "—"}</span>
        </div>
        <div className="aio-detail-kv">
          <span>Health Score:</span>
          <span>{health?.health_score != null ? health.health_score.toFixed(1) : "—"}</span>
        </div>
        <div className="aio-detail-kv">
          <span>Success Rate:</span>
          <span>{health?.success_rate != null ? `${(health.success_rate * 100).toFixed(1)}%` : "—"}</span>
        </div>
        <div className="aio-detail-kv">
          <span>Latency:</span>
          <span>{health?.latency_ms != null ? `${health.latency_ms}ms` : "—"}</span>
        </div>
        <div className="aio-detail-kv">
          <span>Total Checks:</span>
          <span>{health?.total_checks ?? "—"}</span>
        </div>
        <div className="aio-detail-kv">
          <span>Consecutive Failures:</span>
          <span>{health?.consecutive_failures ?? 0}</span>
        </div>
      </section>

      <section className="aio-detail-section">
        <h4>Rate Limits</h4>
        <div className="aio-detail-kv">
          <span>State:</span>
          <span>{rateLimit?.state ?? "—"}</span>
        </div>
        <div className="aio-detail-kv">
          <span>Cooldown:</span>
          <span>{rateLimit?.cooldown_remaining != null ? `${rateLimit.cooldown_remaining}s` : "—"}</span>
        </div>
        <div className="aio-detail-kv">
          <span>Consecutive 429s:</span>
          <span>{rateLimit?.consecutive_429s ?? 0}</span>
        </div>
      </section>

      <section className="aio-detail-section">
        <h4>Capabilities</h4>
        {capabilities.length === 0 ? (
          <div className="aio-detail-empty">No capabilities detected</div>
        ) : (
          <div className="aio-detail-cap-list">
            {capabilities.map((cap) => (
              <span key={cap} className="aio-detail-cap-tag">{cap}</span>
            ))}
          </div>
        )}
      </section>

      <section className="aio-detail-section">
        <h4>Models</h4>
        <div className="aio-detail-kv">
          <span>Enabled / Total:</span>
          <span>{enabledModels} / {totalModels}</span>
        </div>
        <div className="aio-detail-kv">
          <span>Free Models:</span>
          <span>{freeCount}</span>
        </div>
      </section>

      <section className="aio-detail-section">
        <h4>Commercial Policy</h4>
        <div>{diagnostics?.commercial_policy ?? "—"}</div>
      </section>

      <section className="aio-detail-section">
        <h4>Supported Features</h4>
        {featureLine("Vision", firstModel?.supportsVision)}
        {featureLine("Streaming", firstModel?.supportsStreaming)}
        {featureLine("JSON", firstModel?.supportsJSON)}
        {featureLine("Tools", firstModel?.supportsTools)}
        {featureLine("Reasoning", firstModel?.supportsReasoning)}
        {featureLine("Embeddings", firstModel?.supportsEmbeddings)}
        {featureLine("Audio", firstModel?.supportsAudio)}
      </section>

      <button className="aio-btn aio-btn-ghost aio-detail-close" onClick={onClose}>
        Close
      </button>
    </div>
  );
}

export default ProviderDetailPanel;
