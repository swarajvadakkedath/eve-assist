import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import StreamingCursor from "./StreamingCursor";

describe("StreamingCursor", () => {
  it("renders cursor by default", () => {
    const { container } = render(<StreamingCursor />);
    expect(container.firstChild).toHaveClass("pr-streaming-cursor");
  });

  it("renders cursor when visible", () => {
    const { container } = render(<StreamingCursor visible />);
    expect(container.firstChild).toHaveClass("pr-streaming-cursor");
  });

  it("does not render when visible is false", () => {
    const { container } = render(<StreamingCursor visible={false} />);
    expect(container.firstChild).toBeNull();
  });
});
