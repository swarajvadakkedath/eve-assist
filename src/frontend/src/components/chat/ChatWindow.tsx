import { useState, useEffect, useRef, useCallback, KeyboardEvent } from "react";
import { fetchApi } from "../../services/api";
import ConversationSidebar from "../sidebar/ConversationSidebar";
import ConversationHeader from "./ConversationHeader";
import MarkdownRenderer from "./MarkdownRenderer";
import type { RoutingPolicy } from "../providers/types";

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
  routing_trace?: {
    selected_provider_id?: string;
    selected_model_id?: string;
    fallback_reason?: string;
    fallback_from?: string;
    attempted_providers?: string[];
    total_cost?: number;
    selected_cost?: number;
  };
  error_type?: string;
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
  const [currentProviderId, setCurrentProviderId] = useState<string>("");
  const [currentModelId, setCurrentModelId] = useState<string>("");
  const [currentRoutingPolicy, setCurrentRoutingPolicy] = useState<RoutingPolicy>("auto");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

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
      const res = await fetchApi("/chat/conversations");
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
      const res = await fetchApi(`/chat/history/${id}`);
      const data = await res.json();
      if (data.messages) {
        setMessages(data.messages);
      }
      const convRes = await fetchApi(`/chat/conversation/${id}`);
      const conv = await convRes.json();
      if (conv.provider_id) setCurrentProviderId(conv.provider_id);
      if (conv.model_id) setCurrentModelId(conv.model_id);
      if (conv.routing_policy) setCurrentRoutingPolicy(conv.routing_policy as RoutingPolicy);
      else setCurrentRoutingPolicy("auto");
    } catch (err) {
      console.error("Failed to fetch history", err);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = async () => {
    try {
      const res = await fetchApi("/chat/conversation", { method: "POST" });
      const conv = await res.json();
      setActiveId(conv.id);
      setMessages([]);
      setError(null);
      if (conv.provider_id) setCurrentProviderId(conv.provider_id);
      if (conv.model_id) setCurrentModelId(conv.model_id);
      if (conv.routing_policy) setCurrentRoutingPolicy(conv.routing_policy as RoutingPolicy);
      else setCurrentRoutingPolicy("auto");
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
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await fetchApi(`/chat/conversation/${id}`, { method: "DELETE" });
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
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
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
      const res = await fetchApi("/chat/conversation", { method: "POST" });
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
      conversation_id: convId || "",
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

    const abort = new AbortController();
    abortRef.current = abort;

    try {
      const res = await fetchApi("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: convId || "",
          content,
          provider_id: currentProviderId || undefined,
          model_id: currentModelId || undefined,
          routing_policy: currentRoutingPolicy || undefined,
        }),
        signal: abort.signal,
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
                      metadata: event.data.metadata || {},
                      routing_trace: event.data.routing_trace || undefined,
                      error_type: event.data.error_type || undefined,
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
      if (err.name === "AbortError") return;
      setError(err.message || "Connection error");
      setStreaming(false);
      setStatusMessage("");
    } finally {
      if (abortRef.current === abort) abortRef.current = null;
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
        <ConversationHeader
          currentProviderId={currentProviderId}
          currentModelId={currentModelId}
          currentRoutingPolicy={currentRoutingPolicy}
          onProviderChange={(pid) => {
            setCurrentProviderId(pid);
            setCurrentModelId("");
            // Persist to conversation
            if (activeId) {
              fetchApi(`/chat/conversation/${activeId}`, {
                method: "PUT",
                body: JSON.stringify({ provider_id: pid, model_id: "" }),
              }).catch((err) => console.error("Failed to save provider", err));
            }
          }}
          onModelChange={(mid) => {
            setCurrentModelId(mid);
            // Persist to conversation
            if (activeId) {
              fetchApi(`/chat/conversation/${activeId}`, {
                method: "PUT",
                body: JSON.stringify({ model_id: mid }),
              }).catch((err) => console.error("Failed to save model", err));
            }
          }}
          onRoutingPolicyChange={(policy) => {
            setCurrentRoutingPolicy(policy);
            // Persist to conversation
            if (activeId) {
              fetchApi(`/chat/conversation/${activeId}`, {
                method: "PUT",
                body: JSON.stringify({ routing_policy: policy }),
              }).catch((err) => console.error("Failed to save routing policy", err));
            }
          }}
        />
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
                {msg.role === "assistant" && msg.routing_trace && (
                  <div className={`message-fallback-indicator ${msg.routing_trace.selected_cost && msg.routing_trace.selected_cost > 0 ? "paid" : ""}`}>
                    {msg.routing_trace.fallback_reason ? (
                      <span>Used {msg.routing_trace.selected_model_id || msg.routing_trace.selected_provider_id} (fallback: {msg.routing_trace.fallback_reason})</span>
                    ) : (
                      <span>via {msg.routing_trace.selected_model_id || msg.routing_trace.selected_provider_id}</span>
                    )}
                  </div>
                )}
                {msg.role === "assistant" && msg.error_type && (
                  <div className="message-fallback-indicator paid">
                    {msg.error_type === "strict_failure" ? "Strict mode: no fallback — see error" : msg.error_type}
                  </div>
                )}
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
            className={streaming ? "send-button stop" : "send-button"}
            onClick={streaming ? cancelStream : sendMessage}
            disabled={!input.trim() && !streaming}
          >
            {streaming ? "Stop" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
