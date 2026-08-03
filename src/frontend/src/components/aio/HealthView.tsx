import { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import { useAioStore } from "./AioStore";
import { STATE_COLORS, PROVIDER_ICONS } from "./aioTypes";

const PROVIDER_COLORS = [
  "#7c73ff", "#22c55e", "#f59e0b", "#ef4444",
  "#f97316", "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
];

interface ChartPoint {
  time: number;
  label: string;
  [key: string]: string | number;
}

function buildChartPoints(
  history: Record<string, { timestamp: number; latency_ms: number; health_score?: number; success_rate?: number }[]>,
  metricKey: "latency_ms" | "health_score" | "success_rate",
): ChartPoint[] {
  const allTimestamps = new Set<number>();
  for (const snapshots of Object.values(history)) {
    for (const s of snapshots) allTimestamps.add(s.timestamp);
  }
  const sortedTs = Array.from(allTimestamps).sort((a, b) => a - b);
  if (sortedTs.length === 0) return [];
  const firstTs = sortedTs[0];

  return sortedTs.map((ts) => {
    const point: ChartPoint = { time: ts - firstTs, label: formatTime(ts - firstTs) };
    for (const [pid, snapshots] of Object.entries(history)) {
      const match = snapshots.find((s) => s.timestamp === ts);
      point[pid] = match ? (match[metricKey] ?? 0) : 0;
    }
    return point;
  });
}

function formatTime(offsetMs: number): string {
  const secs = Math.floor(offsetMs / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const rem = secs % 60;
  return `${mins}m${rem > 0 ? `${rem}s` : ""}`;
}

function HealthView() {
  const { providers, health, healthHistory } = useAioStore();

  const latencyData = useMemo(
    () => buildChartPoints(healthHistory, "latency_ms"),
    [healthHistory],
  );
  const scoreData = useMemo(
    () => buildChartPoints(healthHistory, "health_score"),
    [healthHistory],
  );
  const successData = useMemo(
    () => buildChartPoints(healthHistory, "success_rate"),
    [healthHistory],
  );

  const providerIds = useMemo(() => {
    return Object.keys(healthHistory);
  }, [healthHistory]);

  const barData = useMemo(
    () =>
      providers.map((p) => ({
        name: `${PROVIDER_ICONS[p.type] ?? ""} ${p.name}`,
        health_score: health[p.id]?.health_score ?? 0,
        state: health[p.id]?.state ?? "unknown",
      })),
    [providers, health],
  );

  const hasData = Object.keys(healthHistory).length > 0;

  function renderAreaChart(
    title: string,
    data: ChartPoint[],
    _metricKey: string,
    unit: string,
  ) {
    return (
      <div className="aio-chart-container">
        <div className="aio-chart-title">{title}</div>
        {!hasData ? (
          <div style={{ padding: 24, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
            No history data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
                axisLine={false}
                tickLine={false}
                width={40}
                unit={unit}
              />
              <Tooltip
                contentStyle={{
                  background: "rgba(26,26,46,0.95)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              {providerIds.map((pid, i) => {
                const provider = providers.find((p) => p.id === pid);
                return (
                  <Area
                    key={pid}
                    type="monotone"
                    dataKey={pid}
                    name={provider?.name ?? pid}
                    stroke={PROVIDER_COLORS[i % PROVIDER_COLORS.length]}
                    fill={PROVIDER_COLORS[i % PROVIDER_COLORS.length]}
                    fillOpacity={0.1}
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                );
              })}
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="aio-section-title">Health Center</div>

      <div className="aio-charts-grid">
        {renderAreaChart("Latency (ms)", latencyData, "latency_ms", "ms")}
        {renderAreaChart("Health Score", scoreData, "health_score", "")}
        {renderAreaChart("Success Rate", successData, "success_rate", "%")}

        <div className="aio-chart-container">
          <div className="aio-chart-title">Provider Availability</div>
          {!hasData ? (
            <div style={{ padding: 24, textAlign: "center", color: "var(--text-secondary)", fontSize: 13 }}>
              No history data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
                  axisLine={false}
                  tickLine={false}
                  width={40}
                  domain={[0, 100]}
                />
                <Tooltip
                  contentStyle={{
                    background: "rgba(26,26,46,0.95)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar
                  dataKey="health_score"
                  radius={[4, 4, 0, 0]}
                  isAnimationActive={false}
                >
                  {barData.map((entry, i) => (
                    <Cell
                      key={i}
                      fill={STATE_COLORS[entry.state] ?? PROVIDER_COLORS[i % PROVIDER_COLORS.length]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}

export default HealthView;
