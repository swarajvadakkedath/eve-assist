import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TypingIndicator from "./TypingIndicator";

describe("TypingIndicator", () => {
  it("renders three dots", () => {
    render(<TypingIndicator />);
    const indicator = screen.getByRole("status");
    expect(indicator).toBeInTheDocument();
    expect(indicator.children).toHaveLength(3);
  });

  it("has aria-label", () => {
    render(<TypingIndicator />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Assistant is typing");
  });

  it("does not render when visible is false", () => {
    const { container } = render(<TypingIndicator visible={false} />);
    expect(container.firstChild).toBeNull();
  });
});
