import { useAioStore } from "./AioStore";

function FreeModelsView() {
  const { freeModels } = useAioStore();

  if (freeModels.length === 0) {
    return (
      <div>
        <div className="aio-section-title">Free Model Explorer</div>
        <div className="aio-empty">
          <div className="aio-empty-icon">🤖</div>
          <div>No free models available</div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="aio-section-title">Free Model Explorer</div>
      <div className="aio-section-sub">{freeModels.length} free / free-tier models</div>
      <div className="aio-model-table-wrap">
        <table className="aio-model-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Provider</th>
              <th>Type</th>
              <th>Context</th>
              <th>Vision</th>
              <th>Reasoning</th>
              <th>Tools</th>
              <th>JSON</th>
              <th>Streaming</th>
              <th>Speed</th>
              <th>Quality</th>
            </tr>
          </thead>
          <tbody>
            {freeModels.map((m) => {
              const displayName = m.displayName || m.id;
              const provider = m.providerName || m.provider || m.providerId || "—";
              const ctx = m.contextWindow ?? m.contextLength ?? null;
              return (
                <tr key={m.id}>
                  <td>{displayName}</td>
                  <td>{provider}</td>
                  <td>
                    <span
                      className={
                        m.commercialStatus === "free"
                          ? "aio-cap-yes"
                          : m.commercialStatus === "free_tier"
                          ? "aio-pill"
                          : ""
                      }
                    >
                      {m.commercialStatus || (m.isFree ? "free" : "—")}
                    </span>
                  </td>
                  <td>{ctx != null ? ctx.toLocaleString() : "—"}</td>
                  <td className={m.supportsVision ? "aio-cap-yes" : "aio-cap-no"}>
                    {m.supportsVision ? "✓" : "—"}
                  </td>
                  <td className={m.supportsReasoning ? "aio-cap-yes" : "aio-cap-no"}>
                    {m.supportsReasoning ? "✓" : "—"}
                  </td>
                  <td className={m.supportsTools ? "aio-cap-yes" : "aio-cap-no"}>
                    {m.supportsTools ? "✓" : "—"}
                  </td>
                  <td className={m.supportsJSON ? "aio-cap-yes" : "aio-cap-no"}>
                    {m.supportsJSON ? "✓" : "—"}
                  </td>
                  <td className={m.supportsStreaming ? "aio-cap-yes" : "aio-cap-no"}>
                    {m.supportsStreaming ? "✓" : "—"}
                  </td>
                  <td>{m.speed != null ? m.speed.toFixed(1) : "—"}</td>
                  <td>{m.quality != null ? m.quality.toFixed(1) : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default FreeModelsView;
