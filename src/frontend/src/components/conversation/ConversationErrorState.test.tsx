import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ConversationErrorState from "./ConversationErrorState";

describe("ConversationErrorState", () => {
  it("renders error message", () => {
    render(<ConversationErrorState error="Something went wrong" />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("has alert role", () => {
    render(<ConversationErrorState error="Error" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("renders retry button when handler provided", () => {
    render(<ConversationErrorState error="Error" onRetry={vi.fn()} />);
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("calls onRetry when retry clicked", async () => {
    const onRetry = vi.fn();
    render(<ConversationErrorState error="Error" onRetry={onRetry} />);
    await userEvent.click(screen.getByText("Retry"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("does not render retry button without handler", () => {
    render(<ConversationErrorState error="Error" />);
    expect(screen.queryByText("Retry")).not.toBeInTheDocument();
  });
});
