import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PermissionCard from "./PermissionCard";
import type { PermissionRequest } from "./types";

const permission: PermissionRequest = {
  id: "perm-1",
  capability: "file.write",
  description: "Eve wants to modify files in Documents",
  level: 2,
};

describe("PermissionCard", () => {
  it("renders title", () => {
    render(<PermissionCard permission={permission} onAllowOnce={vi.fn()} onAlwaysAllow={vi.fn()} onDeny={vi.fn()} />);
    expect(screen.getByText("Permission Required")).toBeInTheDocument();
  });

  it("renders description", () => {
    render(<PermissionCard permission={permission} onAllowOnce={vi.fn()} onAlwaysAllow={vi.fn()} onDeny={vi.fn()} />);
    expect(screen.getByText(/Eve wants to modify files/)).toBeInTheDocument();
  });

  it("renders all three action buttons", () => {
    render(<PermissionCard permission={permission} onAllowOnce={vi.fn()} onAlwaysAllow={vi.fn()} onDeny={vi.fn()} />);
    expect(screen.getByText("Allow Once")).toBeInTheDocument();
    expect(screen.getByText("Always Allow")).toBeInTheDocument();
    expect(screen.getByText("Deny")).toBeInTheDocument();
  });

  it("calls onAllowOnce when clicked", async () => {
    const onAllowOnce = vi.fn();
    render(<PermissionCard permission={permission} onAllowOnce={onAllowOnce} onAlwaysAllow={vi.fn()} onDeny={vi.fn()} />);
    await userEvent.click(screen.getByText("Allow Once"));
    expect(onAllowOnce).toHaveBeenCalledTimes(1);
  });

  it("calls onDeny when clicked", async () => {
    const onDeny = vi.fn();
    render(<PermissionCard permission={permission} onAllowOnce={vi.fn()} onAlwaysAllow={vi.fn()} onDeny={onDeny} />);
    await userEvent.click(screen.getByText("Deny"));
    expect(onDeny).toHaveBeenCalledTimes(1);
  });

  it("has alertdialog role", () => {
    render(<PermissionCard permission={permission} onAllowOnce={vi.fn()} onAlwaysAllow={vi.fn()} onDeny={vi.fn()} />);
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
  });
});
