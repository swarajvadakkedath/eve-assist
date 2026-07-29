import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionEmptyState from "./ExecutionEmptyState";

describe("ExecutionEmptyState", () => {
  it("renders default message", () => {
    render(<ExecutionEmptyState />);
    expect(screen.getByText("No executions yet")).toBeInTheDocument();
  });

  it("renders custom message", () => {
    render(<ExecutionEmptyState message="Custom message" />);
    expect(screen.getByText("Custom message")).toBeInTheDocument();
  });

  it("has role status", () => {
    render(<ExecutionEmptyState />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
