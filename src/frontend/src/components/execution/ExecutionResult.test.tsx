import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionResult from "./ExecutionResult";
import type { ExecutionResultData } from "./types";

const successResult: ExecutionResultData = {
  success: true,
  summary: "All tasks completed successfully",
  output: "Generated report.pdf",
  durationMs: 5000,
  taskCount: 3,
  completedCount: 3,
  failedCount: 0,
  toolsExecuted: ["search", "read"],
};

const failedResult: ExecutionResultData = {
  success: false,
  summary: "Task failed",
  errors: ["File not found"],
  durationMs: 2000,
  taskCount: 2,
  completedCount: 1,
  failedCount: 1,
};

describe("ExecutionResult", () => {
  it("renders success state", () => {
    render(<ExecutionResult result={successResult} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders failed state", () => {
    render(<ExecutionResult result={failedResult} />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("renders summary", () => {
    render(<ExecutionResult result={successResult} />);
    expect(screen.getByText("All tasks completed successfully")).toBeInTheDocument();
  });

  it("renders output", () => {
    render(<ExecutionResult result={successResult} />);
    expect(screen.getByText("Generated report.pdf")).toBeInTheDocument();
  });

  it("renders task stats", () => {
    render(<ExecutionResult result={successResult} />);
    expect(screen.getByText("3 / 3 tasks completed")).toBeInTheDocument();
  });

  it("renders errors", () => {
    render(<ExecutionResult result={failedResult} />);
    expect(screen.getByText(/File not found/)).toBeInTheDocument();
  });

  it("renders tools executed", () => {
    render(<ExecutionResult result={successResult} />);
    expect(screen.getByText(/search, read/)).toBeInTheDocument();
  });
});
