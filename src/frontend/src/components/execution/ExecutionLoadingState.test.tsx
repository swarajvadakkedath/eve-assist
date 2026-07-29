import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionLoadingState from "./ExecutionLoadingState";

describe("ExecutionLoadingState", () => {
  it("renders loading status", () => {
    render(<ExecutionLoadingState />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Loading execution");
  });

  it("renders three skeleton elements", () => {
    const { container } = render(<ExecutionLoadingState />);
    expect(container.querySelectorAll(".pr-exec-loading-skeleton")).toHaveLength(3);
  });
});
