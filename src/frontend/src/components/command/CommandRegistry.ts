import type { CommandItem, CommandProvider } from "./types";

function fuzzyMatch(text: string, query: string): boolean {
  const lower = text.toLowerCase();
  const q = query.toLowerCase();
  if (lower.includes(q)) return true;
  let qi = 0;
  for (let i = 0; i < lower.length && qi < q.length; i++) {
    if (lower[i] === q[qi]) qi++;
  }
  return qi === q.length;
}

function scoreItem(item: CommandItem, query: string): number {
  const q = query.toLowerCase();
  const name = item.name.toLowerCase();
  const desc = item.description.toLowerCase();
  let score = 0;
  if (name === q) score += 100;
  else if (name.startsWith(q)) score += 80;
  else if (name.includes(q)) score += 60;
  else if (desc.includes(q)) score += 40;
  if (item.keywords?.some(k => k.toLowerCase().includes(q))) score += 20;
  if (item.highlight) score += 10;
  return score;
}

export class CommandRegistry {
  private providers: Map<string, CommandProvider> = new Map();
  private staticCommands: CommandItem[] = [];
  private listeners: Set<() => void> = new Set();

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    this.listeners.forEach(fn => fn());
  }

  registerProvider(provider: CommandProvider): void {
    this.providers.set(provider.id, provider);
    this.notify();
  }

  unregisterProvider(id: string): void {
    this.providers.delete(id);
    this.notify();
  }

  getProvider(id: string): CommandProvider | undefined {
    return this.providers.get(id);
  }

  getAllProviders(): CommandProvider[] {
    return Array.from(this.providers.values());
  }

  setStaticCommands(commands: CommandItem[]): void {
    this.staticCommands = commands;
    this.notify();
  }

  addStaticCommand(command: CommandItem): void {
    this.staticCommands = [...this.staticCommands, command];
    this.notify();
  }

  getStaticCommands(): CommandItem[] {
    return this.staticCommands;
  }

  async searchAll(query: string): Promise<CommandItem[]> {
    if (!query.trim()) {
      return this.getRecentFirst();
    }

    const results: CommandItem[] = [];
    const seen = new Set<string>();

    for (const cmd of this.staticCommands) {
      if (seen.has(cmd.id)) continue;
      if (fuzzyMatch(cmd.name + " " + cmd.description + " " + (cmd.keywords?.join(" ") || ""), query)) {
        results.push(cmd);
        seen.add(cmd.id);
      }
    }

    for (const provider of this.providers.values()) {
      try {
        const providerResults = await provider.search(query);
        for (const cmd of providerResults) {
          if (!seen.has(cmd.id)) {
            results.push(cmd);
            seen.add(cmd.id);
          }
        }
      } catch { /* skip failed providers */ }
    }

    return results
      .map(item => ({ item, score: scoreItem(item, query) }))
      .sort((a, b) => b.score - a.score)
      .map(({ item }) => item);
  }

  private getRecentFirst(): CommandItem[] {
    return [...this.staticCommands];
  }

  getAllCommands(): CommandItem[] {
    const all: CommandItem[] = [...this.staticCommands];
    for (const provider of this.providers.values()) {
      all.push(...provider.commands);
    }
    return all;
  }
}

let globalRegistry: CommandRegistry | null = null;

export function getCommandRegistry(): CommandRegistry {
  if (!globalRegistry) {
    globalRegistry = new CommandRegistry();
  }
  return globalRegistry;
}
