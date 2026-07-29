export interface ExecutionFooterProps {
  children?: React.ReactNode;
}

function ExecutionFooter({ children }: ExecutionFooterProps) {
  if (!children) return null;
  return <div className="pr-exec-card-footer">{children}</div>;
}

export default ExecutionFooter;
