import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryActions } from "./MemoryActions";
import type { MemoryNode } from "@/memory/core";

const mockNode: MemoryNode = {
  id: { value: "node-1", type: "test" },
  type: "test",
  subtype: "test:sub",
  title: "Test",
  summary: "",
  createdAt: 0,
  updatedAt: 0,
  lastAccessed: 0,
  source: "test",
  metadata: {},
  tags: [],
  importance: 0.5,
  confidence: 0.5,
  accessCount: 0,
  pinned: false,
  archived: false,
  verified: false,
  verificationMethod: "",
  status: "active",
};

describe("MemoryActions", () => {
  it("renders toolbar with aria-label", () => {
    render(<MemoryActions node={mockNode} />);
    expect(screen.getByRole("toolbar")).toHaveAttribute("aria-label", "Node actions");
  });

  it("renders pin button with correct label for unpinned", () => {
    render(<MemoryActions node={mockNode} onPin={vi.fn()} />);
    expect(screen.getByLabelText("Pin node")).toBeInTheDocument();
  });

  it("renders pin button with correct label for pinned", () => {
    render(<MemoryActions node={{ ...mockNode, pinned: true }} onPin={vi.fn()} />);
    expect(screen.getByLabelText("Unpin node")).toBeInTheDocument();
  });

  it("calls onPin when pin button clicked", async () => {
    const onPin = vi.fn();
    render(<MemoryActions node={mockNode} onPin={onPin} />);
    await userEvent.click(screen.getByLabelText("Pin node"));
    expect(onPin).toHaveBeenCalledWith(mockNode);
  });

  it("renders edit button", () => {
    render(<MemoryActions node={mockNode} onEdit={vi.fn()} />);
    expect(screen.getByLabelText("Edit node")).toBeInTheDocument();
  });

  it("renders archive button with correct label for unarchived", () => {
    render(<MemoryActions node={mockNode} onArchive={vi.fn()} />);
    expect(screen.getByLabelText("Archive node")).toBeInTheDocument();
  });

  it("renders archive button with correct label for archived", () => {
    render(<MemoryActions node={{ ...mockNode, archived: true }} onArchive={vi.fn()} />);
    expect(screen.getByLabelText("Restore node")).toBeInTheDocument();
  });

  it("renders delete button", () => {
    render(<MemoryActions node={mockNode} onDelete={vi.fn()} />);
    expect(screen.getByLabelText("Delete node")).toBeInTheDocument();
  });

  it("does not render buttons for unprovided callbacks", () => {
    render(<MemoryActions node={mockNode} />);
    expect(screen.queryByLabelText("Pin node")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Edit node")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Archive node")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Delete node")).not.toBeInTheDocument();
  });
});
