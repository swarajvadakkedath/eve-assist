import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SystemMessage from "./SystemMessage";
import type { Message } from "./types";

const baseMessage: Message = {
  id: "1",
  conversation_id: "conv-1",
  role: "system",
  content: "System notice",
  timestamp: "2024-01-15T10:30:00Z",
  tokens_used: 0,
  attachments: [],
  metadata: {},
};

describe("SystemMessage", () => {
  it("renders system content", () => {
    render(<SystemMessage message={baseMessage} />);
    expect(screen.getByText("System notice")).toBeInTheDocument();
  });

  it("applies system class", () => {
    const { container } = render(<SystemMessage message={baseMessage} />);
    expect(container.firstChild).toHaveClass("pr-msg-system");
  });
});
