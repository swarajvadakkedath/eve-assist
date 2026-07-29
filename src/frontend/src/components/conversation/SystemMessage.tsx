import type { Message } from "./types";
import Timestamp from "./Timestamp";

export interface SystemMessageProps {
  message: Message;
}

function SystemMessage({ message }: SystemMessageProps) {
  return (
    <div className="pr-msg pr-msg-system">
      <div className="pr-msg-content">
        <div className="pr-msg-body">{message.content}</div>
        <Timestamp timestamp={message.timestamp} />
      </div>
    </div>
  );
}

export default SystemMessage;
