import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorLogs from "./InspectorLogs";
import type { ExecutionSession } from "../execution/session/types";

const session: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [],
  logs: [
    { timestamp: "2025-01-01T00:00:01.000Z", level: "info", message: "Starting", source: "system" },
    { timestamp: "2025-01-01T00:00:02.000Z", level: "warn", message: "Warning message", source: "tool" },
    { timestamp: "2025-01-01T00:00:03.000Z", level: "error", message: "Error occurred", source: "tool" },
    { timestamp: "2025-01-01T00:00:04.000Z", level: "debug", message: "Debug info", source: "system" },
  ],
  metadata: { toolCount: 0, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
};

describe("InspectorLogs", () => {
  it("renders all log entries", () => {
    render(<InspectorLogs session={session} />);
    expect(screen.getByText("Starting")).toBeInTheDocument();
    expect(screen.getByText("Warning message")).toBeInTheDocument();
    expect(screen.getByText("Error occurred")).toBeInTheDocument();
    expect(screen.getByText("Debug info")).toBeInTheDocument();
  });

  it("renders level labels", () => {
    render(<InspectorLogs session={session} />);
    expect(screen.getByText("INFO")).toBeInTheDocument();
    expect(screen.getByText("WARN")).toBeInTheDocument();
    expect(screen.getByText("ERROR")).toBeInTheDocument();
    expect(screen.getByText("DEBUG")).toBeInTheDocument();
  });

  it("renders filter buttons (lowercase labels)", () => {
    render(<InspectorLogs session={session} />);
    expect(screen.getByText("all")).toBeInTheDocument();
    expect(screen.getByText("info")).toBeInTheDocument();
    expect(screen.getByText("warn")).toBeInTheDocument();
    expect(screen.getByText("error")).toBeInTheDocument();
    expect(screen.getByText("debug")).toBeInTheDocument();
  });

  it("shows empty state when no logs", () => {
    const noLogs = { ...session, logs: [] };
    render(<InspectorLogs session={noLogs} />);
    expect(screen.getByText("No logs recorded for this session.")).toBeInTheDocument();
  });

  it("renders collapse toggle with log count", () => {
    render(<InspectorLogs session={session} />);
    expect(screen.getByText(/4 logs/)).toBeInTheDocument();
  });
});
