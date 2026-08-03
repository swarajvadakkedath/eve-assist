import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ConversationTimeline from "./ConversationTimeline";
import type { Message } from "./types";

const messages: Message[] = [
  {
    id: "1", conversation_id: "c1", role: "user",
    content: "Hello", timestamp: "2024-01-15T10:30:00Z",
    tokens_used: 0, attachments: [], metadata: {},
  },
  {
    id: "2", conversation_id: "c1", role: "assistant",
    content: "Hi there!", timestamp: "2024-01-15T10:30:01Z",
    tokens_used: 5, attachments: [], metadata: {},
  },
];

describe("ConversationTimeline", () => {
  it("renders messages", () => {
    render(<ConversationTimeline messages={messages} />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(screen.getByText("Hi there!")).toBeInTheDocument();
  });

  it("renders streaming content", () => {
    render(
      <ConversationTimeline
        messages={[messages[0]]}
        streaming
        streamingContent="Partial..."
      />,
    );
    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(screen.getByText("Partial...")).toBeInTheDocument();
  });

  it("renders empty state render prop", () => {
    render(
      <ConversationTimeline
        messages={[]}
        empty
        renderEmpty={() => <div>Custom Empty</div>}
      />,
    );
    expect(screen.getByText("Custom Empty")).toBeInTheDocument();
  });

  it("renders loading state render prop", () => {
    render(
      <ConversationTimeline
        messages={[]}
        loading
        renderLoading={() => <div>Custom Loading</div>}
      />,
    );
    expect(screen.getByText("Custom Loading")).toBeInTheDocument();
  });

  it("renders error state render prop", () => {
    render(
      <ConversationTimeline
        messages={[]}
        error="Oops"
        renderError={(err) => <div>Error: {err}</div>}
      />,
    );
    expect(screen.getByText("Error: Oops")).toBeInTheDocument();
  });

  it("renders custom execution entries before messages", () => {
    const customEntries = [
      { type: "execution" as const, execution: { id: "e1", objective: "Test execution", status: "completed" as const, nodes: [{ id: "n1", capability: "test", label: "Step 1", status: "completed" as const }], progress: { type: "indeterminate" as const }, logs: [], result: { success: true, summary: "Done", durationMs: 1000, taskCount: 1, completedCount: 1, failedCount: 0 }, createdAt: "2024-01-15T10:00:00Z", completedAt: "2024-01-15T10:01:00Z", durationMs: 60000 } },
    ];
    render(<ConversationTimeline messages={messages} customEntries={customEntries} />);
    expect(screen.getByText("Test execution")).toBeInTheDocument();
    expect(screen.getByText("Step 1")).toBeInTheDocument();
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders custom error entries", () => {
    const customEntries = [
      { type: "error" as const, message: "Execution failed" },
    ];
    render(<ConversationTimeline messages={messages} customEntries={customEntries} />);
    expect(screen.getByText("Execution failed")).toBeInTheDocument();
  });

  it("has log role and aria-live polite", () => {
    render(<ConversationTimeline messages={messages} />);
    const log = screen.getByRole("log");
    expect(log).toHaveAttribute("aria-live", "polite");
  });
});
