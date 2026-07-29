import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ActivityBadge from "./ActivityBadge";

describe("ActivityBadge", () => {
  it("renders with count", () => {
    render(<ActivityBadge status="completed" count={5} />);
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Done")).toBeInTheDocument();
  });

  it("renders with dot when no count", () => {
    const { container } = render(<ActivityBadge status="running" />);
    expect(container.querySelector(".pr-activity-badge-dot")).toBeInTheDocument();
    expect(screen.getByText("Running")).toBeInTheDocument();
  });

  it("has status role", () => {
    render(<ActivityBadge status="failed" count={1} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders correct label for each status", () => {
    const cases: [string, string][] = [
      ["planning", "Planning"],
      ["running", "Running"],
      ["waiting", "Waiting"],
      ["permission", "Permission"],
      ["retrying", "Retrying"],
      ["paused", "Paused"],
      ["completed", "Done"],
      ["failed", "Failed"],
      ["cancelled", "Cancelled"],
      ["background", "BG"],
    ];
    for (const [status, label] of cases) {
      const { unmount } = render(<ActivityBadge status={status as any} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });
});
