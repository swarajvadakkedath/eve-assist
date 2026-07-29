import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CommandItemRow from "./CommandItemRow";
import type { CommandItem } from "./types";

const baseItem: CommandItem = {
  id: "test-cmd",
  name: "Test Command",
  description: "A test command description",
  category: "app",
  resultType: "run-command",
  action: () => {},
};

describe("CommandItemRow", () => {
  it("renders name and description", () => {
    render(<CommandItemRow item={baseItem} selected={false} onSelect={() => {}} onHover={() => {}} />);
    expect(screen.getByText("Test Command")).toBeInTheDocument();
    expect(screen.getByText("A test command description")).toBeInTheDocument();
  });

  it("renders shortcut when provided", () => {
    const item = { ...baseItem, shortcut: "Mod+K" };
    render(<CommandItemRow item={item} selected={false} onSelect={() => {}} onHover={() => {}} />);
    expect(screen.getByText("K")).toBeInTheDocument();
  });

  it("applies selected class", () => {
    const { container } = render(<CommandItemRow item={baseItem} selected={true} onSelect={() => {}} onHover={() => {}} />);
    expect(container.querySelector(".pr-cmd-item-selected")).toBeInTheDocument();
  });

  it("calls onSelect on click", async () => {
    const user = userEvent.setup();
    let called = false;
    render(<CommandItemRow item={baseItem} selected={false} onSelect={() => { called = true; }} onHover={() => {}} />);
    await user.click(screen.getByText("Test Command"));
    expect(called).toBe(true);
  });

  it("calls onHover on mouse enter", async () => {
    const user = userEvent.setup();
    let called = false;
    render(<CommandItemRow item={baseItem} selected={false} onSelect={() => {}} onHover={() => { called = true; }} />);
    await user.hover(screen.getByText("Test Command"));
    expect(called).toBe(true);
  });

  it("has role option", () => {
    render(<CommandItemRow item={baseItem} selected={false} onSelect={() => {}} onHover={() => {}} />);
    expect(screen.getByRole("option")).toBeInTheDocument();
  });
});
