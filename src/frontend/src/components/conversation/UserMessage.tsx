import type { Message } from "./types";
import MessageAvatar from "./MessageAvatar";
import Timestamp from "./Timestamp";

export interface UserMessageProps {
  message: Message;
}

function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="pr-msg pr-msg-user">
      <MessageAvatar role="user" />
      <div className="pr-msg-content">
        <div className="pr-msg-body">{message.content}</div>
        <Timestamp timestamp={message.timestamp} />
      </div>
    </div>
  );
}

export default UserMessage;
