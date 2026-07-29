import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Workspace from "./Workspace";

describe("Workspace", () => {
  it("renders children", () => {
    render(<Workspace><main data-testid="content" /></Workspace>);
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });

  it("renders header when provided", () => {
    render(<Workspace header={<header data-testid="header" />}><div /></Workspace>);
    expect(screen.getByTestId("header")).toBeInTheDocument();
  });

  it("shows loading state", () => {
    render(<Workspace loading><div data-testid="content" /></Workspace>);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByTestId("content")).not.toBeInTheDocument();
  });

  it("shows empty state when empty", () => {
    render(<Workspace empty emptyMessage="Nothing here" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("shows default empty message", () => {
    render(<Workspace empty />);
    expect(screen.getByText("No content")).toBeInTheDocument();
  });

  it("renders footer when provided", () => {
    render(<Workspace footer={<footer data-testid="footer" />}><div /></Workspace>);
    expect(screen.getByTestId("footer")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<Workspace className="custom"><div /></Workspace>);
    expect(container.firstElementChild?.className).toContain("custom");
  });
});
