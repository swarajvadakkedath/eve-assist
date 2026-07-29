import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionSummary from "./ExecutionSummary";

describe("ExecutionSummary", () => {
  it("renders objective and task count", () => {
    render(<ExecutionSummary objective="Search files" status="completed" durationMs={5000} result={{ success: true, summary: "", durationMs: 5000, taskCount: 5, completedCount: 5, failedCount: 0 }} />);
    expect(screen.getByText("Search files")).toBeInTheDocument();
    expect(screen.getByText("5/5 steps")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<ExecutionSummary objective="Test" status="completed" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
