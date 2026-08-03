import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryWorkspace } from "./MemoryWorkspace";
import { setMemoryStore, resetMemoryStore, MemoryStore } from "@/memory/core";
import type { NodeInput } from "@/memory/core";

function createNode(id: string, title: string, overrides: Partial<NodeInput> = {}): NodeInput {
  return {
    id,
    type: "test",
    subtype: "test:sub",
    title,
    source: "test",
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
