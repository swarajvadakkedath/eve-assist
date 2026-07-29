import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorFiles from "./InspectorFiles";
import type { ExecutionSession } from "../execution/session/types";

const session: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [
    { id: "st1", capability: "file.create", label: "Create src/index.ts", status: "completed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:02.000Z", durationMs: 1000 },
    { id: "st2", capability: "file.read", label: "Read config.json", status: "completed", startedAt: "2025-01-01T00:00:02.000Z", completedAt: "2025-01-01T00:00:03.000Z", durationMs: 1000 },
    { id: "st3", capability: "file.edit", label: "Modify package.json", status: "completed", startedAt: "2025-01-01T00:00:03.000Z", completedAt: "2025-01-01T00:00:04.000Z", durationMs: 1000 },
    { id: "st4", capability: "file.delete", label: "Remove old.ts", status: "completed", startedAt: "2025-01-01T00:00:04.000Z", completedAt: "2025-01-01T00:00:05.000Z", durationMs: 1000 },
  ],
  logs: [],
  metadata: { toolCount: 4, fileCount: 4, filesCreated: 1, filesRead: 1, filesModified: 1, filesDeleted: 1, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
};

describe("InspectorFiles", () => {
  it("renders file operation groups", () => {
    render(<InspectorFiles session={session} />);
    expect(screen.getByText("Created")).toBeInTheDocument();
    expect(screen.getByText("Read")).toBeInTheDocument();
    expect(screen.getByText("Modified")).toBeInTheDocument();
    expect(screen.getByText("Deleted")).toBeInTheDocument();
  });

  it("renders file step labels", () => {
    render(<InspectorFiles session={session} />);
    expect(screen.getByText("Create src/index.ts")).toBeInTheDocument();
    expect(screen.getByText("Read config.json")).toBeInTheDocument();
    expect(screen.getByText("Modify package.json")).toBeInTheDocument();
    expect(screen.getByText("Remove old.ts")).toBeInTheDocument();
  });

  it("shows group counts", () => {
    render(<InspectorFiles session={session} />);
    const groups = screen.getAllByText("1");
    expect(groups.length).toBeGreaterThanOrEqual(4);
  });

  it("shows empty state when no file ops", () => {
    const noFiles = { ...session, steps: session.steps.map(s => ({ ...s, capability: "search.web" })), metadata: { ...session.metadata, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0 } };
    render(<InspectorFiles session={noFiles} />);
    expect(screen.getByText(/no file operations/i)).toBeInTheDocument();
  });
});
