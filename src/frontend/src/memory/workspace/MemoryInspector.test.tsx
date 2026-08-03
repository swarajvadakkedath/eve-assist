import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryInspector } from "./MemoryInspector";
import { setMemoryStore, resetMemoryStore, MemoryStore } from "@/memory/core";
import type { MemoryNode } from "@/memory/core";

const mockNode: MemoryNode = {
  id: { value: "node-1", type: "test" },
  type: "test",
  subtype: "test:sub",
  title: "Inspected Node",
  summary: "Node summary for inspector",
  createdAt: 1000000,
  updatedAt: 2000000,
  lastAccessed: 3000000,
  source: "test",
  metadata: {},
  tags: ["tag1"],
  importance: 0.75,
  confidence: 0.85,
  accessCount: 10,
  pinned: true,
  archived: false,
  verified: true,
  verificationMethod: "auto",
  status: "active",
};

describe("MemoryInspector", () => {
  beforeEach(() => {
    resetMemoryStore();
  });

  it("renders node title in header area", () => {
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByText("Inspected Node")).toBeInTheDocument();
  });

  it("renders complementary role", () => {
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByRole("complementary")).toBeInTheDocument();
  });

  it("renders inspector header", () => {
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByText("Inspector")).toBeInTheDocument();
  });

  it("renders close button when onClose provided", () => {
    render(<MemoryInspector node={mockNode} onClose={vi.fn()} />);
    expect(screen.getByLabelText("Close inspector")).toBeInTheDocument();
  });

  it("renders importance progress bar", () => {
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByLabelText("Importance: 75%")).toBeInTheDocument();
  });

  it("renders confidence progress bar", () => {
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByLabelText("Confidence: 85%")).toBeInTheDocument();
  });

  it("renders access count", () => {
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByText("10")).toBeInTheDocument();
  });

  it("renders outgoing children when nodes exist via graph direct add", () => {
    const store = new MemoryStore();
    setMemoryStore(store);
    store.graph.addNode({ id: "node-1", type: "test", subtype: "test:sub", title: "Inspected Node", summary: "Node summary for inspector", source: "test" });
    store.graph.addNode({ id: "child-1", type: "note", subtype: "note", title: "Child Node", summary: "", source: "test" });
    store.graph.addEdge({ sourceNodeId: { value: "node-1", type: "test" }, targetNodeId: { value: "child-1", type: "note" }, type: "contains" });
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByText("Child Node")).toBeInTheDocument();
  });

  it("renders actions when provided", () => {
    render(<MemoryInspector node={mockNode} actions={{ onPin: vi.fn() }} />);
    expect(screen.getByLabelText("Unpin node")).toBeInTheDocument();
  });

  it("shows children count when outgoing edges exist", () => {
    const store = new MemoryStore();
    setMemoryStore(store);
    store.graph.addNode({ id: "node-1", type: "test", subtype: "test:sub", title: "Inspected Node", summary: "Node summary for inspector", source: "test" });
    store.graph.addNode({ id: "child-1", type: "note", subtype: "note", title: "Child Zed", summary: "", source: "test" });
    store.graph.addEdge({ sourceNodeId: { value: "node-1", type: "test" }, targetNodeId: { value: "child-1", type: "note" }, type: "references" });
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByText("Children (1)")).toBeInTheDocument();
  });

  it("shows parents count when incoming edges exist", () => {
    const store = new MemoryStore();
    setMemoryStore(store);
    store.graph.addNode({ id: "node-1", type: "test", subtype: "test:sub", title: "Inspected Node", summary: "Node summary for inspector", source: "test" });
    store.graph.addNode({ id: "parent-1", type: "note", subtype: "note", title: "Parent Node", summary: "", source: "test" });
    store.graph.addEdge({ sourceNodeId: { value: "parent-1", type: "note" }, targetNodeId: { value: "node-1", type: "test" }, type: "references" });
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByText("Parents (1)")).toBeInTheDocument();
  });
});
