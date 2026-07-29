import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import WorkspaceHeader from "./WorkspaceHeader";

describe("WorkspaceHeader", () => {
  it("renders title", () => {
    render(<WorkspaceHeader title="Workspace" />);
    expect(screen.getByText("Workspace")).toBeInTheDocument();
  });

  it("renders controls", () => {
    render(<WorkspaceHeader controls={<button data-testid="ctrl" />} />);
    expect(screen.getByTestId("ctrl")).toBeInTheDocument();
  });

  it("renders status", () => {
    render(<WorkspaceHeader status={<span data-testid="status" />} />);
    expect(screen.getByTestId("status")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<WorkspaceHeader className="custom" />);
    expect(container.firstElementChild?.className).toContain("custom");
  });
});
