import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionInspector from "./ExecutionInspector";
import { getSessionStore } from "../execution/session";

describe("ExecutionInspector", () => {
  it("renders inspector dialog", () => {
    const store = getSessionStore();
    store.applyEvent({
      type: "ExecutionStarted",
      sessionId: "s1",
      conversationId: "c1",
      requestId: "r1",
      request: "Test Session",
    });
    store.applyEvent({
      type: "ExecutionCompleted",
      sessionId: "s1",
      success: true,
      summary: "Completed",
      durationMs: 5000,
    });
    render(<ExecutionInspector sessionId="s1" onClose={() => {}} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("renders session title", () => {
    const store = getSessionStore();
    store.applyEvent({
      type: "ExecutionStarted",
      sessionId: "s2",
      conversationId: "c1",
      requestId: "r1",
      request: "Test Title",
    });
    render(<ExecutionInspector sessionId="s2" onClose={() => {}} />);
    const titles = screen.getAllByText("Test Title");
    expect(titles.length).toBeGreaterThanOrEqual(1);
  });

  it("renders close button", () => {
    const store = getSessionStore();
    store.applyEvent({
      type: "ExecutionStarted",
      sessionId: "s3",
      conversationId: "c1",
      requestId: "r1",
      request: "Test",
    });
    render(<ExecutionInspector sessionId="s3" onClose={() => {}} />);
    expect(screen.getByLabelText("Close inspector")).toBeInTheDocument();
  });

  it("shows not found for missing session", () => {
    render(<ExecutionInspector sessionId="nonexistent" onClose={() => {}} />);
    expect(screen.getByText("Session not found.")).toBeInTheDocument();
  });
});
