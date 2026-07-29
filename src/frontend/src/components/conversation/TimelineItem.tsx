import type { Message } from "./types";
import UserMessageComponent from "./UserMessage";
import AssistantMessageComponent from "./AssistantMessage";
import SystemMessageComponent from "./SystemMessage";
import ExecutionCard from "../execution/ExecutionCard";
import ExecutionSessionCard from "../execution/session/ExecutionSessionCard";
import type { ExecutionState } from "../execution/types";
import type { ExecutionSession } from "../execution/session/types";

export type TimelineEntry =
  | { type: "message"; message: Message }
  | { type: "streaming"; message: Message; streamingContent: string }
  | { type: "typing" }
  | { type: "divider"; label?: string }
  | { type: "execution"; execution: ExecutionState }
  | { type: "session"; session: ExecutionSession }
  | { type: "error"; message: string; onRetry?: () => void }
  | { type: "attachment"; label: string; url?: string }
  | { type: "memory"; content: string }
  | { type: "result"; label: string; success: boolean }
  | { type: "system"; content: string };

export interface TimelineItemProps {
  entry: TimelineEntry;
  onInspectSession?: (sessionId: string) => void;
}

function TimelineItem({ entry, onInspectSession }: TimelineItemProps) {
  switch (entry.type) {
    case "message": {
      const { message } = entry;
      switch (message.role) {
        case "user":
          return <UserMessageComponent message={message} />;
        case "assistant":
          return <AssistantMessageComponent message={message} />;
        case "system":
          return <SystemMessageComponent message={message} />;
        default:
          return null;
      }
    }
    case "streaming":
      return (
        <AssistantMessageComponent
          message={entry.message}
          streaming
          streamingContent={entry.streamingContent}
        />
      );
    case "typing":
      return (
        <div className="pr-msg pr-msg-assistant">
          <div className="pr-msg-avatar pr-msg-avatar-assistant" aria-hidden="true">E</div>
          <div className="pr-msg-content">
            <div className="pr-typing" role="status" aria-label="Assistant is typing">
              <span className="pr-typing-dot" />
              <span className="pr-typing-dot" />
              <span className="pr-typing-dot" />
            </div>
          </div>
        </div>
      );
    case "divider":
      return (
        <div className="pr-timeline-divider" role="separator" aria-orientation="horizontal">
          {entry.label && <span className="pr-timeline-divider-label">{entry.label}</span>}
        </div>
      );
    case "execution":
      return (
        <div className="pr-timeline-execution">
          <ExecutionCard execution={entry.execution} />
        </div>
      );
    case "session":
      return (
        <div className="pr-timeline-session">
          <ExecutionSessionCard session={entry.session} onInspect={onInspectSession} />
        </div>
      );
    case "error":
      return (
        <div className="pr-conv-error" role="alert">
          <span className="pr-conv-error-icon" aria-hidden="true">&#x26A0;</span>
          <span className="pr-conv-error-text">{entry.message}</span>
          {entry.onRetry && (
            <button className="pr-conv-error-retry" onClick={entry.onRetry}>Retry</button>
          )}
        </div>
      );
    case "attachment":
      return (
        <div className="pr-timeline-attachment">
          <span className="pr-timeline-attachment-icon" aria-hidden="true">&#x1F4CE;</span>
          <span>{entry.label}</span>
        </div>
      );
    case "memory":
      return (
        <div className="pr-timeline-memory">
          <span className="pr-timeline-memory-icon" aria-hidden="true">&#x1F9E0;</span>
          <span>{entry.content}</span>
        </div>
      );
    case "result":
      return (
        <div className={`pr-timeline-result ${entry.success ? "pr-timeline-result-success" : "pr-timeline-result-failed"}`}>
          <span className="pr-timeline-result-icon" aria-hidden="true">{entry.success ? "\u2713" : "\u2716"}</span>
          <span>{entry.label}</span>
        </div>
      );
    case "system":
      return (
        <div className="pr-timeline-system">{entry.content}</div>
      );
    default:
      return null;
  }
}

export default TimelineItem;
