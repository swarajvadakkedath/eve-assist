import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ExecutionMetadata from "./ExecutionMetadata";

describe("ExecutionMetadata", () => {
  it("renders metadata items", () => {
    render(<ExecutionMetadata items={[{ label: "Owner", value: "user1" }, { label: "Priority", value: "High" }]} />);
    expect(screen.getByText("Owner")).toBeInTheDocument();
    expect(screen.getByText("user1")).toBeInTheDocument();
    expect(screen.getByText("Priority")).toBeInTheDocument();
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("returns null with empty items", () => {
    const { container } = render(<ExecutionMetadata items={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
