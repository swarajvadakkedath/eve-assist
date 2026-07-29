import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TopBar from "./TopBar";

describe("TopBar", () => {
  it("renders title", () => {
    render(<TopBar title="Dashboard" />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders as banner landmark", () => {
    render(<TopBar title="Test" />);
    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  it("renders controls", () => {
    render(<TopBar controls={<button data-testid="ctrl" />} />);
    expect(screen.getByTestId("ctrl")).toBeInTheDocument();
  });

  it("renders status", () => {
    render(<TopBar status={<span data-testid="status" />} />);
    expect(screen.getByTestId("status")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<TopBar className="custom" />);
    expect(container.firstElementChild?.className).toContain("custom");
  });
});
