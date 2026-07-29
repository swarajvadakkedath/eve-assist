import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Badge from "./Badge";

describe("Badge", () => {
  it("renders children", () => {
    render(<Badge>New</Badge>);
    expect(screen.getByText("New")).toBeInTheDocument();
  });

  it("has role status", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("applies default variant class", () => {
    render(<Badge>Default</Badge>);
    expect(screen.getByRole("status").className).toContain("pr-badge-default");
  });

  it("applies success variant class", () => {
    render(<Badge variant="success">Done</Badge>);
    expect(screen.getByRole("status").className).toContain("pr-badge-success");
  });

  it("applies warning variant class", () => {
    render(<Badge variant="warning">Pending</Badge>);
    expect(screen.getByRole("status").className).toContain("pr-badge-warning");
  });

  it("applies error variant class", () => {
    render(<Badge variant="error">Failed</Badge>);
    expect(screen.getByRole("status").className).toContain("pr-badge-error");
  });

  it("applies info variant class", () => {
    render(<Badge variant="info">Info</Badge>);
    expect(screen.getByRole("status").className).toContain("pr-badge-info");
  });

  it("applies md size by default", () => {
    render(<Badge>Medium</Badge>);
    expect(screen.getByRole("status").className).toContain("pr-badge-md");
  });

  it("applies sm size class", () => {
    render(<Badge size="sm">Small</Badge>);
    expect(screen.getByRole("status").className).toContain("pr-badge-sm");
  });

  it("applies custom className", () => {
    render(<Badge className="custom">Tag</Badge>);
    expect(screen.getByText("Tag").className).toContain("custom");
  });
});
