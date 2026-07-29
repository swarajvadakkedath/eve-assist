import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryGrid } from "./MemoryGrid";
import type { MemoryNode } from "@/memory/core";

function createNode(id: string, title: string): MemoryNode {
  return {
    id: { value: id, type: "test" },
    type: "test",
    subtype: "test:sub",
    title,
    summary: "",
    createdAt: Date.now(),
    updatedAt: Date.now(),
    lastAccessed: Date.now(),
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
}

describe("MemoryGrid", () => {
  it("renders empty state when no nodes", () => {
    render(<MemoryGrid nodes={[]} />);
    expect(screen.getByText("No items to display")).toBeInTheDocument();
  });

  it("renders custom empty message", () => {
    render(<MemoryGrid nodes={[]} emptyMessage="Custom empty" />);
    expect(screen.getByText("Custom empty")).toBeInTheDocument();
  });

  it("renders nodes as cards", () => {
    const nodes = [createNode("1", "Node A"), createNode("2", "Node B")];
    render(<MemoryGrid nodes={nodes} />);
    expect(screen.getByText("Node A")).toBeInTheDocument();
    expect(screen.getByText("Node B")).toBeInTheDocument();
  });

  it("has grid role list", () => {
    const nodes = [createNode("1", "Node A")];
    render(<MemoryGrid nodes={nodes} />);
    expect(screen.getByRole("list")).toBeInTheDocument();
  });

  it("calls onSelect when card clicked", async () => {
    const onSelect = vi.fn();
    const nodes = [createNode("1", "Node A")];
    render(<MemoryGrid nodes={nodes} onSelect={onSelect} />);
    await userEvent.click(screen.getByText("Node A"));
    expect(onSelect).toHaveBeenCalledWith(nodes[0]);
  });

  it("selects node matching selectedId", () => {
    const nodes = [createNode("1", "Node A")];
    render(<MemoryGrid nodes={nodes} selectedId="test:1" />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-selected", "true");
  });
});
