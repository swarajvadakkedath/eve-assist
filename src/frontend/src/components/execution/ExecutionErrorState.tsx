export interface ExecutionErrorStateProps {
  error: string;
  onRetry?: () => void;
}

function ExecutionErrorState({ error, onRetry }: ExecutionErrorStateProps) {
  return (
    <div className="pr-exec-error-state" role="alert">
      <span className="pr-exec-error-state-text">{error}</span>
      {onRetry && (
        <button className="pr-exec-error-state-retry" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export default ExecutionErrorState;
