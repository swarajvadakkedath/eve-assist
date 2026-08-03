import { useEffect, useCallback, useRef, useMemo } from "react";
import type { CommandItem, CommandCenterProps } from "./types";
import { getCommandStore } from "./CommandStore";
import { getCommandRegistry } from "./CommandRegistry";
import CommandInput from "./CommandInput";
import CommandResults from "./CommandResults";
import CommandFooter from "./CommandFooter";
import CommandHistory from "./CommandHistory";
import { useCommandStore } from "./useCommandStore";

function CommandCenter({ onClose, defaultQuery }: CommandCenterProps) {
  const store = useMemo(() => getCommandStore(), []);
  const registry = useMemo(() => getCommandRegistry(), []);
  const state = useCommandStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const paletteRef = useRef<HTMLDivElement>(null);

  const allCommands = useMemo(() => {
    const map = new Map<string, CommandItem>();
    for (const cmd of registry.getAllCommands()) {
      map.set(cmd.id, cmd);
    }
    return map;
  }, [registry, state]);

  useEffect(() => {
    if (defaultQuery) {
      store.setQuery(defaultQuery);
    }
  }, [defaultQuery, store]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        store.selectNext();
        break;
      case "ArrowUp":
        e.preventDefault();
        store.selectPrevious();
        break;
      case "Enter": {
        e.preventDefault();
        const selected = store.getSelectedItem();
        if (selected) {
          store.recordExecution(selected.id);
          selected.action();
          onClose();
        }
        break;
      }
      case "Escape":
        e.preventDefault();
        onClose();
        break;
    }
  }, [store, onClose]);

  const handleSelect = useCallback((item: CommandItem) => {
    store.recordExecution(item.id);
    item.action();
    onClose();
  }, [store, onClose]);

  const handleTogglePin = useCallback((commandId: string) => {
    store.togglePin(commandId);
  }, [store]);

  const handleClearHistory = useCallback(() => {
    store.clearHistory();
  }, [store]);

  const hasQuery = state.query.trim().length > 0;
  return (
    <div className="pr-cmd-overlay" ref={paletteRef} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="pr-cmd-palette" role="dialog" aria-label="Command palette" aria-modal="true">
        <CommandInput
          value={state.query}
          onChange={(q) => store.setQuery(q)}
          onKeyDown={handleKeyDown}
          inputRef={inputRef}
        />

        {!hasQuery && (
          <CommandHistory
            entries={store.getState().recentCommands}
            pinnedIds={store.getState().pinnedCommands}
            onSelect={handleSelect}
            onTogglePin={handleTogglePin}
            onClear={handleClearHistory}
            allCommands={allCommands}
          />
        )}

        <CommandResults
          groups={state.groups}
          selectedIndex={state.selectedIndex}
          onSelect={handleSelect}
          onHover={(idx) => store.setState({ selectedIndex: idx })}
          loading={state.loading}
          error={state.error}
          query={state.query}
        />

        <CommandFooter
          totalResults={state.groups.reduce((n, g) => n + g.commands.length, 0)}
          selectedIndex={state.selectedIndex}
          hasQuery={hasQuery}
        />
      </div>
    </div>
  );
}

export default CommandCenter;
