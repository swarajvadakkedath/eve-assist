import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorTimeline from "./InspectorTimeline";
import type { ExecutionSession } from "../execution/session/types";

const baseSession: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [
    { id: "st1", capability: "file.read", label: "Read file", status: "completed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:02.000Z", durationMs: 1000 },
    { id: "st2", capability: "file.write", label: "Write file", status: "failed", startedAt: "2025-01-01T00:00:02.000Z", completedAt: "2025-01-01T00:00:04.000Z", durationMs: 2000, error: "Write error" },
  ],
  logs: [],
  metadata: { toolCount: 2, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
  result: { success: true, summary: "Done", durationMs: 5000, toolCount: 2, completedCount: 1, failedCount: 1, toolsExecuted: ["file.read", "file.write"], capabilitiesUsed: ["file"] },
};

describe("InspectorTimeline", () => {
  it("renders request node", () => {
    render(<InspectorTimeline session={baseSession} />);
    expect(screen.getByText("Request")).toBeInTheDocument();
  });

  it("renders step nodes", () => {
    render(<InspectorTimeline session={baseSession} />);
    expect(screen.getByText("Read file")).toBeInTheDocument();
    expect(screen.getByText("Write file")).toBeInTheDocument();
  });

  it("renders result node", () => {
    render(<InspectorTimeline session={baseSession} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders step durations", () => {
    render(<InspectorTimeline session={baseSession} />);
    expect(screen.getByText("1.0s")).toBeInTheDocument();
    expect(screen.getByText("2.0s")).toBeInTheDocument();
  });

  it("shows error for failed step", () => {
    render(<InspectorTimeline session={baseSession} />);
    expect(screen.getByText("Write error")).toBeInTheDocument();
  });
});
