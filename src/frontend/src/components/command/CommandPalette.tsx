import { useEffect, useState, useCallback, useRef } from "react";
import type { CommandItem } from "./types";
import { getCommandStore } from "./CommandStore";
import { getCommandRegistry } from "./CommandRegistry";
import CommandCenter from "./CommandCenter";

export interface CommandPaletteTriggerProps {
  workspaces: { id: string; label: string; icon?: string }[];
  onNavigate: (action: string, payload?: string) => void;
  onSwitchWorkspace?: (workspaceId: string) => void;
  activeWorkspaceId?: string;
  shortcut?: string;
}

export function useCommandPalette(
  workspaces: { id: string; label: string; icon?: string }[],
  onNavigate: (action: string, payload?: string) => void,
  onSwitchWorkspace?: (workspaceId: string) => void,
  activeWorkspaceId?: string,
) {
  const [open, setOpen] = useState(false);
  const [defaultQuery, setDefaultQuery] = useState<string | undefined>();
  const storeRef = useRef(getCommandStore());

  const initializeCommands = useCallback(() => {
    const registry = getCommandRegistry();

    registry.setStaticCommands([
      {
        id: "switch-home",
        name: "Home",
        description: "Go to home workspace",
        category: "workspace",
        resultType: "open-workspace",
        shortcut: "Mod+1",
        action: () => onNavigate?.("workspace", "home"),
      },
      {
        id: "switch-conversations",
        name: "Conversations",
        description: "Open conversations workspace",
        category: "workspace",
        resultType: "open-workspace",
        shortcut: "Mod+2",
        action: () => onNavigate?.("workspace", "conversations"),
      },
      {
        id: "switch-execution",
        name: "Execution History",
        description: "Open execution history workspace",
        category: "workspace",
        resultType: "open-workspace",
        shortcut: "Mod+3",
        action: () => onNavigate?.("workspace", "execution"),
      },
      {
        id: "switch-activity",
        name: "Activity Center",
        description: "Open activity center workspace",
        category: "workspace",
        resultType: "open-workspace",
        shortcut: "Mod+4",
        action: () => onNavigate?.("workspace", "activity"),
      },
      {
        id: "new-conversation",
        name: "New Conversation",
        description: "Start a new conversation",
        category: "conversation",
        resultType: "open-conversation",
        shortcut: "Mod+N",
        action: () => onNavigate?.("conversation", "new"),
      },
      {
        id: "search-conversations",
        name: "Search Conversations",
        description: "Search through all conversations",
        category: "conversation",
        resultType: "search-query",
        action: () => onNavigate?.("search", "conversations"),
      },
      {
        id: "toggle-sidebar",
        name: "Toggle Sidebar",
        description: "Show or hide the sidebar",
        category: "app",
        resultType: "open-panel",
        shortcut: "Mod+B",
        action: () => onNavigate?.("panel", "sidebar"),
      },
      {
        id: "toggle-panel",
        name: "Toggle Right Panel",
        description: "Show or hide the right panel",
        category: "app",
        resultType: "open-panel",
        shortcut: "Mod+J",
        action: () => onNavigate?.("panel", "right"),
      },
      {
        id: "settings",
        name: "Settings",
        description: "Open application settings",
        category: "app",
        resultType: "open-panel",
        shortcut: "Mod+,",
        action: () => onNavigate?.("panel", "settings"),
      },
      {
        id: "help",
        name: "Help & Support",
        description: "View help documentation and support",
        category: "app",
        resultType: "open-url",
        action: () => onNavigate?.("url", "/help"),
      },
      {
        id: "toggle-theme",
        name: "Toggle Theme",
        description: "Switch between light and dark mode",
        category: "app",
        resultType: "run-command",
        action: () => onNavigate?.("command", "toggle-theme"),
      },
      {
        id: "run-tool",
        name: "Run Tool...",
        description: "Execute a tool or command",
        category: "tool",
        resultType: "execute-tool",
        action: () => setDefaultQuery("tool:"),
      },
      {
        id: "run-plugin",
        name: "Run Plugin...",
        description: "Execute a plugin",
        category: "plugin",
        resultType: "run-plugin",
        action: () => setDefaultQuery("plugin:"),
      },
    ]);
  }, [onNavigate]);

  useEffect(() => {
    initializeCommands();
  }, [initializeCommands]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        if (!open) setDefaultQuery(undefined);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  useEffect(() => {
    if (!open) {
      const store = getCommandStore();
      store.setQuery("");
    }
  }, [open]);

  const openPalette = useCallback((query?: string) => {
    setDefaultQuery(query);
    setOpen(true);
  }, []);

  return {
    open,
    setOpen,
    defaultQuery,
    openPalette,
    renderPalette: open ? (
      <CommandCenter
        workspaces={workspaces}
        onClose={() => setOpen(false)}
        onNavigate={onNavigate}
        onSwitchWorkspace={onSwitchWorkspace}
        activeWorkspaceId={activeWorkspaceId}
        defaultQuery={defaultQuery}
      />
    ) : null,
  };
}
