import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Timestamp from "./Timestamp";

describe("Timestamp", () => {
  it("renders time from ISO string", () => {
    const { container } = render(<Timestamp timestamp="2024-01-15T10:30:00Z" />);
    expect(container.querySelector(".pr-msg-timestamp")).toBeInTheDocument();
    expect(container.querySelector(".pr-msg-timestamp")?.textContent).toBeTruthy();
  });

  it("renders tokens when provided", () => {
    render(<Timestamp timestamp="2024-01-15T10:30:00Z" tokens={42} />);
    expect(screen.getByText(/42 tokens/)).toBeInTheDocument();
  });

  it("renders nothing when no timestamp or tokens", () => {
    const { container } = render(<Timestamp timestamp="" tokens={0} />);
    expect(container.firstChild).toBeNull();
  });
});
