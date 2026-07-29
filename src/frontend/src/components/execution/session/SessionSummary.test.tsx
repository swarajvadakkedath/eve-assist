import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SessionSummary from "./SessionSummary";
import type { SessionResult } from "./types";

const successResult: SessionResult = {
  success: true,
  summary: "Created 3 files · Read 2 PDFs · Completed in 12.4s",
  durationMs: 12400,
  toolCount: 5,
  completedCount: 5,
  failedCount: 0,
  toolsExecuted: ["file.create", "file.read", "search.web"],
  capabilitiesUsed: ["file", "search"],
};

const failedResult: SessionResult = {
  success: false,
  summary: "Some steps failed",
  durationMs: 8400,
  toolCount: 3,
  completedCount: 2,
  failedCount: 1,
  errors: ["file.write: Permission denied"],
};

describe("SessionSummary", () => {
  it("renders success result", () => {
    render(<SessionSummary result={successResult} />);
    expect(screen.getByText("Created 3 files · Read 2 PDFs · Completed in 12.4s")).toBeInTheDocument();
  });

  it("renders duration stat", () => {
    render(<SessionSummary result={successResult} />);
    expect(screen.getByText("Duration")).toBeInTheDocument();
    expect(screen.getByText("12.4s")).toBeInTheDocument();
  });

  it("renders tool count stat", () => {
    render(<SessionSummary result={successResult} />);
    expect(screen.getByText("Tools")).toBeInTheDocument();
    expect(screen.getByText("Duration")).toBeInTheDocument();
    // tool count is "5" in the stat value; there are multiple "5"s, just check existence
    const statValues = screen.getAllByText("5");
    expect(statValues.length).toBeGreaterThanOrEqual(1);
  });

  it("renders completed count", () => {
    render(<SessionSummary result={successResult} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
    const statValues = screen.getAllByText("5");
    expect(statValues.length).toBeGreaterThanOrEqual(1);
  });

  it("renders failed count when > 0", () => {
    render(<SessionSummary result={failedResult} />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
    const values = screen.getAllByText("1");
    expect(values.length).toBeGreaterThanOrEqual(1);
  });

  it("renders capabilities", () => {
    render(<SessionSummary result={successResult} />);
    expect(screen.getByText("file")).toBeInTheDocument();
    expect(screen.getByText("search")).toBeInTheDocument();
  });

  it("renders errors", () => {
    render(<SessionSummary result={failedResult} />);
    expect(screen.getByText("file.write: Permission denied")).toBeInTheDocument();
  });

  it("does not render failed count when 0", () => {
    render(<SessionSummary result={successResult} />);
    expect(screen.queryByText("Failed")).not.toBeInTheDocument();
  });

  it("does not render capabilities when empty", () => {
    const noCaps = { ...successResult, capabilitiesUsed: [] };
    const { container } = render(<SessionSummary result={noCaps} />);
    expect(container.querySelector(".pr-session-summary-capabilities")).not.toBeInTheDocument();
  });
});
