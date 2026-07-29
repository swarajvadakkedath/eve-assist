import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandEmptyState from "./CommandEmptyState";

describe("CommandEmptyState", () => {
  it("renders default empty state", () => {
    render(<CommandEmptyState query="" />);
    expect(screen.getByText("Type a command or search")).toBeInTheDocument();
  });

  it("renders no results state", () => {
    render(<CommandEmptyState query="unknown" />);
    expect(screen.getByText(/No results for/)).toBeInTheDocument();
  });

  it("has role status", () => {
    render(<CommandEmptyState query="" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
