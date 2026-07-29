import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorSummary from "./InspectorSummary";
import type { ExecutionSession } from "../execution/session/types";

const baseSession: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test Session",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [
    { id: "st1", capability: "file.read", label: "Read file", status: "completed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:02.000Z", durationMs: 1000 },
    { id: "st2", capability: "file.write", label: "Write file", status: "completed", startedAt: "2025-01-01T00:00:02.000Z", completedAt: "2025-01-01T00:00:04.000Z", durationMs: 2000 },
  ],
  logs: [],
  metadata: { toolCount: 2, fileCount: 3, filesCreated: 1, filesRead: 1, filesModified: 1, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
  result: { success: true, summary: "Done", durationMs: 5000, toolCount: 2, completedCount: 2, failedCount: 0, toolsExecuted: ["file.read", "file.write"], capabilitiesUsed: ["file"] },
};

describe("InspectorSummary", () => {
  it("renders session title", () => {
    render(<InspectorSummary session={baseSession} />);
    expect(screen.getByText("Test Session")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<InspectorSummary session={baseSession} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders started and finished time", () => {
    render(<InspectorSummary session={baseSession} />);
    expect(screen.getByText("Started")).toBeInTheDocument();
    expect(screen.getByText("Finished")).toBeInTheDocument();
  });

  it("renders duration", () => {
    render(<InspectorSummary session={baseSession} />);
    expect(screen.getByText("Duration")).toBeInTheDocument();
  });

  it("renders tool count", () => {
    render(<InspectorSummary session={baseSession} />);
    expect(screen.getByText("Tools")).toBeInTheDocument();
  });

  it("renders capabilities", () => {
    render(<InspectorSummary session={baseSession} />);
    expect(screen.getByText("file")).toBeInTheDocument();
  });

  it("renders file count", () => {
    render(<InspectorSummary session={baseSession} />);
    expect(screen.getByText("Files Changed")).toBeInTheDocument();
    const threes = screen.getAllByText("3");
    expect(threes.length).toBeGreaterThanOrEqual(1);
  });

  it("renders outcome for terminal session", () => {
    render(<InspectorSummary session={baseSession} />);
    expect(screen.getByText("Completed Successfully")).toBeInTheDocument();
  });

  it("renders error when present", () => {
    const errSession = { ...baseSession, status: "failed" as const, error: "Something went wrong" };
    render(<InspectorSummary session={errSession} />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("shows step counts for failed session", () => {
    const failedSession = {
      ...baseSession,
      status: "failed" as const,
      result: { ...baseSession.result!, success: false, failedCount: 1, completedCount: 1 },
      steps: [
        { ...baseSession.steps[0] },
        { ...baseSession.steps[1], status: "failed" as const, error: "err" },
      ],
    };
    render(<InspectorSummary session={failedSession} />);
    const failedElements = screen.getAllByText("Failed");
    expect(failedElements.length).toBeGreaterThanOrEqual(1);
  });
});
