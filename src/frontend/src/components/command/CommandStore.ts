import type { CommandItem, CommandGroup, CommandHistoryEntry, CommandStoreState } from "./types";
import { getCommandRegistry } from "./CommandRegistry";

const HISTORY_KEY = "aios:command-history";
const PINNED_KEY = "aios:command-pinned";
const MAX_HISTORY = 50;

function loadHistory(): CommandHistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function saveHistory(entries: CommandHistoryEntry[]): void {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries));
  } catch { /* quota exceeded */ }
}

function loadPinned(): string[] {
  try {
    const raw = localStorage.getItem(PINNED_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function savePinned(ids: string[]): void {
  try {
    localStorage.setItem(PINNED_KEY, JSON.stringify(ids));
  } catch { /* quota exceeded */ }
}

function buildGroups(commands: CommandItem[]): CommandGroup[] {
  const groups = new Map<string, CommandItem[]>();
  for (const cmd of commands) {
    const list = groups.get(cmd.category) || [];
    list.push(cmd);
    groups.set(cmd.category, list);
  }
  const LABELS: Record<string, string> = {
    app: "Applications",
    workspace: "Workspaces",
    tool: "Tools",
    plugin: "Plugins",
    conversation: "Conversations",
    session: "Sessions",
    memory: "Memory",
    browser: "Browser",
    voice: "Voice",
    vision: "Vision",
    developer: "Developer",
    file: "Files",
    nlp: "Natural Language",
    recent: "Recent",
  };
  const ORDER: string[] = [
    "recent", "workspace", "app", "nlp", "conversation",
    "session", "tool", "plugin", "memory", "browser",
    "voice", "vision", "file", "developer",
  ];
  const result: CommandGroup[] = [];
  for (const cat of ORDER) {
    const cmds = groups.get(cat);
    if (cmds && cmds.length > 0) {
      result.push({ label: LABELS[cat] || cat, commands: cmds });
    }
  }
  for (const [cat, cmds] of groups) {
    if (!ORDER.includes(cat)) {
      result.push({ label: LABELS[cat] || cat, commands: cmds });
    }
  }
  return result;
}

export class CommandStore {
  private state: CommandStoreState = {
    query: "",
    results: [],
    groups: [],
    selectedIndex: 0,
    loading: false,
    error: null,
    recentCommands: loadHistory(),
    pinnedCommands: loadPinned(),
  };

  private listeners: Set<() => void> = new Set();
  private searchTimeout: ReturnType<typeof setTimeout> | null = null;

  getState(): CommandStoreState {
    return this.state;
  }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  setState(partial: Partial<CommandStoreState>): void {
    this.state = { ...this.state, ...partial };
    this.notify();
  }

  private notify(): void {
    this.listeners.forEach(fn => fn());
  }

  setQuery(query: string): void {
    this.setState({ query, selectedIndex: 0, loading: true, error: null });
    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => this.doSearch(query), 150);
  }

  private async doSearch(query: string): Promise<void> {
    try {
      const registry = getCommandRegistry();
      const results = await registry.searchAll(query);
      const groups = buildGroups(results);
      this.setState({ results, groups, loading: false });
    } catch (err) {
      this.setState({ error: err instanceof Error ? err.message : "Search failed", loading: false });
    }
  }

  selectNext(): void {
    const max = this.state.groups.reduce((n, g) => n + g.commands.length, 0);
    if (max <= 0) return;
    this.setState({ selectedIndex: Math.min(this.state.selectedIndex + 1, max - 1) });
  }

  selectPrevious(): void {
    const max = this.state.groups.reduce((n, g) => n + g.commands.length, 0);
    if (max <= 0) return;
    this.setState({ selectedIndex: Math.max(this.state.selectedIndex - 1, 0) });
  }

  getSelectedItem(): CommandItem | null {
    let idx = 0;
    for (const group of this.state.groups) {
      for (const cmd of group.commands) {
        if (idx === this.state.selectedIndex) return cmd;
        idx++;
      }
    }
    return null;
  }

  recordExecution(commandId: string): void {
    const now = new Date().toISOString();
    const existing = this.state.recentCommands.find(e => e.commandId === commandId);
    let recent: CommandHistoryEntry[];
    if (existing) {
      recent = this.state.recentCommands.map(e =>
        e.commandId === commandId ? { ...e, executedAt: now } : e
      );
    } else {
      recent = [{ commandId, executedAt: now }, ...this.state.recentCommands];
    }
    if (recent.length > MAX_HISTORY) recent = recent.slice(0, MAX_HISTORY);
    this.setState({ recentCommands: recent });
    saveHistory(recent);
  }

  togglePin(commandId: string): void {
    const pinned = this.state.pinnedCommands.includes(commandId)
      ? this.state.pinnedCommands.filter(id => id !== commandId)
      : [...this.state.pinnedCommands, commandId];
    this.setState({ pinnedCommands: pinned });
    savePinned(pinned);
  }

  isPinned(commandId: string): boolean {
    return this.state.pinnedCommands.includes(commandId);
  }

  clearHistory(): void {
    this.setState({ recentCommands: [] });
    saveHistory([]);
  }

  reset(): void {
    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    this.setState({
      query: "", results: [], groups: [], selectedIndex: 0,
      loading: false, error: null, recentCommands: [], pinnedCommands: [],
    });
  }

  getRecentCommands(allCommands: Map<string, CommandItem>): CommandItem[] {
    const items: CommandItem[] = [];
    const seen = new Set<string>();

    for (const id of this.state.pinnedCommands) {
      const cmd = allCommands.get(id);
      if (cmd && !seen.has(id)) {
        items.push({ ...cmd, category: "recent" });
        seen.add(id);
      }
    }

    for (const entry of this.state.recentCommands) {
      const cmd = allCommands.get(entry.commandId);
      if (cmd && !seen.has(entry.commandId)) {
        items.push({ ...cmd, category: "recent" });
        seen.add(entry.commandId);
      }
    }

    return items;
  }
}

let globalCommandStore: CommandStore | null = null;

export function getCommandStore(): CommandStore {
  if (!globalCommandStore) {
    globalCommandStore = new CommandStore();
  }
  return globalCommandStore;
}
