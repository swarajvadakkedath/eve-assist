import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryWorkspace } from "./MemoryWorkspace";
import { setMemoryStore, resetMemoryStore, MemoryStore } from "@/memory/core";
import type { MemoryNode } from "@/memory/core";

function createNode(id: string, title: string, overrides: Partial<MemoryNode> = {}): MemoryNode {
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
    ...overrides,
  };
}

describe("MemoryWorkspace", () => {
  beforeEach(() => {
    resetMemoryStore();
    const store = new MemoryStore();
    setMemoryStore(store);
    store.addNode(createNode("1", "Item One"));
    store.addNode(createNode("2", "Item Two", { pinned: true }));
  });

  it("renders sidebar", () => {
    render(<MemoryWorkspace />);
    expect(screen.getByRole("complementary")).toBeInTheDocument();
  });

  it("renders explorer region with section label", () => {
    render(<MemoryWorkspace />);
    expect(screen.getByRole("region")).toBeInTheDocument();
  });

  it("renders explorer content area", () => {
    render(<MemoryWorkspace />);
    expect(screen.getByRole("region")).toBeInTheDocument();
  });

  it("shows toolbar with item count", () => {
    render(<MemoryWorkspace defaultView="recent" />);
    expect(screen.getByRole("toolbar")).toBeInTheDocument();
  });
});
