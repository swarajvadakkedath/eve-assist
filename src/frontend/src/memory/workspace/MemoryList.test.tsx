import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryList } from "./MemoryList";
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

describe("MemoryList", () => {
  it("renders empty state when no nodes", () => {
    render(<MemoryList nodes={[]} />);
    expect(screen.getByText("No items to display")).toBeInTheDocument();
  });

  it("renders nodes as list items", () => {
    const nodes = [createNode("1", "Node A"), createNode("2", "Node B")];
    render(<MemoryList nodes={nodes} />);
    expect(screen.getByText("Node A")).toBeInTheDocument();
    expect(screen.getByText("Node B")).toBeInTheDocument();
  });

  it("has list role", () => {
    const nodes = [createNode("1", "Node A")];
    render(<MemoryList nodes={nodes} />);
    expect(screen.getByRole("list")).toBeInTheDocument();
  });

  it("calls onSelect when item clicked", async () => {
    const onSelect = vi.fn();
    const nodes = [createNode("1", "Node A")];
    render(<MemoryList nodes={nodes} onSelect={onSelect} />);
    await userEvent.click(screen.getByText("Node A"));
    expect(onSelect).toHaveBeenCalledWith(nodes[0]);
  });

  it("selects node matching selectedId", () => {
    const nodes = [createNode("1", "Node A")];
    render(<MemoryList nodes={nodes} selectedId="test:1" />);
    const items = screen.getAllByRole("listitem");
    expect(items[0].className).toContain("selected");
  });

  it("renders type badge for each item", () => {
    const nodes = [createNode("1", "Node A")];
    render(<MemoryList nodes={nodes} />);
    expect(screen.getByText("test:sub")).toBeInTheDocument();
  });
});
