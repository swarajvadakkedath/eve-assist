import { useState, useRef, useCallback, useEffect } from "react";
import type { Message, ConversationState, ConversationActions } from "./types";
import ConversationTimeline from "./ConversationTimeline";
import ConversationEmptyState from "./ConversationEmptyState";
import ConversationLoadingState from "./ConversationLoadingState";
import ConversationErrorState from "./ConversationErrorState";
import Composer from "./Composer";
import type { TimelineEntry } from "./TimelineItem";
import { fetchApi } from "../../services/api";
import { getSessionStore, adaptBackendEvent, createCompletedEvent } from "../execution/session";
import { ExecutionInspector } from "../inspector";

export interface ConversationViewProps {
  sidebar?: React.ReactNode;
  state?: ConversationState;
  actions?: ConversationActions;
}

const defaultState: ConversationState = {
  activeId: null,
  messages: [],
  streaming: false,
  streamingContent: "",
  statusMessage: "",
  loading: false,
  error: null,
};

function ConversationView({
  state: externalState,
  actions: externalActions,
}: ConversationViewProps) {
  const internalConversationsRef = useRef<any[]>([]);
  const [internalState, setInternalState] = useState<ConversationState>(defaultState);

  const [customEntries, setCustomEntries] = useState<TimelineEntry[]>([]);
  const [, setSessionTick] = useState(0);
  const sessionStoreRef = useRef(getSessionStore());
  const activeSessionIdRef = useRef<string | null>(null);
  const currentRequestIdRef = useRef<string>("");
  const [inspectedSessionId, setInspectedSessionId] = useState<string | null>(null);

  const state = externalState || internalState;
  const setState = !externalState ? setInternalState : () => {};

  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetchApi("/chat/conversations");
      const data = await res.json();
      internalConversationsRef.current = data.conversations || [];
    } catch (err) {
      console.error("Failed to fetch conversations", err);
    }
  }, []);

  useEffect(() => {
    if (!externalState) {
      fetchConversations();
    }
    return sessionStoreRef.current.subscribe(() => {
      setSessionTick(t => t + 1);
      rebuildEntries();
    });
  }, [externalState, fetchConversations]);

  const createConversation = useCallback(async () => {
    try {
      const res = await fetchApi("/chat/conversation", { method: "POST" });
      const conv = await res.json();
      setState((prev) => ({ ...prev, activeId: conv.id, messages: [], error: null }));
      fetchConversations();
    } catch (err) {
      setState((prev) => ({ ...prev, error: "Failed to create conversation" }));
    }
  }, [fetchConversations, setState]);

  const rebuildEntries = useCallback(() => {
    const store = sessionStoreRef.current;
    if (!state.activeId) {
      setCustomEntries([]);
      return;
    }
    const sessions = store.getAllSessions(state.activeId);
    const entries: TimelineEntry[] = sessions.map(session => ({
      type: "session" as const,
      session,
    }));
    setCustomEntries(entries);
  }, [state.activeId]);

  const sendMessage = useCallback(async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || state.streaming) return;

    let convId = state.activeId;
    if (!convId) {
      try {
        const res = await fetchApi("/chat/conversation", { method: "POST" });
        const conv = await res.json();
        convId = conv.id;
        setState((prev) => ({ ...prev, activeId: conv.id }));
        fetchConversations();
      } catch (err) {
        setState((prev) => ({ ...prev, error: "Failed to create conversation" }));
        return;
      }
    }
    if (!convId) return;

    currentRequestIdRef.current = `req-${Date.now()}`;
    activeSessionIdRef.current = null;

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: convId,
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
      tokens_used: 0,
      attachments: [],
      metadata: {},
    };

    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      streaming: true,
      streamingContent: "",
      statusMessage: "Processing...",
      error: null,
    }));

    try {
      const res = await fetchApi("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: convId, content: trimmed }),
      });

      if (!res.ok) {
        const errData = await res.json();
        setState((prev) => ({
          ...prev,
          error: errData.error || "Request failed",
          streaming: false,
          statusMessage: "",
        }));
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        setState((prev) => ({
          ...prev,
          error: "No response stream",
          streaming: false,
        }));
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
              const adapted = adaptBackendEvent(
                event,
                activeSessionIdRef.current || `session-${Date.now()}`,
                convId!,
                currentRequestIdRef.current,
                trimmed,
              );
              if (adapted) {
                if (adapted.type === "ExecutionStarted" && !activeSessionIdRef.current) {
                  activeSessionIdRef.current = adapted.sessionId;
                }
                sessionStoreRef.current.applyEvent(adapted);
                rebuildEntries();
              }
              switch (event.type) {
                case "token":
                  fullContent += event.data.token;
                  setState((prev) => ({ ...prev, streamingContent: fullContent }));
                  break;
                case "done":
                  if (activeSessionIdRef.current) {
                    const session = sessionStoreRef.current.getSession(activeSessionIdRef.current);
                    if (session && session.status === "running") {
                      const storeDuration = Date.now() - new Date(session.startedAt).getTime();
                      const completedEvent = createCompletedEvent(
                        activeSessionIdRef.current,
                        session.steps.every(s => s.status === "completed" || s.status === "skipped"),
                        "Completed",
                        storeDuration,
                      );
                      sessionStoreRef.current.applyEvent(completedEvent);
                      rebuildEntries();
                    }
                  }
                  activeSessionIdRef.current = null;
                  setState((prev) => ({
                    ...prev,
                    messages: [
                      ...prev.messages,
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
                    ],
                    streamingContent: "",
                    streaming: false,
                    statusMessage: "",
                  }));
                  fetchConversations();
                  break;
                case "error":
                  if (activeSessionIdRef.current) {
                    sessionStoreRef.current.applyEvent({
                      type: "ExecutionFailed",
                      sessionId: activeSessionIdRef.current,
                      error: event.data.error || "Unknown error",
                    });
                    rebuildEntries();
                    activeSessionIdRef.current = null;
                  }
                  setState((prev) => ({
                    ...prev,
                    error: event.data.error,
                    streamingContent: "",
                    streaming: false,
                    statusMessage: "",
                  }));
                  break;
                case "status":
                  setState((prev) => ({ ...prev, statusMessage: event.data.message }));
                  break;
              }
            } catch {
              // skip malformed events
            }
          }
        }
      }
    } catch (err: any) {
      setState((prev) => ({
        ...prev,
        error: err.message || "Connection error",
        streaming: false,
        statusMessage: "",
      }));
    }
  }, [state.activeId, state.streaming, fetchConversations, setState]);

  const handleInspectSession = useCallback((sessionId: string) => {
    setInspectedSessionId(prev => prev === sessionId ? null : sessionId);
  }, []);

  const handleCloseInspector = useCallback(() => {
    setInspectedSessionId(null);
  }, []);

  const retryLast = useCallback(() => {
    const { messages } = state;
    if (messages.length === 0) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
    if (lastUserMsg) {
      setState((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
        error: null,
      }));
    }
  }, [state, setState]);

  const hasMessages = state.messages.length > 0 || state.streaming;

  return (
    <div className="pr-conv">
      {externalActions ? null : (
        <div className="pr-conv-header">
          <span className="pr-conv-status">
            {state.streaming
              ? "Streaming..."
              : state.statusMessage || "Ready"}
          </span>
        </div>
      )}

      <div className="pr-conv-main">
        <ConversationTimeline
          messages={state.messages}
          streaming={state.streaming}
          streamingContent={state.streamingContent}
          loading={state.loading}
          empty={!hasMessages && !state.loading}
          error={state.error}
          onRetry={retryLast}
          onNewConversation={createConversation}
          customEntries={customEntries}
          renderEmpty={() => (
            <ConversationEmptyState onNewConversation={createConversation} />
          )}
          renderLoading={() => <ConversationLoadingState />}
          renderError={(error) => (
            <ConversationErrorState error={error} onRetry={retryLast} />
          )}
          onInspectSession={handleInspectSession}
        />

        {inspectedSessionId && (
          <ExecutionInspector
            sessionId={inspectedSessionId}
            onClose={handleCloseInspector}
          />
        )}
      </div>

      <Composer
        onSend={sendMessage}
        disabled={state.streaming}
        placeholder={state.streaming ? "Waiting for response..." : "Message Eve..."}
      />
    </div>
  );
}

export default ConversationView;
