import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusBar from "./StatusBar";

describe("StatusBar", () => {
  it("renders items with labels", () => {
    render(<StatusBar items={[{ id: "conn", label: "Connected" }]} />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("renders status landmark", () => {
    render(<StatusBar items={[{ id: "s", label: "OK" }]} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders dot indicator when provided", () => {
    const { container } = render(
      <StatusBar items={[{ id: "s", label: "Running", dot: "green" }]} />,
    );
    expect(container.querySelector(".pr-statusbar-dot")).toBeInTheDocument();
  });

  it("renders left content", () => {
    render(<StatusBar left={<span data-testid="left" />} />);
    expect(screen.getByTestId("left")).toBeInTheDocument();
  });

  it("renders right content", () => {
    render(<StatusBar right={<span data-testid="right" />} />);
    expect(screen.getByTestId("right")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(<StatusBar className="custom" />);
    expect(container.firstElementChild?.className).toContain("custom");
  });
});
