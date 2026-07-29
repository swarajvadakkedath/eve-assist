import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandLoadingState from "./CommandLoadingState";

describe("CommandLoadingState", () => {
  it("renders loading message", () => {
    render(<CommandLoadingState />);
    expect(screen.getByText("Searching...")).toBeInTheDocument();
  });

  it("renders custom message", () => {
    render(<CommandLoadingState message="Loading..." />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("has role status", () => {
    render(<CommandLoadingState />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
