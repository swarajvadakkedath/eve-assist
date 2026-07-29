export interface RecoveryCardProps {
  error: string;
  onRetry: () => void;
  onRetryAll?: () => void;
  onContinue?: () => void;
  onSkip?: () => void;
  onCancel?: () => void;
}

function RecoveryCard({ error, onRetry, onRetryAll, onContinue, onSkip, onCancel }: RecoveryCardProps) {
  return (
    <div className="pr-exec-recovery" role="alert" aria-label="Recovery available">
      <div className="pr-exec-recovery-icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12a9 9 0 11-9-9" />
          <path d="M21 3v6h-6" />
        </svg>
      </div>
      <div className="pr-exec-recovery-body">
        <div className="pr-exec-recovery-title">Step Failed</div>
        <div className="pr-exec-recovery-error">{error}</div>
        <div className="pr-exec-recovery-actions">
          <button className="pr-exec-recovery-btn pr-exec-recovery-retry" onClick={onRetry}>
            Retry Step
          </button>
          {onRetryAll && (
            <button className="pr-exec-recovery-btn pr-exec-recovery-retry-all" onClick={onRetryAll}>
              Retry All
            </button>
          )}
          {onContinue && (
            <button className="pr-exec-recovery-btn pr-exec-recovery-continue" onClick={onContinue}>
              Continue
            </button>
          )}
          {onSkip && (
            <button className="pr-exec-recovery-btn pr-exec-recovery-skip" onClick={onSkip}>
              Skip
            </button>
          )}
          {onCancel && (
            <button className="pr-exec-recovery-btn pr-exec-recovery-cancel" onClick={onCancel}>
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default RecoveryCard;
