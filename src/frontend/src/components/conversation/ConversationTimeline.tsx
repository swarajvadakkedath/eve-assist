import { useEffect, useRef } from "react";
import type { Message } from "./types";
import TimelineItem from "./TimelineItem";
import type { TimelineEntry } from "./TimelineItem";

export interface ConversationTimelineProps {
  messages: Message[];
  streaming?: boolean;
  streamingContent?: string;
  loading?: boolean;
  empty?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onNewConversation?: () => void;
  renderEmpty?: () => React.ReactNode;
  renderLoading?: () => React.ReactNode;
  renderError?: (error: string) => React.ReactNode;
  customEntries?: TimelineEntry[];
  onInspectSession?: (sessionId: string) => void;
}

function buildEntries(
  messages: Message[],
  streaming: boolean,
  streamingContent: string,
  customEntries: TimelineEntry[] = [],
): TimelineEntry[] {
  const entries: TimelineEntry[] = [...customEntries];

  for (let i = 0; i < messages.length; i++) {
    const msg = messages[i];
    entries.push({ type: "message", message: msg });
  }

  if (streaming) {
    const lastMsg = messages[messages.length - 1];
    if (lastMsg && lastMsg.role === "assistant") {
      entries[entries.length - 1] = {
        type: "streaming",
        message: lastMsg,
        streamingContent,
      };
    } else {
      entries.push({
        type: "streaming",
        message: {
          id: "streaming",
          conversation_id: "",
          role: "assistant",
          content: "",
          timestamp: new Date().toISOString(),
          tokens_used: 0,
          attachments: [],
          metadata: {},
        },
        streamingContent,
      });
    }
  }

  return entries;
}

function ConversationTimeline({
  messages,
  streaming = false,
  streamingContent = "",
  loading = false,
  empty = false,
  error = null,
  onRetry,
  onNewConversation,
  renderEmpty,
  renderLoading,
  renderError,
  customEntries,
  onInspectSession,
}: ConversationTimelineProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  if (loading) {
    return <div className="pr-timeline">{renderLoading ? renderLoading() : null}</div>;
  }

  if (error) {
    return <div className="pr-timeline">{renderError ? renderError(error) : null}</div>;
  }

  const entries = buildEntries(messages, streaming, streamingContent, customEntries);

  if (!loading && entries.length === 0) {
    return <div className="pr-timeline">{renderEmpty ? renderEmpty() : null}</div>;
  }

  return (
    <div className="pr-timeline" role="log" aria-label="Conversation messages" aria-live="polite">
      <div className="pr-timeline-inner">
        {entries.map((entry, i) => (
          <TimelineItem key={i} entry={entry} onInspectSession={onInspectSession} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

export default ConversationTimeline;
