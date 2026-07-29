import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExecutionCard from "./ExecutionCard";
import type { ExecutionState } from "./types";

const runningExecution: ExecutionState = {
  id: "exec-1",
  objective: "Search files",
  status: "running",
  nodes: [
    { id: "n1", capability: "search", label: "Search Documents", status: "completed" },
    { id: "n2", capability: "read", label: "Read Results", status: "running", progress: { type: "indeterminate" } },
  ],
  progress: { type: "indeterminate" },
  logs: [],
  createdAt: "2024-01-15T10:00:00Z",
  startedAt: "2024-01-15T10:00:01Z",
};

const completedExecution: ExecutionState = {
  id: "exec-2",
  objective: "Generate report",
  status: "completed",
  nodes: [
    { id: "n1", capability: "search", label: "Search Data", status: "completed" },
    { id: "n2", capability: "analyze", label: "Analyze", status: "completed" },
    { id: "n3", capability: "write", label: "Generate", status: "completed" },
  ],
  progress: { type: "percentage", value: 100, max: 100 },
  logs: [
    { timestamp: "2024-01-15T10:00:00Z", level: "info", message: "Started" },
    { timestamp: "2024-01-15T10:05:00Z", level: "info", message: "Completed" },
  ],
  result: {
    success: true,
    summary: "Report generated",
    durationMs: 300000,
    taskCount: 3,
    completedCount: 3,
    failedCount: 0,
  },
  createdAt: "2024-01-15T10:00:00Z",
  startedAt: "2024-01-15T10:00:01Z",
  completedAt: "2024-01-15T10:05:01Z",
  durationMs: 300000,
};

describe("ExecutionCard", () => {
  it("renders objective in header", () => {
    render(<ExecutionCard execution={runningExecution} />);
    expect(screen.getByText("Search files")).toBeInTheDocument();
  });

  it("renders thread nodes", () => {
    render(<ExecutionCard execution={runningExecution} />);
    expect(screen.getByText("Search Documents")).toBeInTheDocument();
    expect(screen.getByText("Read Results")).toBeInTheDocument();
  });

  it("renders summary when collapsed and terminal", () => {
    render(<ExecutionCard execution={completedExecution} expanded={false} />);
    expect(screen.getAllByText("Generate report")).toHaveLength(2);
    expect(screen.getByText("3/3 steps")).toBeInTheDocument();
  });

  it("renders result when present", () => {
    render(<ExecutionCard execution={completedExecution} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders logs when present", () => {
    render(<ExecutionCard execution={completedExecution} />);
    expect(screen.getByText("Logs (2)")).toBeInTheDocument();
  });

  it("renders action buttons for running state", () => {
    render(<ExecutionCard execution={runningExecution} onPause={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText("Pause")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("renders retry button for completed state", () => {
    render(<ExecutionCard execution={completedExecution} onRetry={vi.fn()} />);
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("calls onToggle when header clicked", async () => {
    const onToggle = vi.fn();
    render(<ExecutionCard execution={runningExecution} expanded onToggle={onToggle} />);
    await userEvent.click(screen.getByRole("button", { name: /Search files/ }));
    expect(onToggle).toHaveBeenCalledWith(false);
  });

  it("has region role", () => {
    render(<ExecutionCard execution={runningExecution} />);
    expect(screen.getByRole("region")).toBeInTheDocument();
  });
});
