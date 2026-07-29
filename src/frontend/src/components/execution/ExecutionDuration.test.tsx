import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import ExecutionDuration from "./ExecutionDuration";

describe("ExecutionDuration", () => {
  it("renders duration in seconds", () => {
    const { container } = render(<ExecutionDuration durationMs={5000} />);
    expect(container.textContent).toMatch(/5s/);
  });

  it("renders duration in minutes:seconds", () => {
    const { container } = render(<ExecutionDuration durationMs={125000} />);
    expect(container.textContent).toMatch(/2m 5s/);
  });

  it("renders duration from completedAt - startedAt", () => {
    const { container } = render(
      <ExecutionDuration
        startedAt="2024-01-15T10:00:00Z"
        completedAt="2024-01-15T10:05:30Z"
      />,
    );
    expect(container.textContent).toMatch(/5m 30s/);
  });

  it("renders live counter when running", () => {
    const { container } = render(
      <ExecutionDuration startedAt={new Date().toISOString()} running />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("returns null with no time data", () => {
    const { container } = render(<ExecutionDuration />);
    expect(container.firstChild).toBeNull();
  });
});
