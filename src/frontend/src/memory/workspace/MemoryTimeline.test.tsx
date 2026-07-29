import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryTimeline } from "./MemoryTimeline";
import type { MemoryNode } from "@/memory/core";

function createNode(id: string, title: string, updatedAt: number): MemoryNode {
  return {
    id: { value: id, type: "test" },
    type: "test",
    subtype: "test:sub",
    title,
    summary: "",
    createdAt: updatedAt,
    updatedAt,
    lastAccessed: updatedAt,
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

describe("MemoryTimeline", () => {
  it("renders empty state when no nodes", () => {
    render(<MemoryTimeline nodes={[]} />);
    expect(screen.getByText("No timeline items")).toBeInTheDocument();
  });

  it("groups nodes by time period", () => {
    const now = Date.now();
    const nodes = [
      createNode("1", "Today Node", now),
      createNode("2", "Yesterday Node", now - 86400000),
      createNode("3", "Old Node", now - 86400000 * 10),
    ];
    render(<MemoryTimeline nodes={nodes} />);
    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByText("Yesterday")).toBeInTheDocument();
    expect(screen.getByText("Last Week")).toBeInTheDocument();
  });

  it("renders node titles in groups", () => {
    const nodes = [
      createNode("1", "Node Today", Date.now()),
    ];
    render(<MemoryTimeline nodes={nodes} />);
    expect(screen.getByText("Node Today")).toBeInTheDocument();
  });

  it("has list role", () => {
    const nodes = [createNode("1", "Node", Date.now())];
    render(<MemoryTimeline nodes={nodes} />);
    expect(screen.getByRole("list")).toBeInTheDocument();
  });

  it("calls onSelect when item clicked", async () => {
    const onSelect = vi.fn();
    const nodes = [createNode("1", "Clickable", Date.now())];
    render(<MemoryTimeline nodes={nodes} onSelect={onSelect} />);
    await userEvent.click(screen.getByText("Clickable"));
    expect(onSelect).toHaveBeenCalledWith(nodes[0]);
  });

  it("shows count per group", () => {
    const now = Date.now();
    const nodes = [
      createNode("1", "A", now),
      createNode("2", "B", now),
    ];
    render(<MemoryTimeline nodes={nodes} />);
    expect(screen.getByText("(2)")).toBeInTheDocument();
  });
});
