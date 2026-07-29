import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ActivityCenter from "./ActivityCenter";
import { getSessionStore } from "../execution/session";

describe("ActivityCenter", () => {
  it("renders activity center", () => {
    render(<ActivityCenter />);
    expect(screen.getByText("Activity")).toBeInTheDocument();
  });

  it("renders filter bar", () => {
    render(<ActivityCenter />);
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders session items via store subscription", () => {
    const store = getSessionStore();
    const id = `ac-test-${Date.now()}`;
    store.applyEvent({
      type: "ExecutionStarted",
      sessionId: id,
      conversationId: "c1",
      requestId: "r1",
      request: "Search files",
    });
    store.applyEvent({
      type: "ExecutionCompleted",
      sessionId: id,
      durationMs: 5000,
    });
    render(<ActivityCenter />);
    expect(screen.getByText("Search files")).toBeInTheDocument();
  });

  it("renders empty state container", () => {
    render(<ActivityCenter />);
    expect(screen.getByRole("region")).toBeInTheDocument();
  });

  it("renders with onSelectSession callback", () => {
    const onSelect = vi.fn();
    const store = getSessionStore();
    const id = `ac-test-sel-${Date.now()}`;
    store.applyEvent({
      type: "ExecutionStarted",
      sessionId: id,
      conversationId: "c1",
      requestId: "r1",
      request: "Test Item",
    });
    render(<ActivityCenter onSelectSession={onSelect} />);
    screen.getByText("Test Item").click();
    expect(onSelect).toHaveBeenCalledWith(id);
  });

  it("has correct region role", () => {
    render(<ActivityCenter />);
    expect(screen.getByRole("region")).toBeInTheDocument();
  });
});
