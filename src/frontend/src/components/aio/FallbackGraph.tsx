import { Fragment } from "react";
import { useAioStore } from "./AioStore";
import { PROVIDER_ICONS, STATE_COLORS } from "./aioTypes";

interface RankedProvider {
  rank: number;
  id: string;
  name: string;
  icon: string;
  state: string;
  healthScore: number;
}

function FallbackGraph() {
  const { providers, health } = useAioStore();

  const ranked: RankedProvider[] = providers
    .map((p, i) => {
      const h = health[p.id];
      return {
        rank: i + 1,
        id: p.id,
        name: p.name,
        icon: PROVIDER_ICONS[p.type] ?? "❓",
        state: h?.state ?? "unknown",
        healthScore: h?.health_score ?? 0,
      };
    })
    .sort((a, b) => b.healthScore - a.healthScore);

  if (ranked.length === 0) {
    return (
      <div className="aio-empty" style={{ padding: 24 }}>
        <div>No providers available.</div>
      </div>
    );
  }

  return (
    <div className="aio-fallback-graph">
      {ranked.map((p, idx) => (
        <Fragment key={p.id}>
          <div className="aio-fallback-node">
            <div className="aio-fallback-rank">{p.rank}</div>
            <span style={{ fontSize: 18 }}>{p.icon}</span>
            <span style={{ fontWeight: 600, fontSize: 13, flex: 1 }}>{p.name}</span>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: STATE_COLORS[p.state] ?? "#6b7280",
                flexShrink: 0,
              }}
            />
            <span style={{ fontSize: 12, color: "var(--text-secondary)", fontFamily: "monospace" }}>
              {p.healthScore.toFixed(0)}
            </span>
          </div>
          {idx < ranked.length - 1 && (
            <div className="aio-fallback-arrow">↓</div>
          )}
        </Fragment>
      ))}
    </div>
  );
}

export default FallbackGraph;
