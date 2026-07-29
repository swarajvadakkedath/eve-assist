import type { ReactNode, HTMLAttributes } from "react";

export interface WorkspaceHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  controls?: ReactNode;
  status?: ReactNode;
}

function WorkspaceHeader({ title, controls, status, className = "", ...rest }: WorkspaceHeaderProps) {
  return (
    <div className={`pr-topbar ${className}`.trim()} {...rest}>
      {title && <h1 className="pr-topbar-title">{title}</h1>}
      {status && <div className="pr-topbar-status">{status}</div>}
      {controls && <div className="pr-topbar-controls">{controls}</div>}
    </div>
  );
}

export default WorkspaceHeader;
