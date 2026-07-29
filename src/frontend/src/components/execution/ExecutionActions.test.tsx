import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ExecutionActions from "./ExecutionActions";
import type { Action } from "./ExecutionActions";

const actions: Action[] = [
  { id: "pause", label: "Pause", onClick: vi.fn() },
  { id: "cancel", label: "Cancel", variant: "danger", onClick: vi.fn() },
];

describe("ExecutionActions", () => {
  it("renders all action buttons", () => {
    render(<ExecutionActions actions={actions} />);
    expect(screen.getByText("Pause")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<ExecutionActions actions={[{ id: "test", label: "Test", onClick }]} />);
    await userEvent.click(screen.getByText("Test"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("disables button when disabled", () => {
    render(<ExecutionActions actions={[{ id: "test", label: "Test", onClick: vi.fn(), disabled: true }]} />);
    expect(screen.getByText("Test").closest("button")).toBeDisabled();
  });

  it("returns null with empty actions", () => {
    const { container } = render(<ExecutionActions actions={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
