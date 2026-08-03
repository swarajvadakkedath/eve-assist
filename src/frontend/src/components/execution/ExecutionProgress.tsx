import type { ExecutionProgress as ProgressData } from "./types";

export interface ExecutionProgressProps {
  progress: ProgressData;
}

function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="pr-exec-progress-bar-track" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
      <div className="pr-exec-progress-bar-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

function renderProgressLabel(progress: ProgressData): string {
  switch (progress.type) {
    case "percentage":
      return `${Math.round(progress.value || 0)}%`;
    case "steps":
      return `Step ${progress.current || 0} of ${progress.max || 0}`;
    case "files":
      return `${progress.current || 0} / ${progress.max || 0} files`;
    case "tokens":
      return `${progress.current || 0} tokens`;
    case "bytes":
      const mb = ((progress.current || 0) / (1024 * 1024)).toFixed(1);
      const maxMb = progress.max ? ` / ${(progress.max / (1024 * 1024)).toFixed(1)} MB` : "";
      return `${mb} MB${maxMb}`;
    case "time":
      return progress.label || "";
    case "custom":
      return progress.label || "";
    default:
      return progress.label || "";
  }
}

function ExecutionProgress({ progress }: ExecutionProgressProps) {
  const label = renderProgressLabel(progress);

  if (progress.type === "indeterminate") {
    return (
      <div className="pr-exec-progress pr-exec-progress-indeterminate" role="progressbar" aria-label={progress.label || "In progress"}>
        <div className="pr-exec-progress-bar-track">
          <div className="pr-exec-progress-bar-fill" />
        </div>
      </div>
    );
  }

  if (progress.type === "percentage" || progress.type === "steps" || progress.type === "files" || progress.type === "bytes") {
    const value = progress.value ?? progress.current ?? 0;
    const max = progress.max ?? 100;
    return (
      <div className="pr-exec-progress" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max} aria-label={label}>
        <ProgressBar value={value} max={max} />
        {label && <span className="pr-exec-progress-label">{label}</span>}
      </div>
    );
  }

  return (
    <div className="pr-exec-progress">
      {label && <span className="pr-exec-progress-label">{label}</span>}
    </div>
  );
}

export default ExecutionProgress;
