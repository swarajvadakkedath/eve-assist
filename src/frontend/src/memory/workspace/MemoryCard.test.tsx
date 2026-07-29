import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryCard } from "./MemoryCard";
import type { MemoryNode } from "@/memory/core";

function createMockNode(overrides: Partial<MemoryNode> = {}): MemoryNode {
  return {
    id: { value: "node-1", type: "test" },
    type: "test",
    subtype: "test:sub",
    title: "Test Node",
    summary: "A test node summary",
    createdAt: Date.now() - 10000,
    updatedAt: Date.now() - 5000,
    lastAccessed: Date.now() - 1000,
    source: "test",
    metadata: {},
    tags: ["tag1", "tag2", "tag3"],
    importance: 0.8,
    confidence: 0.9,
    accessCount: 5,
    pinned: false,
    archived: false,
    verified: true,
    verificationMethod: "manual",
    status: "active",
    ...overrides,
  };
}

describe("MemoryCard", () => {
  it("renders node title", () => {
    render(<MemoryCard node={createMockNode()} />);
    expect(screen.getByText("Test Node")).toBeInTheDocument();
  });

  it("renders subtype badge", () => {
    render(<MemoryCard node={createMockNode()} />);
    expect(screen.getByText("test:sub")).toBeInTheDocument();
  });

  it("renders summary when not compact", () => {
    render(<MemoryCard node={createMockNode()} />);
    expect(screen.getByText("A test node summary")).toBeInTheDocument();
  });

  it("hides summary in compact mode", () => {
    render(<MemoryCard node={createMockNode()} compact />);
    expect(screen.queryByText("A test node summary")).not.toBeInTheDocument();
  });

  it("shows pinned indicator when pinned", () => {
    render(<MemoryCard node={createMockNode({ pinned: true })} />);
    expect(screen.getByLabelText("Pinned")).toBeInTheDocument();
  });

  it("renders tags", () => {
    render(<MemoryCard node={createMockNode()} />);
    expect(screen.getByText("tag1")).toBeInTheDocument();
    expect(screen.getByText("tag2")).toBeInTheDocument();
    expect(screen.getByText("tag3")).toBeInTheDocument();
  });

  it("shows +N for extra tags beyond 3", () => {
    const node = createMockNode({ tags: ["a", "b", "c", "d", "e"] });
    render(<MemoryCard node={node} />);
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("hides tags when showTags is false", () => {
    render(<MemoryCard node={createMockNode()} showTags={false} />);
    expect(screen.queryByText("tag1")).not.toBeInTheDocument();
  });

  it("applies selected class when selected", () => {
    const { container } = render(<MemoryCard node={createMockNode()} selected />);
    expect(container.firstElementChild?.className).toContain("selected");
  });

  it("has button role and tabIndex", () => {
    render(<MemoryCard node={createMockNode()} />);
    const el = screen.getByRole("button");
    expect(el).toHaveAttribute("tabIndex", "0");
  });

  it("sets aria-selected when selected", () => {
    render(<MemoryCard node={createMockNode()} selected />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-selected", "true");
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<MemoryCard node={createMockNode()} onClick={onClick} />);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
