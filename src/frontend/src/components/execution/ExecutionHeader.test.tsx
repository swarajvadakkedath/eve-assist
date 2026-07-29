import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExecutionHeader from "./ExecutionHeader";

describe("ExecutionHeader", () => {
  it("renders objective", () => {
    render(<ExecutionHeader objective="Search files" status="running" expanded onToggle={vi.fn()} />);
    expect(screen.getByText("Search files")).toBeInTheDocument();
  });

  it("shows status badge", () => {
    render(<ExecutionHeader objective="Search files" status="completed" expanded onToggle={vi.fn()} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("calls onToggle when clicked", async () => {
    const onToggle = vi.fn();
    render(<ExecutionHeader objective="Test" status="running" expanded onToggle={onToggle} />);
    await userEvent.click(screen.getByRole("button"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("sets aria-expanded based on expanded prop", () => {
    const { rerender } = render(<ExecutionHeader objective="Test" status="running" expanded onToggle={vi.fn()} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "true");
    rerender(<ExecutionHeader objective="Test" status="running" expanded={false} onToggle={vi.fn()} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });
});
