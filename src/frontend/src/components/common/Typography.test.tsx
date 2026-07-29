import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Typography from "./Typography";

describe("Typography", () => {
  it("renders children", () => {
    render(<Typography>Hello</Typography>);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders paragraph by default", () => {
    render(<Typography>Text</Typography>);
    expect(screen.getByText("Text").tagName).toBe("P");
  });

  it("renders h1 with variant prop", () => {
    render(<Typography variant="h1">Heading</Typography>);
    expect(screen.getByText("Heading").tagName).toBe("H1");
  });

  it("renders h2 with variant prop", () => {
    render(<Typography variant="h2">Heading 2</Typography>);
    expect(screen.getByText("Heading 2").tagName).toBe("H2");
  });

  it("renders custom as prop", () => {
    render(<Typography as="div">Div text</Typography>);
    expect(screen.getByText("Div text").tagName).toBe("DIV");
  });

  it("renders label variant as span", () => {
    render(<Typography variant="label">Label</Typography>);
    expect(screen.getByText("Label").tagName).toBe("SPAN");
  });

  it("renders caption variant as span", () => {
    render(<Typography variant="caption">Caption</Typography>);
    expect(screen.getByText("Caption").tagName).toBe("SPAN");
  });

  it("applies color style when color prop is provided", () => {
    render(<Typography color="accent">Colored</Typography>);
    expect(screen.getByText("Colored")).toHaveStyle("color: var(--accent)");
  });

  it("applies color style for error", () => {
    render(<Typography color="error">Error text</Typography>);
    expect(screen.getByText("Error text")).toHaveStyle("color: var(--error)");
  });

  it("merges custom style", () => {
    render(<Typography style={{ marginTop: 8 }}>Styled</Typography>);
    expect(screen.getByText("Styled")).toHaveStyle("margin-top: 8px");
  });

  it("applies font-size from variant", () => {
    render(<Typography variant="h1">Big</Typography>);
    expect(screen.getByText("Big")).toHaveStyle("font-size: var(--text-3xl)");
  });

  it("forwards additional props", () => {
    render(<Typography data-testid="typo">Test</Typography>);
    expect(screen.getByTestId("typo")).toBeInTheDocument();
  });
});
