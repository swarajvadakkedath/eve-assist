import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionProgress from "./ExecutionProgress";

describe("ExecutionProgress", () => {
  it("renders indeterminate progress", () => {
    const { container } = render(<ExecutionProgress progress={{ type: "indeterminate" }} />);
    expect(container.firstChild).toHaveClass("pr-exec-progress-indeterminate");
  });

  it("renders percentage progress", () => {
    render(<ExecutionProgress progress={{ type: "percentage", value: 42, max: 100 }} />);
    expect(screen.getByText("42%")).toBeInTheDocument();
  });

  it("renders steps progress", () => {
    render(<ExecutionProgress progress={{ type: "steps", current: 3, max: 7 }} />);
    expect(screen.getByText("Step 3 of 7")).toBeInTheDocument();
  });

  it("renders files progress", () => {
    render(<ExecutionProgress progress={{ type: "files", current: 14, max: 23 }} />);
    expect(screen.getByText("14 / 23 files")).toBeInTheDocument();
  });

  it("renders tokens progress", () => {
    render(<ExecutionProgress progress={{ type: "tokens", current: 500 }} />);
    expect(screen.getByText("500 tokens")).toBeInTheDocument();
  });

  it("renders custom label", () => {
    render(<ExecutionProgress progress={{ type: "custom", label: "Processing..." }} />);
    expect(screen.getByText("Processing...")).toBeInTheDocument();
  });
});
