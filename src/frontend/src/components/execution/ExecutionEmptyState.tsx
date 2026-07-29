export interface ExecutionEmptyStateProps {
  message?: string;
}

function ExecutionEmptyState({ message = "No executions yet" }: ExecutionEmptyStateProps) {
  return (
    <div className="pr-exec-empty" role="status">
      <div className="pr-exec-empty-icon" aria-hidden="true">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      </div>
      <span className="pr-exec-empty-text">{message}</span>
    </div>
  );
}

export default ExecutionEmptyState;
