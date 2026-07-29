import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import InspectorJsonView from "./InspectorJsonView";
import type { ExecutionSession } from "../execution/session/types";

const session: ExecutionSession = {
  id: "s1", conversationId: "c1", requestId: "r1", title: "Test",
  status: "completed", startedAt: "2025-01-01T00:00:00.000Z",
  completedAt: "2025-01-01T00:00:05.000Z", durationMs: 5000,
  steps: [{ id: "st1", capability: "file.read", label: "Read", status: "completed", startedAt: "2025-01-01T00:00:01.000Z", completedAt: "2025-01-01T00:00:02.000Z", durationMs: 1000 }],
  logs: [],
  metadata: { toolCount: 1, fileCount: 0, filesCreated: 0, filesRead: 0, filesModified: 0, filesDeleted: 0, tokensUsed: 0, retryCount: 0, permissionRequests: 0 },
  collapsed: false,
  result: { success: true, summary: "", durationMs: 5000, toolCount: 1, completedCount: 1, failedCount: 0, toolsExecuted: ["file.read"], capabilitiesUsed: ["file"] },
};

describe("InspectorJsonView", () => {
  it("renders collapse button by default", () => {
    render(<InspectorJsonView session={session} />);
    expect(screen.getByText("Collapse")).toBeInTheDocument();
  });

  it("renders copy button", () => {
    render(<InspectorJsonView session={session} />);
    expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
  });

  it("renders JSON content in code element", () => {
    const { container } = render(<InspectorJsonView session={session} />);
    const codeEl = container.querySelector("code");
    expect(codeEl).toBeInTheDocument();
    expect(codeEl!.textContent).toContain("s1");
    expect(codeEl!.textContent).toContain("completed");
  });

});
