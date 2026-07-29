import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorActions from "./InspectorActions";
import type { ExecutionSession } from "../execution/session/types";

const baseSession: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [], logs: [],
  metadata: { toolCount: 0, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
  result: { success: true, summary: "Done", durationMs: 5000, toolCount: 0, completedCount: 0, failedCount: 0, toolsExecuted: [], capabilitiesUsed: [] },
};

describe("InspectorActions", () => {
  it("renders copy summary button", () => {
    render(<InspectorActions session={baseSession} onClose={() => {}} />);
    expect(screen.getByText("Copy Summary")).toBeInTheDocument();
  });

  it("renders open result button for terminal session with output", () => {
    const withOutput = {
      ...baseSession,
      result: { ...baseSession.result!, output: "some output" },
    };
    render(<InspectorActions session={withOutput} onClose={() => {}} />);
    expect(screen.getByText("Open Result")).toBeInTheDocument();
  });

  it("renders close inspector button", () => {
    render(<InspectorActions session={baseSession} onClose={() => {}} />);
    expect(screen.getByText("Close Inspector")).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(<InspectorActions session={baseSession} onClose={onClose} />);
    screen.getByText("Close Inspector").click();
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not show open result when no output", () => {
    render(<InspectorActions session={baseSession} onClose={() => {}} />);
    expect(screen.queryByText("Open Result")).not.toBeInTheDocument();
  });
});
