import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemorySearch } from "./MemorySearch";
import { setMemoryStore, resetMemoryStore, MemoryStore } from "@/memory/core";
import type { MemoryNode, SearchQuery, SearchResult } from "@/memory/core";

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

describe("MemorySearch", () => {
  beforeEach(() => {
    resetMemoryStore();
    const store = new MemoryStore();
    setMemoryStore(store);
    store.addNode(createNode("1", "Payment API Documentation"));
    store.addNode(createNode("2", "Authentication Module"));
    store.addNode(createNode("3", "Database Schema"));
  });

  it("renders search input", () => {
    render(<MemorySearch />);
    expect(screen.getByLabelText("Search memory")).toBeInTheDocument();
  });

  it("shows placeholder text when no query", () => {
    render(<MemorySearch />);
    expect(screen.getByText("Type to search memory nodes")).toBeInTheDocument();
  });

  it("renders clear button when query entered", async () => {
    render(<MemorySearch />);
    const input = screen.getByLabelText("Search memory");
    await userEvent.type(input, "test");
    expect(screen.getByLabelText("Clear search")).toBeInTheDocument();
  });

  it("clears search when clear button clicked", async () => {
    render(<MemorySearch />);
    const input = screen.getByLabelText("Search memory");
    await userEvent.type(input, "test");
    await userEvent.click(screen.getByLabelText("Clear search"));
    expect(input).toHaveValue("");
  });

  it("renders with search role", () => {
    render(<MemorySearch />);
    expect(screen.getByRole("search")).toBeInTheDocument();
  });
});
