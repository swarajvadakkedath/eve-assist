import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExecutionErrorState from "./ExecutionErrorState";

describe("ExecutionErrorState", () => {
  it("renders error message", () => {
    render(<ExecutionErrorState error="Something went wrong" />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("has alert role", () => {
    render(<ExecutionErrorState error="Error" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("renders retry button when handler provided", () => {
    render(<ExecutionErrorState error="Error" onRetry={vi.fn()} />);
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("calls onRetry when clicked", async () => {
    const onRetry = vi.fn();
    render(<ExecutionErrorState error="Error" onRetry={onRetry} />);
    await userEvent.click(screen.getByText("Retry"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
