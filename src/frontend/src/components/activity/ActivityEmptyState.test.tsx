import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ActivityEmptyState from "./ActivityEmptyState";

describe("ActivityEmptyState", () => {
  it("renders default message", () => {
    render(<ActivityEmptyState />);
    expect(screen.getByText("No activity yet")).toBeInTheDocument();
    expect(screen.getByText(/Execution sessions will appear here/)).toBeInTheDocument();
  });

  it("renders filter-specific message", () => {
    render(<ActivityEmptyState filter="running" />);
    expect(screen.getByText("No running activity")).toBeInTheDocument();
    expect(screen.getByText(/match the.*running.*filter/i)).toBeInTheDocument();
  });

  it("renders different filter", () => {
    render(<ActivityEmptyState filter="failed" />);
    expect(screen.getByText("No failed activity")).toBeInTheDocument();
  });

  it("has status role", () => {
    render(<ActivityEmptyState />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
