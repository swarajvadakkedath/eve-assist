import { useState, useEffect } from "react";

export interface ExecutionDurationProps {
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  running?: boolean;
}

function formatDuration(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  if (totalSec < 60) return `${totalSec}s`;
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  if (min < 60) return `${min}m ${sec}s`;
  const hr = Math.floor(min / 60);
  const remainMin = min % 60;
  return `${hr}h ${remainMin}m`;
}

function getElapsed(startedAt?: string): number {
  if (!startedAt) return 0;
  return Date.now() - new Date(startedAt).getTime();
}

function ExecutionDuration({ startedAt, completedAt, durationMs, running }: ExecutionDurationProps) {
  const [, setNow] = useState(Date.now());

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [running]);

  if (durationMs !== undefined) {
    return <span className="pr-exec-duration">{formatDuration(durationMs)}</span>;
  }

  if (completedAt && startedAt) {
    const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
    return <span className="pr-exec-duration">{formatDuration(ms)}</span>;
  }

  if (running && startedAt) {
    return <span className="pr-exec-duration">{formatDuration(getElapsed(startedAt))}</span>;
  }

  return null;
}

export default ExecutionDuration;
