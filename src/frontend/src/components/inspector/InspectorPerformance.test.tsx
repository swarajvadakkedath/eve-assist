import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorPerformance from "./InspectorPerformance";
import type { ExecutionSession } from "../execution/session/types";

const session: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [
    { id: "st1", capability: "file.read", label: "Read config", status: "completed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:02.000Z", durationMs: 1000 },
    { id: "st2", capability: "file.write", label: "Write output", status: "completed", startedAt: "2025-01-01T00:00:02.000Z", completedAt: "2025-01-01T00:00:04.000Z", durationMs: 2000 },
  ],
  logs: [],
  metadata: { toolCount: 2, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
  result: { success: true, summary: "", durationMs: 5000, toolCount: 2, completedCount: 2, failedCount: 0, toolsExecuted: ["file.read", "file.write"], capabilitiesUsed: ["file"] },
};

describe("InspectorPerformance", () => {
  it("renders performance section", () => {
    render(<InspectorPerformance session={session} />);
    expect(screen.getByText("Performance Breakdown")).toBeInTheDocument();
  });

  it("renders total duration bar", () => {
    render(<InspectorPerformance session={session} />);
    expect(screen.getByText("Total Duration")).toBeInTheDocument();
    expect(screen.getByText("5.0s")).toBeInTheDocument();
  });

  it("renders steps total bar", () => {
    render(<InspectorPerformance session={session} />);
    expect(screen.getByText("Steps Total")).toBeInTheDocument();
  });

  it("renders longest step", () => {
    render(<InspectorPerformance session={session} />);
    expect(screen.getByText(/Longest Step/i)).toBeInTheDocument();
    const writeOutputs = screen.getAllByText(/Write output/);
    expect(writeOutputs.length).toBeGreaterThanOrEqual(1);
  });

  it("renders step timing table", () => {
    render(<InspectorPerformance session={session} />);
    expect(screen.getByText("Step Timing")).toBeInTheDocument();
  });

  it("renders individual step rows", () => {
    render(<InspectorPerformance session={session} />);
    expect(screen.getByText("Read config")).toBeInTheDocument();
    expect(screen.getByText("Write output")).toBeInTheDocument();
  });
});
