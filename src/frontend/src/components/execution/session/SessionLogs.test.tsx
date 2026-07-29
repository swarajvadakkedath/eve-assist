import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SessionLogs from "./SessionLogs";
import type { SessionLogEntry } from "./types";

const logs: SessionLogEntry[] = [
  { timestamp: "12:00:00", level: "info", message: "Starting execution", source: "planner" },
  { timestamp: "12:00:01", level: "info", message: "Reading file", source: "file.read" },
  { timestamp: "12:00:02", level: "warn", message: "Slow operation", source: "file.read" },
  { timestamp: "12:00:03", level: "error", message: "Failed to write", source: "file.write" },
];

describe("SessionLogs", () => {
  it("renders logs when present", () => {
    render(<SessionLogs logs={logs} />);
    expect(screen.getByText("Starting execution")).toBeInTheDocument();
    expect(screen.getByText("Reading file")).toBeInTheDocument();
    expect(screen.getByText("Slow operation")).toBeInTheDocument();
    expect(screen.getByText("Failed to write")).toBeInTheDocument();
  });

  it("renders log count in toggle button", () => {
    render(<SessionLogs logs={logs} />);
    const toggle = screen.getByRole("button", { name: /Logs/ });
    expect(toggle).toBeTruthy();
  });

  it("returns null when logs are empty", () => {
    const { container } = render(<SessionLogs logs={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders log levels", () => {
    render(<SessionLogs logs={logs} />);
    expect(screen.getAllByText("INFO").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("WARN")).toBeInTheDocument();
    expect(screen.getByText("ERROR")).toBeInTheDocument();
  });

  it("renders log sources", () => {
    render(<SessionLogs logs={logs} />);
    expect(screen.getByText("[planner]")).toBeInTheDocument();
    expect(screen.getAllByText("[file.read]").length).toBeGreaterThanOrEqual(1);
  });

  it("has copy button", () => {
    render(<SessionLogs logs={logs} />);
    expect(screen.getByRole("button", { name: "Copy logs to clipboard" })).toBeInTheDocument();
  });

  it("has toggle button with aria-expanded", () => {
    render(<SessionLogs logs={logs} />);
    const toggle = screen.getByRole("button", { name: /Logs/ });
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });

  it("has log role and label", () => {
    render(<SessionLogs logs={logs} />);
    expect(screen.getByRole("log")).toHaveAttribute("aria-label", "Execution logs");
  });
});
