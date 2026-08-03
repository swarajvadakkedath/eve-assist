import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { getCommandRegistry } from "./CommandRegistry";
import { getCommandStore } from "./CommandStore";
import CommandCenter from "./CommandCenter";
import type { CommandItem } from "./types";

describe("CommandRegistry", () => {
  beforeEach(() => {
    getCommandRegistry().setStaticCommands([]);
  });

  it("registers static commands", () => {
    const reg = getCommandRegistry();
    const cmd: CommandItem = {
      id: "test-1", name: "Test", description: "A test command",
      category: "app", resultType: "run-command", action: () => {},
    };
    reg.addStaticCommand(cmd);
    expect(reg.getStaticCommands()).toHaveLength(1);
  });

  it("searches by fuzzy match", async () => {
    const reg = getCommandRegistry();
    reg.setStaticCommands([
      { id: "settings", name: "Settings", description: "Open settings", category: "app", resultType: "open-panel", action: () => {} },
      { id: "theme", name: "Toggle Theme", description: "Switch theme", category: "app", resultType: "run-command", action: () => {} },
    ]);
    const results = await reg.searchAll("set");
    expect(results.length).toBeGreaterThanOrEqual(1);
    expect(results[0].id).toBe("settings");
  });

  it("returns empty for no match", async () => {
    const reg = getCommandRegistry();
    reg.setStaticCommands([]);
    const results = await reg.searchAll("zzzznonexistent");
    expect(results).toHaveLength(0);
  });
});

describe("CommandStore", () => {
  beforeEach(() => {
    getCommandStore().reset();
    getCommandRegistry().setStaticCommands([]);
  });

  it("stores query state", () => {
    const store = getCommandStore();
    store.setQuery("test");
    expect(store.getState().query).toBe("test");
  });

  it("tracks selection index", async () => {
    const reg = getCommandRegistry();
    reg.setStaticCommands([{ id: "a", name: "A", description: "", category: "app", resultType: "run-command", action: () => {} }]);
    const store = getCommandStore();
    store.reset();
    store.setQuery("");
    await new Promise(r => setTimeout(r, 200));
    const state = store.getState();
    expect(state.selectedIndex).toBe(0);
    expect(state.groups.length).toBeGreaterThanOrEqual(0);
  });

  it("records execution history", () => {
    const store = getCommandStore();
    store.recordExecution("cmd-1");
    expect(store.getState().recentCommands.length).toBeGreaterThanOrEqual(1);
    expect(store.getState().recentCommands[0].commandId).toBe("cmd-1");
  });

  it("toggles pin state", () => {
    const store = getCommandStore();
    expect(store.isPinned("pin-1")).toBe(false);
    store.togglePin("pin-1");
    expect(store.isPinned("pin-1")).toBe(true);
    store.togglePin("pin-1");
    expect(store.isPinned("pin-1")).toBe(false);
  });

  it("clears history", () => {
    const store = getCommandStore();
    store.recordExecution("cmd-clear");
    store.clearHistory();
    expect(store.getState().recentCommands).toHaveLength(0);
  });
});

describe("CommandCenter", () => {
  beforeEach(() => {
    getCommandRegistry().setStaticCommands([]);
    getCommandStore().reset();
  });

  it("renders overlay with input", () => {
    render(
      <CommandCenter
        workspaces={[{ id: "test", label: "Test" }]}
        onClose={() => {}}
        onNavigate={() => {}}
      />
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("Command search")).toBeInTheDocument();
  });

  it("renders empty state by default", () => {
    const { container } = render(
      <CommandCenter
        workspaces={[{ id: "test", label: "Test" }]}
        onClose={() => {}}
        onNavigate={() => {}}
      />
    );
    expect(container.querySelector(".pr-cmd-empty")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Type a command or search...")).toBeInTheDocument();
  });
});
