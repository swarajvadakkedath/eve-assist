import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MessageAvatar from "./MessageAvatar";

describe("MessageAvatar", () => {
  it("renders user avatar", () => {
    render(<MessageAvatar role="user" />);
    expect(screen.getByText("U")).toBeInTheDocument();
  });

  it("renders assistant avatar", () => {
    render(<MessageAvatar role="assistant" />);
    expect(screen.getByText("E")).toBeInTheDocument();
  });

  it("renders system avatar", () => {
    render(<MessageAvatar role="system" />);
    expect(screen.getByText("S")).toBeInTheDocument();
  });

  it("applies user class for user role", () => {
    const { container } = render(<MessageAvatar role="user" />);
    expect(container.firstChild).toHaveClass("pr-msg-avatar-user");
  });

  it("applies assistant class for assistant role", () => {
    const { container } = render(<MessageAvatar role="assistant" />);
    expect(container.firstChild).toHaveClass("pr-msg-avatar-assistant");
  });
});
