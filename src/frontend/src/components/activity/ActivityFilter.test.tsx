import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ActivityFilter from "./ActivityFilter";

describe("ActivityFilter", () => {
  it("renders all filter buttons", () => {
    render(<ActivityFilter active="all" onChange={() => {}} counts={{}} />);
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("Browser")).toBeInTheDocument();
    expect(screen.getByText("Memory")).toBeInTheDocument();
    expect(screen.getByText("Plugins")).toBeInTheDocument();
    expect(screen.getByText("Voice")).toBeInTheDocument();
    expect(screen.getByText("Vision")).toBeInTheDocument();
    expect(screen.getByText("Files")).toBeInTheDocument();
  });

  it("marks active filter as pressed", () => {
    render(<ActivityFilter active="completed" onChange={() => {}} counts={{}} />);
    expect(screen.getByText("Completed")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("All")).toHaveAttribute("aria-pressed", "false");
  });

  it("shows counts when present", () => {
    render(<ActivityFilter active="all" onChange={() => {}} counts={{ all: 10, running: 3 }} />);
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("calls onChange on click", () => {
    const onChange = vi.fn();
    render(<ActivityFilter active="all" onChange={onChange} counts={{}} />);
    screen.getByText("Failed").click();
    expect(onChange).toHaveBeenCalledWith("failed");
  });

  it("has correct role", () => {
    render(<ActivityFilter active="all" onChange={() => {}} counts={{}} />);
    expect(screen.getByRole("group")).toBeInTheDocument();
  });
});
