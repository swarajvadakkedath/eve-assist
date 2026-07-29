import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryExplorer } from "./MemoryExplorer";
import { getMemoryStore, setMemoryStore, resetMemoryStore, MemoryStore } from "@/memory/core";
import type { NodeInput } from "@/memory/core";

function addNode(id: string, title: string, overrides: Partial<NodeInput> = {}) {
  const store = getMemoryStore();
  store.addNode({
    id,
    type: "note",
    subtype: "note",
    title,
    summary: "",
    source: "test",
    metadata: {},
    tags: [],
    importance: 0.5,
    confidence: 0.5,
    pinned: false,
    archived: false,
    verified: false,
    verificationMethod: "",
    status: "active",
    ...overrides,
  });
}

describe("MemoryExplorer", () => {
  beforeEach(() => {
    resetMemoryStore();
    const store = new MemoryStore();
    setMemoryStore(store);
    addNode("1", "Recent Item");
    addNode("2", "Pinned Item", { pinned: true });
    addNode("3", "Knowledge Item", { type: "knowledge:statement", subtype: "knowledge:statement" });
  });

  it("renders region for the current view", () => {
    render(<MemoryExplorer view="recent" />);
    expect(screen.getByRole("region")).toHaveAttribute("aria-label", "Recent");
  });

  it("renders nodes for the recent view", () => {
    render(<MemoryExplorer view="recent" />);
    expect(screen.getByText("Recent Item")).toBeInTheDocument();
  });

  it("renders breadcrumbs", () => {
    render(<MemoryExplorer view="recent" />);
    expect(screen.getByText("Memory")).toBeInTheDocument();
    expect(screen.getByText("Recent")).toBeInTheDocument();
  });

  it("renders toolbar with total count", () => {
    render(<MemoryExplorer view="recent" />);
    expect(screen.getByText("3 items")).toBeInTheDocument();
  });

  it("renders empty state when no nodes match", () => {
    resetMemoryStore();
    render(<MemoryExplorer view="recent" />);
    expect(screen.getByText("No items to display")).toBeInTheDocument();
  });

  it("uses timeline view for timeline view", () => {
    render(<MemoryExplorer view="timeline" />);
    expect(screen.getByRole("list")).toBeInTheDocument();
  });

  it("calls onSelect when node clicked", async () => {
    const onSelect = vi.fn();
    render(<MemoryExplorer view="recent" onSelect={onSelect} />);
    const item = screen.getByText("Recent Item");
    const userEvent = (await import("@testing-library/user-event")).default;
    await userEvent.click(item);
    expect(onSelect).toHaveBeenCalled();
  });
});
