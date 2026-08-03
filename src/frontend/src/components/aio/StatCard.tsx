
interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}

function StatCard({ label, value, sub, color }: StatCardProps) {
  return (
    <div className="aio-stat-card">
      <div className="aio-stat-label">{label}</div>
      <div
        className="aio-stat-value"
        style={color ? { color } : undefined}
      >
        {value}
      </div>
      {sub && <div className="aio-stat-sub">{sub}</div>}
    </div>
  );
}

export default StatCard;
