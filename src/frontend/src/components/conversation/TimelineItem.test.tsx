import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TimelineItem from "./TimelineItem";
import type { Message } from "./types";
import type { ExecutionState } from "../execution/types";
import type { ExecutionSession } from "../execution/session/types";

const userMsg: Message = {
  id: "u1", conversation_id: "c1", role: "user",
  content: "Hi", timestamp: "2024-01-15T10:30:00Z",
  tokens_used: 0, attachments: [], metadata: {},
};

const assistantMsg: Message = {
  id: "a1", conversation_id: "c1", role: "assistant",
  content: "Hello!", timestamp: "2024-01-15T10:30:01Z",
  tokens_used: 10, attachments: [], metadata: {},
};

const systemMsg: Message = {
  id: "s1", conversation_id: "c1", role: "system",
  content: "System message", timestamp: "2024-01-15T10:30:02Z",
  tokens_used: 0, attachments: [], metadata: {},
};

const sessionState: ExecutionSession = {
  id: "session-1",
  conversationId: "c1",
  requestId: "req-1",
  title: "Read my files",
  status: "completed",
  startedAt: "2024-01-15T10:00:00Z",
  completedAt: "2024-01-15T10:01:00Z",
  durationMs: 60000,
  steps: [{ id: "n1", capability: "file.read", label: "Read file", status: "completed" }],
  logs: [],
  metadata: { toolCount: 1, fileCount: 0, filesCreated: 0, filesRead: 1, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  result: { success: true, summary: "Read 1 file · Completed in 60.0s", durationMs: 60000, toolCount: 1, completedCount: 1, failedCount: 0, toolsExecuted: ["file.read"] },
  collapsed: true,
};

const executionState: ExecutionState = {
  id: "exec-1",
  objective: "Test execution",
  status: "completed",
  nodes: [{ id: "n1", capability: "test", label: "Test step", status: "completed" }],
  progress: { type: "indeterminate" },
  logs: [],
  result: { success: true, summary: "Done", durationMs: 1000, taskCount: 1, completedCount: 1, failedCount: 0 },
  createdAt: "2024-01-15T10:00:00Z",
  completedAt: "2024-01-15T10:01:00Z",
  durationMs: 60000,
};

describe("TimelineItem", () => {
  it("renders user message entry", () => {
    render(<TimelineItem entry={{ type: "message", message: userMsg }} />);
    expect(screen.getByText("Hi")).toBeInTheDocument();
  });

  it("renders assistant message entry", () => {
    render(<TimelineItem entry={{ type: "message", message: assistantMsg }} />);
    expect(screen.getByText("Hello!")).toBeInTheDocument();
  });

  it("renders system message entry", () => {
    render(<TimelineItem entry={{ type: "message", message: systemMsg }} />);
    expect(screen.getByText("System message")).toBeInTheDocument();
  });

  it("renders streaming entry", () => {
    render(
      <TimelineItem
        entry={{ type: "streaming", message: assistantMsg, streamingContent: "Thinking..." }}
      />,
    );
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
  });

  it("renders typing entry", () => {
    const { container } = render(<TimelineItem entry={{ type: "typing" }} />);
    expect(container.querySelector(".pr-typing")).toBeInTheDocument();
  });

  it("renders divider entry", () => {
    render(<TimelineItem entry={{ type: "divider", label: "Today" }} />);
    expect(screen.getByText("Today")).toBeInTheDocument();
  });

  it("renders execution entry", () => {
    render(<TimelineItem entry={{ type: "execution", execution: executionState }} />);
    expect(screen.getByText("Test execution")).toBeInTheDocument();
    expect(screen.getByText("Test step")).toBeInTheDocument();
  });

  it("renders session entry", () => {
    render(<TimelineItem entry={{ type: "session", session: sessionState }} />);
    expect(screen.getAllByText("Read my files").length).toBeGreaterThanOrEqual(1);
  });

  it("renders error entry", () => {
    render(<TimelineItem entry={{ type: "error", message: "Network error" }} />);
    expect(screen.getByText("Network error")).toBeInTheDocument();
  });

  it("renders attachment entry", () => {
    render(<TimelineItem entry={{ type: "attachment", label: "file.pdf" }} />);
    expect(screen.getByText("file.pdf")).toBeInTheDocument();
  });

  it("renders memory entry", () => {
    render(<TimelineItem entry={{ type: "memory", content: "Remembered context" }} />);
    expect(screen.getByText("Remembered context")).toBeInTheDocument();
  });

  it("renders result entry", () => {
    render(<TimelineItem entry={{ type: "result", label: "Task completed", success: true }} />);
    expect(screen.getByText("Task completed")).toBeInTheDocument();
  });

  it("renders system entry", () => {
    render(<TimelineItem entry={{ type: "system", content: "System notice" }} />);
    expect(screen.getByText("System notice")).toBeInTheDocument();
  });

  it("returns null for unknown entry type", () => {
    const { container } = render(
      <TimelineItem entry={{ type: "unknown" as any }} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
