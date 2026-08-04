export interface ConversationErrorStateProps {
  error: string;
  errorData?: {
    category?: string;
    likely_cause?: string;
    recovery_suggestions?: string[];
    provider?: string;
    model?: string;
  };
  onRetry?: () => void;
  onViewRecovery?: () => void;
}

function ConversationErrorState({ error, errorData, onRetry, onViewRecovery }: ConversationErrorStateProps) {
  return (
    <div className="pr-conv-error" role="alert">
      <div className="pr-conv-error-header">
        <span className="pr-conv-error-icon" aria-hidden="true">&#x26A0;</span>
        <span className="pr-conv-error-text">{error}</span>
      </div>
      {errorData?.likely_cause && (
        <div className="pr-conv-error-cause">{errorData.likely_cause}</div>
      )}
      {errorData?.recovery_suggestions && errorData.recovery_suggestions.length > 0 && (
        <div className="pr-conv-error-suggestions">
          {errorData.recovery_suggestions.map((s, i) => (
            <span key={i} className="pr-conv-error-suggestion">✓ {s}</span>
          ))}
        </div>
      )}
      <div className="pr-conv-error-meta">
        {errorData?.provider && <span className="pr-conv-error-pill">{errorData.provider}</span>}
        {errorData?.model && <span className="pr-conv-error-pill">{errorData.model}</span>}
        {errorData?.category && <span className="pr-conv-error-pill">{errorData.category}</span>}
      </div>
      <div className="pr-conv-error-actions">
        {onRetry && (
          <button className="pr-conv-error-retry" onClick={onRetry}>
            Retry
          </button>
        )}
        {onViewRecovery && (
          <button className="pr-conv-error-recovery" onClick={onViewRecovery}>
            View in Recovery Center
          </button>
        )}
      </div>
    </div>
  );
}

export default ConversationErrorState;
