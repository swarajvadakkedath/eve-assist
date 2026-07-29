import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Card from "./Card";

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Content</Card>);
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("applies outlined variant by default", () => {
    render(<Card>Content</Card>);
    expect(screen.getByText("Content").className).toContain("pr-card-outlined");
  });

  it("applies elevated variant class", () => {
    render(<Card variant="elevated">Content</Card>);
    expect(screen.getByText("Content").className).toContain("pr-card-elevated");
  });

  it("applies filled variant class", () => {
    render(<Card variant="filled">Content</Card>);
    expect(screen.getByText("Content").className).toContain("pr-card-filled");
  });

  it("applies md padding by default", () => {
    render(<Card>Content</Card>);
    expect(screen.getByText("Content").className).toContain("pr-card-padding-md");
  });

  it("applies custom padding class", () => {
    render(<Card padding="lg">Content</Card>);
    expect(screen.getByText("Content").className).toContain("pr-card-padding-lg");
  });

  it("applies custom className", () => {
    render(<Card className="custom-card">Content</Card>);
    expect(screen.getByText("Content").className).toContain("custom-card");
  });
});
