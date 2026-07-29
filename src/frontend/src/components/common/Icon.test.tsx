import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Icon from "./Icon";

describe("Icon", () => {
  it("renders children", () => {
    render(<Icon><svg data-testid="svg" /></Icon>);
    expect(screen.getByTestId("svg")).toBeInTheDocument();
  });

  it("has aria-hidden by default", () => {
    const { container } = render(<Icon><svg /></Icon>);
    expect(container.querySelector(".pr-icon")).toHaveAttribute("aria-hidden", "true");
  });

  it("has role img when label is provided", () => {
    render(<Icon label="Close"><svg /></Icon>);
    const icon = screen.getByRole("img");
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute("aria-label", "Close");
  });

  it("applies default size", () => {
    const { container } = render(<Icon><svg /></Icon>);
    expect(container.querySelector(".pr-icon")).toHaveStyle("width: 16px");
    expect(container.querySelector(".pr-icon")).toHaveStyle("height: 16px");
  });

  it("applies custom size", () => {
    const { container } = render(<Icon size={24}><svg /></Icon>);
    expect(container.querySelector(".pr-icon")).toHaveStyle("width: 24px");
    expect(container.querySelector(".pr-icon")).toHaveStyle("height: 24px");
  });

  it("applies custom className", () => {
    const { container } = render(<Icon className="custom-icon"><svg /></Icon>);
    expect(container.querySelector(".custom-icon")).toBeInTheDocument();
  });
});
