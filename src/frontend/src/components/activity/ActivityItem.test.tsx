import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ActivityItem from "./ActivityItem";
import type { ExecutionSession } from "../execution/session/types";

const session: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test Session",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [
    { id: "st1", capability: "file.read", label: "Read", status: "completed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:02.000Z", durationMs: 1000 },
    { id: "st2", capability: "search.web", label: "Search", status: "completed", startedAt: "2025-01-01T00:00:02.000Z", completedAt: "2025-01-01T00:00:04.000Z", durationMs: 2000 },
  ],
  logs: [],
  metadata: { toolCount: 2, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
  result: { success: true, summary: "", durationMs: 5000, toolCount: 2, completedCount: 2, failedCount: 0, toolsExecuted: ["file.read", "search.web"], capabilitiesUsed: ["file", "search"] },
};

describe("ActivityItem", () => {
  it("renders session title", () => {
    render(<ActivityItem session={session} />);
    expect(screen.getByText("Test Session")).toBeInTheDocument();
  });

  it("renders capabilities", () => {
    render(<ActivityItem session={session} />);
    expect(screen.getByText("file, search")).toBeInTheDocument();
  });

  it("renders step count", () => {
    render(<ActivityItem session={session} />);
    expect(screen.getByText("2 steps")).toBeInTheDocument();
  });

  it("renders duration", () => {
    render(<ActivityItem session={session} />);
    expect(screen.getByText("5.0s")).toBeInTheDocument();
  });

  it("has listitem role", () => {
    render(<ActivityItem session={session} />);
    expect(screen.getByRole("listitem")).toBeInTheDocument();
  });

  it("calls onSelect on click", () => {
    const onSelect = vi.fn();
    render(<ActivityItem session={session} onSelect={onSelect} />);
    screen.getByText("Test Session").click();
    expect(onSelect).toHaveBeenCalledWith("s1");
  });

  it("renders status badge", () => {
    render(<ActivityItem session={session} />);
    expect(screen.getByText("Done")).toBeInTheDocument();
  });

  it("renders running session with active class", () => {
    const running = { ...session, status: "running" as const, durationMs: undefined, completedAt: undefined };
    const { container } = render(<ActivityItem session={running} />);
    expect(container.querySelector(".pr-activity-item-active")).toBeInTheDocument();
  });

  it("renders failed session with failed class", () => {
    const failed = { ...session, status: "failed" as const };
    const { container } = render(<ActivityItem session={failed} />);
    expect(container.querySelector(".pr-activity-item-failed")).toBeInTheDocument();
  });
});
