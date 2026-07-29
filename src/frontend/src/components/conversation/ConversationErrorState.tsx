export interface ConversationErrorStateProps {
  error: string;
  onRetry?: () => void;
}

function ConversationErrorState({ error, onRetry }: ConversationErrorStateProps) {
  return (
    <div className="pr-conv-error" role="alert">
      <span className="pr-conv-error-icon" aria-hidden="true">&#x26A0;</span>
      <span className="pr-conv-error-text">{error}</span>
      {onRetry && (
        <button className="pr-conv-error-retry" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export default ConversationErrorState;
