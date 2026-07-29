import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionBadge from "./ExecutionBadge";

describe("ExecutionBadge", () => {
  it("renders label for running state", () => {
    render(<ExecutionBadge status="running" />);
    expect(screen.getByText("Running")).toBeInTheDocument();
  });

  it("renders label for completed state", () => {
    render(<ExecutionBadge status="completed" />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders label for failed state", () => {
    render(<ExecutionBadge status="failed" />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("renders compact without label", () => {
    const { container } = render(<ExecutionBadge status="running" compact />);
    expect(container.firstChild).toHaveClass("pr-exec-badge-compact");
    expect(screen.queryByText("Running")).not.toBeInTheDocument();
  });

  it("has role status", () => {
    render(<ExecutionBadge status="planning" />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Planning");
  });
});
