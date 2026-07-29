import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ResizableLayout from "./ResizableLayout";

describe("ResizableLayout", () => {
  it("renders sidebar and children", () => {
    render(
      <ResizableLayout sidebar={<nav data-testid="sidebar" />}>
        <main data-testid="content" />
      </ResizableLayout>,
    );
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });

  it("renders resize separator", () => {
    render(
      <ResizableLayout sidebar={<aside />}>
        <div />
      </ResizableLayout>,
    );
    expect(screen.getByRole("separator")).toBeInTheDocument();
  });

  it("applies collapsed class when collapsed", () => {
    const { container } = render(
      <ResizableLayout sidebar={<aside />} collapsed>
        <div />
      </ResizableLayout>,
    );
    expect(container.querySelector(".pr-sidebar-collapsed")).toBeInTheDocument();
  });

  it("applies expanded class when not collapsed", () => {
    const { container } = render(
      <ResizableLayout sidebar={<aside />}>
        <div />
      </ResizableLayout>,
    );
    expect(container.querySelector(".pr-sidebar-expanded")).toBeInTheDocument();
  });

  it("does not render resize handle when not collapsible", () => {
    render(
      <ResizableLayout sidebar={<aside />} collapsible={false}>
        <div />
      </ResizableLayout>,
    );
    expect(screen.queryByRole("separator")).not.toBeInTheDocument();
  });

  it("renders group role with label", () => {
    render(
      <ResizableLayout sidebar={<aside />}>
        <div />
      </ResizableLayout>,
    );
    expect(screen.getByRole("group")).toHaveAttribute("aria-label", "Resizable layout");
  });
});
