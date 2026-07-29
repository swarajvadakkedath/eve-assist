import type { CommandLoadingStateProps } from "./types";

function CommandLoadingState({ message = "Searching..." }: CommandLoadingStateProps) {
  return (
    <div className="pr-cmd-loading" role="status" aria-label={message}>
      <div className="pr-cmd-loading-spinner" aria-hidden="true" />
      <span className="pr-cmd-loading-text">{message}</span>
    </div>
  );
}

export default CommandLoadingState;
