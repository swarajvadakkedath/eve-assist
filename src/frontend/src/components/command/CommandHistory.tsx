import type { CommandHistoryProps } from "./types";
import CommandItemRow from "./CommandItemRow";

function CommandHistory({
  entries, pinnedIds, onSelect, onTogglePin, onClear, allCommands,
}: CommandHistoryProps) {
  if (entries.length === 0) {
    return null;
  }

  const displayed = entries.slice(0, 10);

  return (
    <div className="pr-cmd-history" role="region" aria-label="Recent commands">
      <div className="pr-cmd-history-header">
        <span className="pr-cmd-history-title">Recent</span>
        <button className="pr-cmd-history-clear" onClick={onClear} title="Clear history">
          Clear
        </button>
      </div>
      <div className="pr-cmd-history-list" role="listbox" aria-label="Recent commands">
        {displayed.map((entry) => {
          const cmd = allCommands.get(entry.commandId);
          if (!cmd) return null;
          const pinned = pinnedIds.includes(entry.commandId);
          return (
            <div key={entry.commandId} className="pr-cmd-history-item" role="presentation">
              <CommandItemRow
                item={cmd}
                selected={false}
                onSelect={() => onSelect(cmd)}
                onHover={() => {}}
              />
              <button
                className={`pr-cmd-history-pin ${pinned ? "pr-cmd-history-pinned" : ""}`}
                onClick={() => onTogglePin(entry.commandId)}
                aria-label={pinned ? "Unpin command" : "Pin command"}
                title={pinned ? "Unpin" : "Pin"}
              >
                {pinned ? '\u2605' : '\u2606'}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default CommandHistory;
