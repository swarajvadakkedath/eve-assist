import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Panel from "./Panel";

describe("Panel", () => {
  it("renders children", () => {
    render(<Panel>Body</Panel>);
    expect(screen.getByText("Body")).toBeInTheDocument();
  });

  it("renders header when provided", () => {
    render(<Panel header="Header">Body</Panel>);
    expect(screen.getByText("Header")).toBeInTheDocument();
  });

  it("renders footer when provided", () => {
    render(<Panel footer="Footer">Body</Panel>);
    expect(screen.getByText("Footer")).toBeInTheDocument();
  });

  it("applies panel class", () => {
    const { container } = render(<Panel>Body</Panel>);
    expect(container.firstElementChild?.className).toContain("pr-panel");
  });

  it("applies custom className", () => {
    const { container } = render(<Panel className="custom">Body</Panel>);
    expect(container.firstElementChild?.className).toContain("custom");
  });
});
