import type { CommandSuggestionsProps } from "./types";
import CommandItemRow from "./CommandItemRow";

function CommandSuggestions({ suggestions, onSelect }: CommandSuggestionsProps) {
  if (suggestions.length === 0) return null;

  return (
    <div className="pr-cmd-suggestions" role="region" aria-label="Suggestions">
      <span className="pr-cmd-suggestions-title">Suggestions</span>
      <div className="pr-cmd-suggestions-list" role="listbox">
        {suggestions.map((cmd) => (
          <CommandItemRow
            key={cmd.id}
            item={cmd}
            selected={false}
            onSelect={() => onSelect(cmd)}
            onHover={() => {}}
          />
        ))}
      </div>
    </div>
  );
}

export default CommandSuggestions;
