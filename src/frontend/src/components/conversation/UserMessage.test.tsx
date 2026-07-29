import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import UserMessage from "./UserMessage";
import type { Message } from "./types";

const baseMessage: Message = {
  id: "1",
  conversation_id: "conv-1",
  role: "user",
  content: "Hello!",
  timestamp: "2024-01-15T10:30:00Z",
  tokens_used: 0,
  attachments: [],
  metadata: {},
};

describe("UserMessage", () => {
  it("renders user content", () => {
    render(<UserMessage message={baseMessage} />);
    expect(screen.getByText("Hello!")).toBeInTheDocument();
  });

  it("renders user avatar", () => {
    render(<UserMessage message={baseMessage} />);
    expect(screen.getByText("U")).toBeInTheDocument();
  });

  it("applies user class", () => {
    const { container } = render(<UserMessage message={baseMessage} />);
    expect(container.firstChild).toHaveClass("pr-msg-user");
  });
});
