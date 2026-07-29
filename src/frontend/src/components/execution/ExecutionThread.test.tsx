import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionThread from "./ExecutionThread";
import type { ExecutionNode as NodeData } from "./types";

const nodes: NodeData[] = [
  { id: "1", capability: "search", label: "Search files", status: "completed" },
  { id: "2", capability: "read", label: "Read PDF", status: "completed" },
  { id: "3", capability: "extract", label: "Extract tables", status: "running" },
];

describe("ExecutionThread", () => {
  it("renders all nodes", () => {
    render(<ExecutionThread nodes={nodes} />);
    expect(screen.getByText("Search files")).toBeInTheDocument();
    expect(screen.getByText("Read PDF")).toBeInTheDocument();
    expect(screen.getByText("Extract tables")).toBeInTheDocument();
  });

  it("has list role", () => {
    render(<ExecutionThread nodes={nodes} />);
    expect(screen.getByRole("list")).toBeInTheDocument();
  });

  it("has correct number of listitems", () => {
    render(<ExecutionThread nodes={nodes} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
  });

  it("returns null for empty nodes", () => {
    const { container } = render(<ExecutionThread nodes={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("marks last node", () => {
    const { container } = render(<ExecutionThread nodes={nodes} />);
    const items = container.querySelectorAll(".pr-exec-node");
    expect(items[2]).toHaveClass("pr-exec-node-last");
  });
});
