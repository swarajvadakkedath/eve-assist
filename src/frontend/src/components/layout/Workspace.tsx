import type { ReactNode, HTMLAttributes } from "react";

export interface WorkspaceProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
  header?: ReactNode;
  footer?: ReactNode;
  loading?: boolean;
  empty?: boolean;
  emptyMessage?: string;
}

function Workspace({
  children,
  header,
  footer,
  loading = false,
  empty = false,
  emptyMessage = "No content",
  className = "",
  ...rest
}: WorkspaceProps) {
  return (
    <div className={`pr-workspace ${className}`.trim()} {...rest}>
      {header}
      {loading && (
        <div className="pr-workspace-loading" role="status" aria-label="Loading">
          Loading...
        </div>
      )}
      {!loading && empty && (
        <div className="pr-workspace-empty" role="status">
          {emptyMessage}
        </div>
      )}
      {!loading && !empty && children}
      {footer}
    </div>
  );
}

export default Workspace;
