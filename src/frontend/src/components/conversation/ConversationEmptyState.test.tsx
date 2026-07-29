import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConversationEmptyState from "./ConversationEmptyState";

describe("ConversationEmptyState", () => {
  it("renders welcome heading", () => {
    render(<ConversationEmptyState />);
    expect(screen.getByText("Welcome to Eve")).toBeInTheDocument();
  });

  it("renders shortcut hints", () => {
    render(<ConversationEmptyState />);
    expect(screen.getByText("Ctrl+K — Command Palette")).toBeInTheDocument();
    expect(screen.getByText("Enter — Send")).toBeInTheDocument();
  });

  it("renders new conversation button when handler provided", () => {
    render(<ConversationEmptyState onNewConversation={vi.fn()} />);
    expect(screen.getByText("New Conversation")).toBeInTheDocument();
  });

  it("calls onNewConversation when button clicked", async () => {
    const onNew = vi.fn();
    render(<ConversationEmptyState onNewConversation={onNew} />);
    await userEvent.click(screen.getByText("New Conversation"));
    expect(onNew).toHaveBeenCalledTimes(1);
  });

  it("does not render button without handler", () => {
    render(<ConversationEmptyState />);
    expect(screen.queryByText("New Conversation")).not.toBeInTheDocument();
  });
});
