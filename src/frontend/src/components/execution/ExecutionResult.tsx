import type { ExecutionResultData } from "./types";
import ExecutionDuration from "./ExecutionDuration";

export interface ExecutionResultProps {
  result: ExecutionResultData;
}

function ExecutionResult({ result }: ExecutionResultProps) {
  const isSuccess = result.success;

  return (
    <div className={`pr-exec-result ${isSuccess ? "pr-exec-result-success" : "pr-exec-result-failed"}`}>
      <div className="pr-exec-result-header">
        {isSuccess ? (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <circle cx="10" cy="10" r="9" stroke="var(--execution-completed)" strokeWidth="2" />
            <path d="M6 10l3 3 5-5" stroke="var(--execution-completed)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <circle cx="10" cy="10" r="9" stroke="var(--execution-failed)" strokeWidth="2" />
            <path d="M7 7l6 6M13 7l-6 6" stroke="var(--execution-failed)" strokeWidth="2" strokeLinecap="round" />
          </svg>
        )}
        <span className="pr-exec-result-label">
          {isSuccess ? "Completed" : "Failed"}
        </span>
        <ExecutionDuration durationMs={result.durationMs} />
      </div>

      <div className="pr-exec-result-summary">{result.summary}</div>

      {result.output && (
        <pre className="pr-exec-result-output">{result.output}</pre>
      )}

      {result.warnings && result.warnings.length > 0 && (
        <div className="pr-exec-result-warnings">
          {result.warnings.map((w, i) => (
            <div key={i} className="pr-exec-result-warning">&#x26A0; {w}</div>
          ))}
        </div>
      )}

      {result.errors && result.errors.length > 0 && (
        <div className="pr-exec-result-errors">
          {result.errors.map((e, i) => (
            <div key={i} className="pr-exec-result-error">&#x2716; {e}</div>
          ))}
        </div>
      )}

      <div className="pr-exec-result-stats">
        <span>{result.completedCount} / {result.taskCount} tasks completed</span>
        {result.failedCount > 0 && <span className="pr-exec-result-stat-failed">{result.failedCount} failed</span>}
        {result.toolsExecuted && result.toolsExecuted.length > 0 && (
          <span>Tools: {result.toolsExecuted.join(", ")}</span>
        )}
      </div>
    </div>
  );
}

export default ExecutionResult;
