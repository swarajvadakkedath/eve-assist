import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AppShell from "./AppShell";

describe("AppShell", () => {
  it("renders sidebar and children", () => {
    render(
      <AppShell sidebar={<nav data-testid="sidebar" />}>
        <main data-testid="content" />
      </AppShell>,
    );
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });

  it("applies app-shell class", () => {
    const { container } = render(
      <AppShell sidebar={<aside />}><div /></AppShell>,
    );
    expect(container.firstElementChild?.className).toContain("pr-app-shell");
  });

  it("applies custom className", () => {
    const { container } = render(
      <AppShell sidebar={<aside />} className="custom"><div /></AppShell>,
    );
    expect(container.firstElementChild?.className).toContain("custom");
  });
});
