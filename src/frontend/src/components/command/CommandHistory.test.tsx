import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CommandHistory from "./CommandHistory";
import type { CommandItem, CommandHistoryEntry } from "./types";

const cmd1: CommandItem = {
  id: "cmd-1", name: "Settings", description: "Open settings", category: "app", resultType: "open-panel", action: () => {},
};
const cmd2: CommandItem = {
  id: "cmd-2", name: "Theme", description: "Toggle theme", category: "app", resultType: "run-command", action: () => {},
};

const allCommands = new Map<string, CommandItem>([
  ["cmd-1", cmd1],
  ["cmd-2", cmd2],
]);

const entries: CommandHistoryEntry[] = [
  { commandId: "cmd-1", executedAt: "2026-07-20T10:00:00Z" },
  { commandId: "cmd-2", executedAt: "2026-07-20T09:00:00Z" },
];

describe("CommandHistory", () => {
  it("returns null when empty", () => {
    const { container } = render(
      <CommandHistory entries={[]} pinnedIds={[]} onSelect={() => {}} onTogglePin={() => {}} onClear={() => {}} allCommands={allCommands} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders recent commands", () => {
    render(
      <CommandHistory entries={entries} pinnedIds={[]} onSelect={() => {}} onTogglePin={() => {}} onClear={() => {}} allCommands={allCommands} />
    );
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Theme")).toBeInTheDocument();
  });

  it("shows pinned state", () => {
    render(
      <CommandHistory entries={entries} pinnedIds={["cmd-1"]} onSelect={() => {}} onTogglePin={() => {}} onClear={() => {}} allCommands={allCommands} />
    );
    const pinButtons = screen.getAllByTitle("Unpin");
    expect(pinButtons.length).toBeGreaterThanOrEqual(1);
  });

  it("calls onClear when clear button clicked", async () => {
    const user = userEvent.setup();
    let cleared = false;
    render(
      <CommandHistory entries={entries} pinnedIds={[]} onSelect={() => {}} onTogglePin={() => {}} onClear={() => { cleared = true; }} allCommands={allCommands} />
    );
    await user.click(screen.getByText("Clear"));
    expect(cleared).toBe(true);
  });
});
