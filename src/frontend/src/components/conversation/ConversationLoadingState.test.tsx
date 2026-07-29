import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ConversationLoadingState from "./ConversationLoadingState";

describe("ConversationLoadingState", () => {
  it("renders loading status", () => {
    render(<ConversationLoadingState />);
    expect(screen.getByRole("status")).toHaveAttribute("aria-label", "Loading messages");
  });

  it("renders skeleton elements", () => {
    const { container } = render(<ConversationLoadingState />);
    const skeletons = container.querySelectorAll(".pr-conv-loading-skeleton");
    expect(skeletons).toHaveLength(3);
  });
});
