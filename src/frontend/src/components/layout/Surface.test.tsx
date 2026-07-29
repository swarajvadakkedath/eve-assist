import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Surface from "./Surface";

describe("Surface", () => {
  it("renders children", () => {
    render(<Surface>Content</Surface>);
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("applies primary variant class by default", () => {
    const { container } = render(<Surface>Content</Surface>);
    expect(container.firstElementChild?.className).toContain("pr-surface");
  });

  it("applies secondary variant class", () => {
    const { container } = render(<Surface variant="secondary">Content</Surface>);
    expect(container.firstElementChild?.className).toContain("pr-surface-secondary");
  });

  it("applies elevated variant class", () => {
    const { container } = render(<Surface variant="elevated">Content</Surface>);
    expect(container.firstElementChild?.className).toContain("pr-surface-elevated");
  });

  it("applies floating variant class", () => {
    const { container } = render(<Surface variant="floating">Content</Surface>);
    expect(container.firstElementChild?.className).toContain("pr-surface-floating");
  });

  it("applies panel variant class", () => {
    const { container } = render(<Surface variant="panel">Content</Surface>);
    expect(container.firstElementChild?.className).toContain("pr-surface-panel");
  });

  it("applies custom className", () => {
    const { container } = render(<Surface className="custom">Content</Surface>);
    expect(container.firstElementChild?.className).toContain("custom");
  });
});
