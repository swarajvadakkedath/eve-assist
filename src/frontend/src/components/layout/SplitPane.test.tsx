import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SplitPane from "./SplitPane";

describe("SplitPane", () => {
  it("renders two children", () => {
    render(
      <SplitPane>
        <div data-testid="left" />
        <div data-testid="right" />
      </SplitPane>,
    );
    expect(screen.getByTestId("left")).toBeInTheDocument();
    expect(screen.getByTestId("right")).toBeInTheDocument();
  });

  it("renders horizontal direction by default", () => {
    const { container } = render(
      <SplitPane>
        <div />
        <div />
      </SplitPane>,
    );
    expect(container.firstElementChild?.className).toContain("pr-split-pane-horizontal");
  });

  it("renders vertical direction", () => {
    const { container } = render(
      <SplitPane direction="vertical">
        <div />
        <div />
      </SplitPane>,
    );
    expect(container.firstElementChild?.className).toContain("pr-split-pane-vertical");
  });

  it("renders a gutter separator", () => {
    render(
      <SplitPane>
        <div />
        <div />
      </SplitPane>,
    );
    expect(screen.getByRole("separator")).toBeInTheDocument();
  });

  it("uses aria-label on group", () => {
    render(
      <SplitPane>
        <div />
        <div />
      </SplitPane>,
    );
    expect(screen.getByRole("group")).toHaveAttribute("aria-label", "Split pane");
  });
});
