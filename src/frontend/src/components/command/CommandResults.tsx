import type { CommandResultsProps } from "./types";
import CommandCategory from "./CommandCategory";
import CommandItemRow from "./CommandItemRow";
import CommandEmptyState from "./CommandEmptyState";
import CommandLoadingState from "./CommandLoadingState";
import CommandErrorState from "./CommandErrorState";

function CommandResults({ groups, selectedIndex, onSelect, onHover, loading, error, query }: CommandResultsProps) {
  const totalItems = groups.reduce((n, g) => n + g.commands.length, 0);
  const hasSuggestions = totalItems > 0;

  if (loading) {
    return <CommandLoadingState />;
  }

  if (error) {
    return <CommandErrorState error={error} />;
  }

  if (totalItems === 0) {
    return <CommandEmptyState query={query} hasSuggestions={hasSuggestions} />;
  }

  let flatIdx = 0;
  return (
    <div className="pr-cmd-results" role="listbox" aria-label="Command results" tabIndex={-1}>
      {groups.map((group) => (
        <div key={group.label} role="presentation">
          <CommandCategory label={group.label} count={group.commands.length} />
          {group.commands.map((cmd) => {
            const currentIdx = flatIdx;
            flatIdx++;
            return (
              <CommandItemRow
                key={cmd.id}
                item={cmd}
                selected={selectedIndex === currentIdx}
                onSelect={() => onSelect(cmd)}
                onHover={() => onHover(currentIdx)}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
}

export default CommandResults;
