import { useState, useMemo, Fragment } from "react";
import { useAioStore } from "./AioStore";

type FilterKey = "all" | "free" | "vision" | "reasoning" | "tools" | "json" | "embeddings";
type SortKey = "name" | "provider" | "context" | "quality";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "free", label: "Free" },
  { key: "vision", label: "Vision" },
  { key: "reasoning", label: "Reasoning" },
  { key: "tools", label: "Tools" },
  { key: "json", label: "JSON" },
  { key: "embeddings", label: "Embeddings" },
];

interface FlatModel {
  id: string;
  displayName: string;
  providerType: string;
  providerInstanceId: string;
  providerDisplayName: string;
  contextWindow: number;
  commercialStatus: string;
  supportsVision: boolean;
  supportsReasoning: boolean;
  supportsTools: boolean;
  supportsJSON: boolean;
  supportsEmbeddings: boolean;
  speed: number;
  quality: number;
}

function filterModels(m: FlatModel, key: FilterKey): boolean {
  switch (key) {
    case "free": return m.commercialStatus === "free";
    case "vision": return m.supportsVision;
    case "reasoning": return m.supportsReasoning;
    case "tools": return m.supportsTools;
    case "json": return m.supportsJSON;
    case "embeddings": return m.supportsEmbeddings;
    default: return true;
  }
}

function formatCtx(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${Math.round(n / 1000)}K`;
  return String(n);
}

function sortModels(list: FlatModel[], key: SortKey): FlatModel[] {
  const sorted = [...list];
  switch (key) {
    case "name": sorted.sort((a, b) => a.displayName.localeCompare(b.displayName)); break;
    case "provider": sorted.sort((a, b) => a.providerType.localeCompare(b.providerType) || a.displayName.localeCompare(b.displayName)); break;
    case "context": sorted.sort((a, b) => b.contextWindow - a.contextWindow); break;
    case "quality": sorted.sort((a, b) => b.quality - a.quality); break;
  }
  return sorted;
}

function ModelsView() {
  const { providers } = useAioStore();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
  const [sortBy, setSortBy] = useState<SortKey>("name");
  const [grouped, setGrouped] = useState(false);

  const flatList = useMemo<FlatModel[]>(() => {
    const result: FlatModel[] = [];
    for (const provider of providers) {
      for (const m of provider.models) {
        result.push({
          id: m.id,
          displayName: m.displayName ?? m.id,
          providerType: m.providerType ?? m.provider_type ?? provider.type,
          providerInstanceId: m.providerInstanceId ?? m.provider_instance_id ?? provider.id,
          providerDisplayName: provider.name,
          contextWindow: m.contextWindow ?? m.contextLength ?? 0,
          commercialStatus: m.commercialStatus ?? (m.isFree ? "free" : "unknown"),
          supportsVision: m.supportsVision ?? false,
          supportsReasoning: m.supportsReasoning ?? m.supportsThinking ?? false,
          supportsTools: m.supportsTools ?? m.supportsFunctionCalling ?? false,
          supportsJSON: m.supportsJSON ?? false,
          supportsEmbeddings: m.supportsEmbeddings ?? false,
          speed: m.speed ?? 0,
          quality: m.quality ?? 0,
        });
      }
    }
    return result;
  }, [providers]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    let list = flatList;
    if (q) {
      list = list.filter((m) =>
        m.id.toLowerCase().includes(q) || m.displayName.toLowerCase().includes(q)
      );
    }
    if (filter !== "all") {
      list = list.filter((m) => filterModels(m, filter));
    }
    return sortModels(list, sortBy);
  }, [flatList, search, filter, sortBy]);

  const groups = useMemo(() => {
    if (!grouped) return null;
    const map = new Map<string, FlatModel[]>();
    for (const m of filtered) {
      const list = map.get(m.providerType) ?? [];
      list.push(m);
      map.set(m.providerType, list);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered, grouped]);

  function renderRow(m: FlatModel) {
    return (
      <tr key={`${m.providerInstanceId}:${m.id}`}>
        <td style={{ fontFamily: "monospace", fontSize: 12 }}>{m.id}</td>
        <td>{m.providerDisplayName}</td>
        <td>
          <span
            className="aio-provider-badge"
            style={{
              background: m.commercialStatus === "free" ? "rgba(34,197,94,0.15)" : "rgba(255,255,255,0.06)",
              color: m.commercialStatus === "free" ? "#22c55e" : "var(--text-secondary)",
            }}
          >
            {m.commercialStatus}
          </span>
        </td>
        <td>{m.contextWindow > 0 ? formatCtx(m.contextWindow) : "—"}</td>
        <td><span className={m.supportsVision ? "aio-cap-yes" : "aio-cap-no"}>{m.supportsVision ? "✓" : "—"}</span></td>
        <td><span className={m.supportsReasoning ? "aio-cap-yes" : "aio-cap-no"}>{m.supportsReasoning ? "✓" : "—"}</span></td>
        <td><span className={m.supportsTools ? "aio-cap-yes" : "aio-cap-no"}>{m.supportsTools ? "✓" : "—"}</span></td>
        <td><span className={m.supportsJSON ? "aio-cap-yes" : "aio-cap-no"}>{m.supportsJSON ? "✓" : "—"}</span></td>
        <td><span className={m.supportsEmbeddings ? "aio-cap-yes" : "aio-cap-no"}>{m.supportsEmbeddings ? "✓" : "—"}</span></td>
        <td>{m.speed > 0 ? m.speed.toFixed(1) : "—"}</td>
        <td>{m.quality > 0 ? m.quality.toFixed(1) : "—"}</td>
      </tr>
    );
  }

  return (
    <div>
      <div className="aio-section-title">Models ({filtered.length})</div>

      <div className="aio-model-search">
        <input
          className="aio-search-input"
          placeholder="Search models…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="aio-filter-pills">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`aio-pill${filter === f.key ? " active" : ""}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <select className="aio-select" value={sortBy} onChange={(e) => setSortBy(e.target.value as SortKey)}>
          <option value="name">Sort: Name</option>
          <option value="provider">Sort: Provider</option>
          <option value="context">Sort: Context</option>
          <option value="quality">Sort: Quality</option>
        </select>
        <button
          className={`aio-pill${grouped ? " active" : ""}`}
          onClick={() => setGrouped(!grouped)}
        >
          {grouped ? "Ungroup" : "Group by Provider"}
        </button>
      </div>

      <div className="aio-model-table-wrap">
        <table className="aio-model-table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Provider</th>
              <th>Commercial</th>
              <th>Context</th>
              <th>Vision</th>
              <th>Reasoning</th>
              <th>Tools</th>
              <th>JSON</th>
              <th>Embeddings</th>
              <th>Speed</th>
              <th>Quality</th>
            </tr>
          </thead>
          <tbody>
            {groups
              ? groups.map(([providerType, models]) => (
                  <Fragment key={providerType}>
                    <tr>
                      <td
                        colSpan={11}
                        style={{
                          fontWeight: 600,
                          padding: "8px 12px",
                          background: "rgba(124,115,255,0.06)",
                          fontSize: 13,
                          color: "var(--accent)",
                        }}
                      >
                        {providerType} ({models.length})
                      </td>
                    </tr>
                    {models.map(renderRow)}
                  </Fragment>
                ))
              : filtered.map(renderRow)}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <div className="aio-empty">
          <div className="aio-empty-icon">🔍</div>
          <div>No models match your search.</div>
        </div>
      )}
    </div>
  );
}

export default ModelsView;
