import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionNode from "./ExecutionNode";
import type { ExecutionNode as NodeData } from "./types";

const baseNode: NodeData = {
  id: "1",
  capability: "file.read",
  label: "Read config file",
  status: "completed",
};

describe("ExecutionNode", () => {
  it("renders node label", () => {
    render(<ExecutionNode node={baseNode} />);
    expect(screen.getByText("Read config file")).toBeInTheDocument();
  });

  it("renders with aria label", () => {
    render(<ExecutionNode node={baseNode} />);
    expect(screen.getByRole("listitem")).toHaveAttribute("aria-label", "Read config file: Completed");
  });

  it("shows error text when failed", () => {
    render(<ExecutionNode node={{ ...baseNode, status: "failed", error: "File not found" }} />);
    expect(screen.getByText("File not found")).toBeInTheDocument();
  });

  it("shows progress when provided", () => {
    const { container } = render(
      <ExecutionNode
        node={{ ...baseNode, status: "running", progress: { type: "indeterminate" } }}
      />,
    );
    expect(container.querySelector(".pr-exec-progress")).toBeInTheDocument();
  });

  it("applies completed class", () => {
    const { container } = render(<ExecutionNode node={baseNode} />);
    expect(container.firstChild).toHaveClass("pr-exec-node-completed");
  });

  it("applies running class", () => {
    const { container } = render(<ExecutionNode node={{ ...baseNode, status: "running" }} />);
    expect(container.firstChild).toHaveClass("pr-exec-node-running");
  });

  it("marks last node", () => {
    const { container } = render(<ExecutionNode node={baseNode} isLast />);
    expect(container.firstChild).toHaveClass("pr-exec-node-last");
  });
});
