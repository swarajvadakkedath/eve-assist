import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ActivityFeed from "./ActivityFeed";
import type { ExecutionSession } from "../execution/session/types";

const sessions: ExecutionSession[] = [
  {
    id: "s1", conversationId: "c1", requestId: "r1", title: "Running task",
    status: "running", startedAt: "2025-01-01T00:00:00.000Z",
    steps: [{ id: "st1", capability: "file.read", label: "Read", status: "running", startedAt: "2025-01-01T00:00:01.000Z" }],
    logs: [],
    metadata: { toolCount: 1, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
    collapsed: false,
  },
  {
    id: "s2", conversationId: "c1", requestId: "r2", title: "Completed task",
    status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
    completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
    steps: [{ id: "st2", capability: "search.web", label: "Search", status: "completed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:02.000Z", durationMs: 1000 }],
    logs: [],
    metadata: { toolCount: 1, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
    collapsed: false,
    result: { success: true, summary: "", durationMs: 5000, toolCount: 1, completedCount: 1, failedCount: 0, toolsExecuted: ["search.web"], capabilitiesUsed: ["search"] },
  },
  {
    id: "s3", conversationId: "c1", requestId: "r3", title: "Failed task",
    status: "failed", startedAt: "2025-01-01T00:00:00.000Z",
    completedAt: "2025-01-01T00:00:03.000Z", durationMs: 3000,
    steps: [{ id: "st3", capability: "file.write", label: "Write", status: "failed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:03.000Z", durationMs: 2000, error: "err" }],
    logs: [],
    metadata: { toolCount: 1, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
    collapsed: false,
    result: { success: false, summary: "", durationMs: 3000, toolCount: 1, completedCount: 0, failedCount: 1, toolsExecuted: ["file.write"], capabilitiesUsed: ["file"] },
  },
];

describe("ActivityFeed", () => {
  it("renders all sessions with 'all' filter", () => {
    render(<ActivityFeed sessions={sessions} filter="all" />);
    expect(screen.getByText("Running task")).toBeInTheDocument();
    expect(screen.getByText("Completed task")).toBeInTheDocument();
    expect(screen.getByText("Failed task")).toBeInTheDocument();
  });

  it("filters by running status", () => {
    render(<ActivityFeed sessions={sessions} filter="running" />);
    expect(screen.getByText("Running task")).toBeInTheDocument();
    expect(screen.queryByText("Completed task")).not.toBeInTheDocument();
    expect(screen.queryByText("Failed task")).not.toBeInTheDocument();
  });

  it("filters by completed status", () => {
    render(<ActivityFeed sessions={sessions} filter="completed" />);
    expect(screen.getByText("Completed task")).toBeInTheDocument();
    expect(screen.queryByText("Running task")).not.toBeInTheDocument();
    expect(screen.queryByText("Failed task")).not.toBeInTheDocument();
  });

  it("filters by failed status", () => {
    render(<ActivityFeed sessions={sessions} filter="failed" />);
    expect(screen.getByText("Failed task")).toBeInTheDocument();
    expect(screen.queryByText("Running task")).not.toBeInTheDocument();
    expect(screen.queryByText("Completed task")).not.toBeInTheDocument();
  });

  it("filters by capability prefix", () => {
    render(<ActivityFeed sessions={sessions} filter="files" />);
    expect(screen.getByText("Running task")).toBeInTheDocument();
    expect(screen.getByText("Failed task")).toBeInTheDocument();
    expect(screen.queryByText("Completed task")).not.toBeInTheDocument();
  });

  it("has list role", () => {
    render(<ActivityFeed sessions={sessions} filter="all" />);
    expect(screen.getByRole("list")).toBeInTheDocument();
  });

  it("calls onSelectSession", () => {
    const onSelect = vi.fn();
    render(<ActivityFeed sessions={[sessions[0]]} filter="all" onSelectSession={onSelect} />);
    screen.getByText("Running task").click();
    expect(onSelect).toHaveBeenCalledWith("s1");
  });
});
