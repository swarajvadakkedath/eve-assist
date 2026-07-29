import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorMetadata from "./InspectorMetadata";
import type { ExecutionSession } from "../execution/session/types";

const session: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [], logs: [],
  metadata: { toolCount: 2, fileCount: 3, filesCreated: 1, filesRead: 1, filesModified: 1, filesDeleted: 0, tokensUsed: 500, retryCount: 1, permissionRequests: 2 },
  collapsed: false,
  result: { success: true, summary: "", durationMs: 5000, toolCount: 2, completedCount: 2, failedCount: 0, toolsExecuted: [], capabilitiesUsed: [] },
};

describe("InspectorMetadata", () => {
  it("renders session metadata grid", () => {
    render(<InspectorMetadata session={session} />);
    expect(screen.getByText("Session Metadata")).toBeInTheDocument();
  });

  it("renders session id", () => {
    render(<InspectorMetadata session={session} />);
    expect(screen.getByText("s1")).toBeInTheDocument();
  });

  it("renders conversation id", () => {
    render(<InspectorMetadata session={session} />);
    expect(screen.getByText("c1")).toBeInTheDocument();
  });

  it("renders status", () => {
    render(<InspectorMetadata session={session} />);
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("renders tool count", () => {
    render(<InspectorMetadata session={session} />);
    const twos = screen.getAllByText("2");
    expect(twos.length).toBeGreaterThanOrEqual(2);
  });

  it("renders file stats", () => {
    render(<InspectorMetadata session={session} />);
    expect(screen.getByText("Files Changed")).toBeInTheDocument();
    expect(screen.getByText("Files Created")).toBeInTheDocument();
    expect(screen.getByText("Files Read")).toBeInTheDocument();
    expect(screen.getByText("Files Modified")).toBeInTheDocument();
  });

  it("renders tokens used", () => {
    render(<InspectorMetadata session={session} />);
    expect(screen.getByText("500")).toBeInTheDocument();
  });
});
