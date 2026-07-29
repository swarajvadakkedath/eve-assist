import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorPermissions from "./InspectorPermissions";
import type { ExecutionSession } from "../execution/session/types";

describe("InspectorPermissions", () => {
  it("shows requested when status is permission", () => {
    const permSession: ExecutionSession = {
      id: "s1", conversationId: "c1", requestId: "r1", title: "Perm test",
      status: "permission", startedAt: "2025-01-01T00:00:00.000Z",
      steps: [], logs: [],
      metadata: { toolCount: 0, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 2 },
      collapsed: false,
    };
    render(<InspectorPermissions session={permSession} />);
    expect(screen.getByText(/permission/i)).toBeInTheDocument();
    expect(screen.getByText(/2/)).toBeInTheDocument();
  });

  it("shows empty state when no permission requests", () => {
    const noPerm: ExecutionSession = {
      id: "s1", conversationId: "c1", requestId: "r1", title: "No perm",
      status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
      completedAt: "2025-01-01T00:00:01.000Z", durationMs: 1000,
      steps: [], logs: [],
      metadata: { toolCount: 0, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
      collapsed: false,
      result: { success: true, summary: "", durationMs: 1000, toolCount: 0, completedCount: 0, failedCount: 0, toolsExecuted: [], capabilitiesUsed: [] },
    };
    render(<InspectorPermissions session={noPerm} />);
    expect(screen.getByText("No permission requests in this session.")).toBeInTheDocument();
  });

  it("shows resolved for completed sessions with requests", () => {
    const resolved: ExecutionSession = {
      id: "s1", conversationId: "c1", requestId: "r1", title: "Resolved",
      status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
      completedAt: "2025-01-01T00:00:01.000Z", durationMs: 1000,
      steps: [], logs: [],
      metadata: { toolCount: 0, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 3 },
      collapsed: false,
      result: { success: true, summary: "", durationMs: 1000, toolCount: 0, completedCount: 0, failedCount: 0, toolsExecuted: [], capabilitiesUsed: [] },
    };
    render(<InspectorPermissions session={resolved} />);
    expect(screen.getByText(/resolved/i)).toBeInTheDocument();
  });
});
