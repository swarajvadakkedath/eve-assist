import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Composer from "./Composer";

describe("Composer", () => {
  it("renders textarea", () => {
    render(<Composer onSend={vi.fn()} />);
    expect(screen.getByRole("textbox", { name: "Message input" })).toBeInTheDocument();
  });

  it("renders send button", () => {
    render(<Composer onSend={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Send message" })).toBeInTheDocument();
  });

  it("disables send button when input is empty", () => {
    render(<Composer onSend={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it("enables send button when input has text", async () => {
    render(<Composer onSend={vi.fn()} />);
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "Hello");
    expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled();
  });

  it("calls onSend with trimmed content", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "Hello");
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(onSend).toHaveBeenCalledWith("Hello");
  });

  it("clears input after send", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "Hello");
    await userEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(textarea).toHaveValue("");
  });

  it("sends on Enter without Shift", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "Hello{Enter}");
    expect(onSend).toHaveBeenCalledWith("Hello");
  });

  it("does not send on Shift+Enter", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "Hello{Shift>}{Enter}{/Shift}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables textarea when disabled", () => {
    render(<Composer onSend={vi.fn()} disabled />);
    expect(screen.getByRole("textbox")).toBeDisabled();
  });
});
