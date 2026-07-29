import type { Message } from "./types";
import MessageAvatar from "./MessageAvatar";
import Timestamp from "./Timestamp";
import MarkdownRenderer from "./MarkdownRenderer";
import TypingIndicator from "./TypingIndicator";

export interface AssistantMessageProps {
  message: Message;
  streaming?: boolean;
  streamingContent?: string;
}

function AssistantMessage({ message, streaming, streamingContent }: AssistantMessageProps) {
  const content = streaming ? streamingContent || "" : message.content;
  const hasContent = content.length > 0;

  return (
    <div className="pr-msg pr-msg-assistant">
      <MessageAvatar role="assistant" />
      <div className="pr-msg-content">
        {streaming && <div className="pr-msg-header">Eve</div>}
        {hasContent ? (
          <MarkdownRenderer content={content} streaming={streaming} />
        ) : (
          streaming && <TypingIndicator />
        )}
        {!streaming && (
          <Timestamp timestamp={message.timestamp} tokens={message.tokens_used} />
        )}
      </div>
    </div>
  );
}

export default AssistantMessage;
