import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryPreview } from "./MemoryPreview";
import type { MemoryNode } from "@/memory/core";

const mockNode: MemoryNode = {
  id: { value: "node-1", type: "test" },
  type: "test",
  subtype: "test:sub",
  title: "Test Node Preview",
  summary: "This is a summary of the test node",
  createdAt: 1000000,
  updatedAt: 2000000,
  lastAccessed: 3000000,
  source: "manual",
  metadata: {},
  tags: ["tag-a", "tag-b"],
  importance: 0.8,
  confidence: 0.9,
  accessCount: 5,
  pinned: true,
  archived: false,
  verified: true,
  verificationMethod: "manual",
  status: "active",
};

describe("MemoryPreview", () => {
  it("renders node title", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("Test Node Preview")).toBeInTheDocument();
  });

  it("renders node type", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("test:sub")).toBeInTheDocument();
  });

  it("renders source", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("manual")).toBeInTheDocument();
  });

  it("renders status", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("active")).toBeInTheDocument();
  });

  it("renders pinned status", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("Yes")).toBeInTheDocument();
  });

  it("renders verification status", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("Yes (manual)")).toBeInTheDocument();
  });

  it("renders summary", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("This is a summary of the test node")).toBeInTheDocument();
  });

  it("renders tags", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("tag-a")).toBeInTheDocument();
    expect(screen.getByText("tag-b")).toBeInTheDocument();
  });

  it("renders No for archived when not archived", () => {
    render(<MemoryPreview node={mockNode} />);
    expect(screen.getByText("No")).toBeInTheDocument();
  });
});
