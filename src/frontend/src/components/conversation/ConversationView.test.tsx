import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ConversationView from "./ConversationView";
import type { ConversationState, ConversationActions } from "./types";

describe("ConversationView", () => {
  it("renders empty state with no messages", () => {
    render(<ConversationView />);
    expect(screen.getByText("Welcome to Eve")).toBeInTheDocument();
  });

  it("renders composer", () => {
    render(<ConversationView />);
    expect(screen.getByRole("textbox", { name: "Message input" })).toBeInTheDocument();
  });

  it("renders messages from external state", () => {
    const state: ConversationState = {
      activeId: "c1",
      messages: [
        {
          id: "1", conversation_id: "c1", role: "user",
          content: "Test message", timestamp: new Date().toISOString(),
          tokens_used: 0, attachments: [], metadata: {},
        },
      ],
      streaming: false,
      streamingContent: "",
      statusMessage: "",
      loading: false,
      error: null,
    };
    const actions: ConversationActions = {
      sendMessage: async () => {},
      cancelStream: () => {},
      retryLast: () => {},
      createConversation: async () => {},
      selectConversation: async () => {},
      deleteConversation: async () => {},
      renameConversation: () => {},
    };
    render(<ConversationView state={state} actions={actions} />);
    expect(screen.getByText("Test message")).toBeInTheDocument();
  });

  it("renders streaming indicator when streaming", () => {
    const state: ConversationState = {
      activeId: "c1",
      messages: [],
      streaming: true,
      streamingContent: "",
      statusMessage: "Processing...",
      loading: false,
      error: null,
    };
    render(<ConversationView state={state} />);
    expect(screen.getByText("Streaming...")).toBeInTheDocument();
  });

  it("renders error state", () => {
    const state: ConversationState = {
      activeId: "c1",
      messages: [],
      streaming: false,
      streamingContent: "",
      statusMessage: "",
      loading: false,
      error: "Network error",
    };
    render(<ConversationView state={state} />);
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("renders loading state", () => {
    const state: ConversationState = {
      activeId: "c1",
      messages: [],
      streaming: false,
      streamingContent: "",
      statusMessage: "",
      loading: true,
      error: null,
    };
    const { container } = render(<ConversationView state={state} />);
    expect(container.querySelector(".pr-conv-loading")).toBeInTheDocument();
  });
});
