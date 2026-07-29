export interface StreamingCursorProps {
  visible?: boolean;
}

function StreamingCursor({ visible = true }: StreamingCursorProps) {
  if (!visible) return null;
  return <span className="pr-streaming-cursor" aria-hidden="true" />;
}

export default StreamingCursor;
