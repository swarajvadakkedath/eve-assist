import type { ExecutionNodeStatus } from "./types";
import ExecutionBadge from "./ExecutionBadge";
import ExecutionDuration from "./ExecutionDuration";
import type { ExecutionResultData } from "./types";

export interface ExecutionSummaryProps {
  objective: string;
  status: ExecutionNodeStatus;
  durationMs?: number;
  result?: ExecutionResultData;
}

function ExecutionSummary({ objective, status, durationMs, result }: ExecutionSummaryProps) {
  const successCount = result?.completedCount ?? 0;
  const totalCount = result?.taskCount ?? 0;

  return (
    <div className="pr-exec-summary">
      <div className="pr-exec-summary-left">
        <span className="pr-exec-summary-objective">{objective}</span>
        <span className="pr-exec-summary-tasks">{successCount}/{totalCount} steps</span>
      </div>
      <div className="pr-exec-summary-right">
        <ExecutionBadge status={status} compact />
        {durationMs !== undefined && <ExecutionDuration durationMs={durationMs} />}
      </div>
    </div>
  );
}

export default ExecutionSummary;
