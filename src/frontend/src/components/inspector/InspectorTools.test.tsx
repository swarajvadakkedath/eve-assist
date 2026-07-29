import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorTools from "./InspectorTools";
import type { ExecutionSession } from "../execution/session/types";

const session: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [
    { id: "st1", capability: "file.read", label: "Read config", status: "completed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:02.000Z", durationMs: 1000 },
    { id: "st2", capability: "file.write", label: "Write output", status: "failed", startedAt: "2025-01-01T00:00:02.000Z", completedAt: "2025-01-01T00:00:04.000Z", durationMs: 2000, error: "Permission denied" },
    { id: "st3", capability: "search.web", label: "Search web", status: "running", startedAt: "2025-01-01T00:00:04.000Z" },
  ],
  logs: [],
  metadata: { toolCount: 3, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
};

describe("InspectorTools", () => {
  it("renders all tool cards", () => {
    render(<InspectorTools session={session} />);
    expect(screen.getByText("Read config")).toBeInTheDocument();
    expect(screen.getByText("Write output")).toBeInTheDocument();
    expect(screen.getByText("Search web")).toBeInTheDocument();
  });

  it("renders capabilities", () => {
    render(<InspectorTools session={session} />);
    expect(screen.getByText("file.read")).toBeInTheDocument();
    expect(screen.getByText("file.write")).toBeInTheDocument();
    expect(screen.getByText("search.web")).toBeInTheDocument();
  });

  it("renders durations as ms for completed steps", () => {
    render(<InspectorTools session={session} />);
    expect(screen.getByText("1000ms")).toBeInTheDocument();
    expect(screen.getByText("2000ms")).toBeInTheDocument();
  });

  it("renders error for failed step", () => {
    render(<InspectorTools session={session} />);
    expect(screen.getByText(/Error: Permission denied/)).toBeInTheDocument();
  });
});
