import type { CommandErrorStateProps } from "./types";

function CommandErrorState({ error, onRetry }: CommandErrorStateProps) {
  return (
    <div className="pr-cmd-error" role="alert">
      <span className="pr-cmd-error-icon" aria-hidden="true">{'\u26A0'}</span>
      <span className="pr-cmd-error-text">{error}</span>
      {onRetry && (
        <button className="pr-cmd-error-retry" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export default CommandErrorState;
