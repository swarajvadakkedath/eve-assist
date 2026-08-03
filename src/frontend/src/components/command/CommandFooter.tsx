import type { CommandFooterProps } from "./types";

function CommandFooter({ totalResults, hasQuery }: CommandFooterProps) {
  return (
    <div className="pr-cmd-footer" role="toolbar" aria-label="Command palette tips">
      <div className="pr-cmd-footer-tips">
        <span className="pr-cmd-footer-tip">
          <kbd className="pr-cmd-kbd">{'\u2191'}{'\u2193'}</kbd> navigate
        </span>
        <span className="pr-cmd-footer-tip">
          <kbd className="pr-cmd-kbd">{'\u23CE'}</kbd> select
        </span>
        <span className="pr-cmd-footer-tip">
          <kbd className="pr-cmd-kbd">ESC</kbd> close
        </span>
      </div>
      {hasQuery && (
        <span className="pr-cmd-footer-count">
          {totalResults} result{totalResults !== 1 ? "s" : ""}
        </span>
      )}
    </div>
  );
}

export default CommandFooter;
