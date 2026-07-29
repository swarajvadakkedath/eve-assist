import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RecoveryCard from "./RecoveryCard";

describe("RecoveryCard", () => {
  it("renders error message", () => {
    render(<RecoveryCard error="Connection timeout" onRetry={vi.fn()} />);
    expect(screen.getByText("Connection timeout")).toBeInTheDocument();
  });

  it("renders retry button", () => {
    render(<RecoveryCard error="Error" onRetry={vi.fn()} />);
    expect(screen.getByText("Retry Step")).toBeInTheDocument();
  });

  it("renders all optional buttons when provided", () => {
    render(<RecoveryCard error="Error" onRetry={vi.fn()} onRetryAll={vi.fn()} onContinue={vi.fn()} onSkip={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText("Retry Step")).toBeInTheDocument();
    expect(screen.getByText("Retry All")).toBeInTheDocument();
    expect(screen.getByText("Continue")).toBeInTheDocument();
    expect(screen.getByText("Skip")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
  });

  it("calls onRetry when clicked", async () => {
    const onRetry = vi.fn();
    render(<RecoveryCard error="Error" onRetry={onRetry} />);
    await userEvent.click(screen.getByText("Retry Step"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when clicked", async () => {
    const onCancel = vi.fn();
    render(<RecoveryCard error="Error" onRetry={vi.fn()} onCancel={onCancel} />);
    await userEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("has alert role", () => {
    render(<RecoveryCard error="Error" onRetry={vi.fn()} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
