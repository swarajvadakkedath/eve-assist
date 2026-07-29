import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AssistantMessage from "./AssistantMessage";
import type { Message } from "./types";

const baseMessage: Message = {
  id: "1",
  conversation_id: "conv-1",
  role: "assistant",
  content: "Hello! How can I help?",
  timestamp: "2024-01-15T10:30:00Z",
  tokens_used: 42,
  attachments: [],
  metadata: {},
};

describe("AssistantMessage", () => {
  it("renders assistant content", () => {
    render(<AssistantMessage message={baseMessage} />);
    expect(screen.getByText("Hello! How can I help?")).toBeInTheDocument();
  });

  it("renders assistant avatar", () => {
    render(<AssistantMessage message={baseMessage} />);
    expect(screen.getByText("E")).toBeInTheDocument();
  });

  it("renders timestamp with tokens", () => {
    render(<AssistantMessage message={baseMessage} />);
    expect(screen.getByText(/42 tokens/)).toBeInTheDocument();
  });

  it("renders streaming content when streaming", () => {
    render(
      <AssistantMessage
        message={baseMessage}
        streaming
        streamingContent="Partial response"
      />,
    );
    expect(screen.getByText("Partial response")).toBeInTheDocument();
  });

  it("shows typing indicator when streaming without content", () => {
    const { container } = render(
      <AssistantMessage message={baseMessage} streaming streamingContent="" />,
    );
    expect(container.querySelector(".pr-typing")).toBeInTheDocument();
  });

  it("applies assistant class", () => {
    const { container } = render(<AssistantMessage message={baseMessage} />);
    expect(container.firstChild).toHaveClass("pr-msg-assistant");
  });
});
