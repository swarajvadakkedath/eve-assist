import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryToolbar } from "./MemoryToolbar";

describe("MemoryToolbar", () => {
  const defaultProps = {
    viewMode: "grid" as const,
    onViewModeChange: vi.fn(),
    sortField: "updatedAt" as const,
    sortOrder: "desc" as const,
    onSortChange: vi.fn(),
    totalCount: 10,
  };

  it("renders toolbar with toolbar role", () => {
    render(<MemoryToolbar {...defaultProps} />);
    expect(screen.getByRole("toolbar")).toBeInTheDocument();
  });

  it("renders view mode buttons", () => {
    render(<MemoryToolbar {...defaultProps} />);
    expect(screen.getByLabelText("Grid view")).toBeInTheDocument();
    expect(screen.getByLabelText("List view")).toBeInTheDocument();
  });

  it("toggles view mode", async () => {
    const onViewModeChange = vi.fn();
    render(<MemoryToolbar {...defaultProps} onViewModeChange={onViewModeChange} />);
    await userEvent.click(screen.getByLabelText("List view"));
    expect(onViewModeChange).toHaveBeenCalledWith("list");
  });

  it("renders total count", () => {
    render(<MemoryToolbar {...defaultProps} totalCount={42} />);
    expect(screen.getByText("42 items")).toBeInTheDocument();
  });

  it("renders singular count for 1 item", () => {
    render(<MemoryToolbar {...defaultProps} totalCount={1} />);
    expect(screen.getByText("1 item")).toBeInTheDocument();
  });

  it("renders sort select with label", () => {
    render(<MemoryToolbar {...defaultProps} />);
    expect(screen.getByLabelText("Sort by")).toBeInTheDocument();
  });

  it("renders sort direction button", () => {
    render(<MemoryToolbar {...defaultProps} />);
    expect(screen.getByLabelText("Sort ascending")).toBeInTheDocument();
  });

  it("toggles sort direction", async () => {
    const onSortChange = vi.fn();
    render(<MemoryToolbar {...defaultProps} onSortChange={onSortChange} />);
    await userEvent.click(screen.getByLabelText("Sort ascending"));
    expect(onSortChange).toHaveBeenCalledWith("updatedAt", "asc");
  });

  it("renders new node button when callback provided", () => {
    const onNewNode = vi.fn();
    render(<MemoryToolbar {...defaultProps} onNewNode={onNewNode} />);
    expect(screen.getByLabelText("Create new node")).toBeInTheDocument();
  });

  it("does not render new node button when callback not provided", () => {
    render(<MemoryToolbar {...defaultProps} />);
    expect(screen.queryByLabelText("Create new node")).not.toBeInTheDocument();
  });

  it("renders filter toggle button when callback provided", () => {
    const onToggleFilters = vi.fn();
    render(<MemoryToolbar {...defaultProps} onToggleFilters={onToggleFilters} />);
    expect(screen.getByLabelText("Toggle filters")).toBeInTheDocument();
  });
});
