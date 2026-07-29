export interface TypingIndicatorProps {
  visible?: boolean;
}

function TypingIndicator({ visible = true }: TypingIndicatorProps) {
  if (!visible) return null;
  return (
    <div className="pr-typing" role="status" aria-label="Assistant is typing">
      <span className="pr-typing-dot" />
      <span className="pr-typing-dot" />
      <span className="pr-typing-dot" />
    </div>
  );
}

export default TypingIndicator;
