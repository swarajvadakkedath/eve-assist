export interface TimestampProps {
  timestamp: string;
  tokens?: number;
}

function formatTime(iso: string): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

function Timestamp({ timestamp, tokens }: TimestampProps) {
  const time = formatTime(timestamp);
  if (!time && !tokens) return null;
  return (
    <span className="pr-msg-timestamp">
      {time}
      {tokens && tokens > 0 ? ` · ${tokens} tokens` : ""}
    </span>
  );
}

export default Timestamp;
