import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ActivityToolbar from "./ActivityToolbar";

describe("ActivityToolbar", () => {
  it("renders session count", () => {
    render(<ActivityToolbar totalCount={5} />);
    expect(screen.getByText("5 sessions")).toBeInTheDocument();
  });

  it("renders singular", () => {
    render(<ActivityToolbar totalCount={1} />);
    expect(screen.getByText("1 session")).toBeInTheDocument();
  });

  it("renders clear all button when onClear provided and count > 0", () => {
    const onClear = vi.fn();
    render(<ActivityToolbar totalCount={3} onClear={onClear} />);
    expect(screen.getByText("Clear All")).toBeInTheDocument();
  });

  it("does not render clear button when onClear not provided", () => {
    render(<ActivityToolbar totalCount={3} />);
    expect(screen.queryByText("Clear All")).not.toBeInTheDocument();
  });

  it("does not render clear button when count is 0", () => {
    const onClear = vi.fn();
    render(<ActivityToolbar totalCount={0} onClear={onClear} />);
    expect(screen.queryByText("Clear All")).not.toBeInTheDocument();
  });

  it("calls onClear on click", () => {
    const onClear = vi.fn();
    render(<ActivityToolbar totalCount={3} onClear={onClear} />);
    screen.getByText("Clear All").click();
    expect(onClear).toHaveBeenCalledOnce();
  });
});
