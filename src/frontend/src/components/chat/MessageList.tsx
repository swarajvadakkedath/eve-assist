interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

interface MessageListProps {
  messages: Message[];
  loading: boolean;
}

export default function MessageList({ messages, loading }: MessageListProps) {
  if (messages.length === 0 && !loading) {
    return (
      <div className="message-list empty">
        <div className="welcome">
          <h2>Hello, I'm Eve</h2>
          <p>Your AI operating system assistant. How can I help you today?</p>
        </div>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((msg) => (
        <div key={msg.id} className={`message ${msg.role}`}>
          <div className="message-avatar">
            {msg.role === "assistant" ? "E" : "U"}
          </div>
          <div className="message-content">
            <p>{msg.content}</p>
            <span className="message-time">
              {new Date(msg.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      ))}
      {loading && (
        <div className="message assistant loading">
          <div className="message-avatar">E</div>
          <div className="message-content">
            <span className="typing-indicator">Thinking...</span>
          </div>
        </div>
      )}
    </div>
  );
}
