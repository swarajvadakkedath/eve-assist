import type { NaturalLanguageResultProps } from "./types";

const ACTION_LABELS: Record<string, string> = {
  "open-workspace": "Open workspace",
  "open-conversation": "Open conversation",
  "open-session": "Open session",
  "execute-tool": "Run tool",
  "open-panel": "Open panel",
  "nlp-query": "Process query",
  "open-url": "Navigate to URL",
  "run-command": "Execute command",
  "run-plugin": "Run plugin",
  "search-query": "Search",
};

function NaturalLanguageResult({ intent, onExecute }: NaturalLanguageResultProps) {
  const confidencePct = Math.round(intent.confidence * 100);

  return (
    <div className="pr-cmd-nlp" role="region" aria-label="Natural language interpretation">
      <div className="pr-cmd-nlp-header">
        <span className="pr-cmd-nlp-badge">NL</span>
        <span className="pr-cmd-nlp-intent">{intent.intent}</span>
        <span className="pr-cmd-nlp-confidence" aria-label={`${confidencePct}% confidence`}>
          {confidencePct}%
        </span>
      </div>
      <p className="pr-cmd-nlp-text">{intent.text}</p>
      <div className="pr-cmd-nlp-action">
        <span className="pr-cmd-nlp-action-label">
          {ACTION_LABELS[intent.resultType] || intent.resultType}
        </span>
        {intent.suggestedCommand && (
          <button
            className="pr-cmd-nlp-execute"
            onClick={() => onExecute(intent.suggestedCommand!)}
          >
            Execute
          </button>
        )}
      </div>
    </div>
  );
}

export default NaturalLanguageResult;
