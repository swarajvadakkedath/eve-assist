import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExecutionLogs from "./ExecutionLogs";

const logs = [
  { timestamp: "2024-01-15T10:00:00Z", level: "info" as const, message: "Started" },
  { timestamp: "2024-01-15T10:01:00Z", level: "warn" as const, message: "Warning message" },
  { timestamp: "2024-01-15T10:02:00Z", level: "error" as const, message: "Error occurred" },
];

describe("ExecutionLogs", () => {
  it("renders log count in toggle", () => {
    render(<ExecutionLogs logs={logs} />);
    expect(screen.getByText("Logs (3)")).toBeInTheDocument();
  });

  it("expands logs on toggle click", async () => {
    render(<ExecutionLogs logs={logs} defaultCollapsed />);
    expect(screen.queryByText("Started")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Logs (3)"));
    expect(screen.getByText("Started")).toBeInTheDocument();
  });

  it("renders log levels", async () => {
    render(<ExecutionLogs logs={logs} defaultCollapsed={false} />);
    expect(screen.getByText("INFO")).toBeInTheDocument();
    expect(screen.getByText("WARN")).toBeInTheDocument();
    expect(screen.getByText("ERROR")).toBeInTheDocument();
  });

  it("renders copy button when expanded", () => {
    render(<ExecutionLogs logs={logs} defaultCollapsed={false} />);
    expect(screen.getByRole("button", { name: "Copy logs" })).toBeInTheDocument();
  });

  it("toggles aria-expanded", () => {
    render(<ExecutionLogs logs={logs} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });
});
