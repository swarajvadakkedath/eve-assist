export interface ConversationEmptyStateProps {
  onNewConversation?: () => void;
}

function ConversationEmptyState({ onNewConversation }: ConversationEmptyStateProps) {
  return (
    <div className="pr-conv-empty">
      <div className="pr-conv-empty-icon" aria-hidden="true">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <h2 className="pr-conv-empty-title">Welcome to Eve</h2>
      <p className="pr-conv-empty-text">
        Your intelligent AI operating system. Start a conversation to get started.
      </p>
      <div className="pr-conv-empty-shortcuts">
        <span>Ctrl+K — Command Palette</span>
        <span>Ctrl+, — Settings</span>
        <span>Enter — Send</span>
        <span>Shift+Enter — New Line</span>
      </div>
      {onNewConversation && (
        <button className="pr-conv-empty-action" onClick={onNewConversation}>
          New Conversation
        </button>
      )}
    </div>
  );
}

export default ConversationEmptyState;
