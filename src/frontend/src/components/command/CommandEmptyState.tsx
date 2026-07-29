import type { CommandEmptyStateProps } from "./types";

function CommandEmptyState({ query, hasSuggestions }: CommandEmptyStateProps) {
  if (query && !hasSuggestions) {
    return (
      <div className="pr-cmd-empty" role="status">
        <div className="pr-cmd-empty-icon" aria-hidden="true">[SEARCH]</div>
        <p className="pr-cmd-empty-title">No results for "{query}"</p>
        <p className="pr-cmd-empty-desc">Try a different search term or browse categories</p>
      </div>
    );
  }
  return (
    <div className="pr-cmd-empty" role="status">
      <div className="pr-cmd-empty-icon" aria-hidden="true">[CMD]</div>
      <p className="pr-cmd-empty-title">Type a command or search</p>
      <p className="pr-cmd-empty-desc">Search conversations, tools, workspaces, and more</p>
    </div>
  );
}

export default CommandEmptyState;
