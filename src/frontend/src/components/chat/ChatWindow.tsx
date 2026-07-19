import { useState, useEffect, useRef, useCallback, KeyboardEvent } from "react";
import ConversationSidebar from "../sidebar/ConversationSidebar";
import MarkdownRenderer from "./MarkdownRenderer";

interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  tokens_used: number;
  attachments: any[];
  tool_calls?: any[];
  metadata: Record<string, any>;
}

export default function ChatWindow() {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<any[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, scrollToBottom]);

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    try {
      const res = await fetch("/api/v1/chat/conversations");
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error("Failed to fetch conversations", err);
    }
  };

  const fetchHistory = async (id: string) => {
    setLoading(true);
    setMessages([]);
    setError(null);
    try {
      const res = await fetch(`/api/v1/chat/history/${id}`);
      const data = await res.json();
      if (data.messages) {
        setMessages(data.messages);
      }
    } catch (err) {
      console.error("Failed to fetch history", err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const res = await fetch("/api/v1/chat/conversation", { method: "POST" });
      const conv = await res.json();
      setActiveId(conv.id);
      setMessages([]);
      setError(null);
      fetchConversations();
    } catch (err) {
      console.error("Failed to create conversation", err);
    }
  };

  const handleSelectConversation = (id: string) => {
    if (streaming) {
      cancelStream();
    }
    setActiveId(id);
    fetchHistory(id);
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await fetch(`/api/v1/chat/conversation/${id}`, { method: "DELETE" });
      if (activeId === id) {
        setActiveId(null);
        setMessages([]);
      }
      fetchConversations();
    } catch (err) {
      console.error("Failed to delete conversation", err);
    }
  };

  const handleRenameConversation = (id: string, title: string) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title } : c))
    );
  };

  const cancelStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setStreaming(false);
    setStatusMessage("");
  };

  const sendMessage = async () => {
    const content = input.trim();
    if (!content || streaming) return;
    setInput("");
    setError(null);

    let convId = activeId;
    if (!convId) {
      try {
        const res = await fetch("/api/v1/chat/conversation", { method: "POST" });
        const conv = await res.json();
        convId = conv.id;
        setActiveId(conv.id);
        fetchConversations();
      } catch (err) {
        setError("Failed to create conversation");
        return;
      }
    }

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: convId,
      role: "user",
      content,
      timestamp: new Date().toISOString(),
      tokens_used: 0,
      attachments: [],
      metadata: {},
    };
    setMessages((prev) => [...prev, userMessage]);
    setStreaming(true);
    setStreamingContent("");
    setStatusMessage("Processing...");

    try {
      const res = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: convId, content }),
      });

      if (!res.ok) {
        const errData = await res.json();
        setError(errData.error || "Request failed");
        setStreaming(false);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        setError("No response stream");
        setStreaming(false);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const event = JSON.parse(line.slice(6));
              switch (event.type) {
                case "token":
                  fullContent += event.data.token;
                  setStreamingContent(fullContent);
                  break;
                case "done":
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: event.data.message_id || `msg-${Date.now()}`,
                      conversation_id: convId!,
                      role: "assistant",
                      content: fullContent,
                      timestamp: new Date().toISOString(),
                      tokens_used: event.data.tokens_used || 0,
                      attachments: [],
                      metadata: {},
                    },
                  ]);
                  setStreamingContent("");
                  setStreaming(false);
                  setStatusMessage("");
                  fetchConversations();
                  break;
                case "error":
                  setError(event.data.error);
                  setStreamingContent("");
                  setStreaming(false);
                  setStatusMessage("");
                  break;
                case "status":
                  setStatusMessage(event.data.message);
                  break;
                case "tool_call":
                  break;
                case "tool_result":
                  break;
              }
            } catch {
              // skip malformed events
            }
          }
        }
      }
    } catch (err: any) {
      setError(err.message || "Connection error");
      setStreaming(false);
      setStatusMessage("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const retryLast = () => {
    if (messages.length === 0) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      setInput(lastUserMsg.content);
      setMessages((prev) => prev.slice(0, -2));
      setError(null);
    }
  };

  return (
    <div className="chat-layout">
      <ConversationSidebar
        activeId={activeId}
        onSelect={handleSelectConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
        onRename={handleRenameConversation}
      />
      <div className="chat-window">
        <div className="chat-header">
          <h1>Eve</h1>
          <div className="status-indicator">
            {streaming ? "Streaming..." : statusMessage || "Ready"}
          </div>
        </div>

        <div className="message-list">
          {loading && <div className="loading-skeleton">Loading messages...</div>}

          {!loading && messages.length === 0 && !streaming && (
            <div className="welcome">
              <h2>Welcome to Eve</h2>
              <p>Your intelligent AI operating system. Start a conversation to get started.</p>
              <div className="shortcut-hints">
                <span>Ctrl+K — Command Palette</span>
                <span>Ctrl+, — Settings</span>
                <span>Enter — Send</span>
                <span>Shift+Enter — New Line</span>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`message ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === "user" ? "U" : msg.role === "assistant" ? "E" : "S"}
              </div>
              <div className="message-content">
                <MarkdownRenderer content={msg.content} />
                <span className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                  {msg.tokens_used > 0 && ` · ${msg.tokens_used} tokens`}
                </span>
              </div>
            </div>
          ))}

          {streaming && streamingContent && (
            <div className="message assistant">
              <div className="message-avatar">E</div>
              <div className="message-content">
                <MarkdownRenderer content={streamingContent} streaming />
                <span className="typing-indicator" />
              </div>
            </div>
          )}

          {streaming && !streamingContent && (
            <div className="message assistant">
              <div className="message-avatar">E</div>
              <div className="message-content">
                <div className="typing-indicator" />
              </div>
            </div>
          )}

          {error && (
            <div className="message-error">
              <span>{error}</span>
              <button className="btn-retry" onClick={retryLast}>Retry</button>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="message-input-container">
          <textarea
            ref={inputRef}
            className="message-input"
            placeholder={streaming ? "Waiting for response..." : "Message Eve..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={streaming}
            rows={1}
          />
          <button
            className="send-button"
            onClick={sendMessage}
            disabled={!input.trim() || streaming}
          >
            {streaming ? (
              <span className="stop-btn" onClick={cancelStream}>Stop</span>
            ) : (
              "Send"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
