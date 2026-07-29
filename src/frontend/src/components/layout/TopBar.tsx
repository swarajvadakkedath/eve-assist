import type { ReactNode, HTMLAttributes } from "react";

export interface TopBarProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  controls?: ReactNode;
  status?: ReactNode;
}

function TopBar({ title, controls, status, className = "", ...rest }: TopBarProps) {
  return (
    <div className={`pr-topbar ${className}`.trim()} role="banner" {...rest}>
      {title && <h1 className="pr-topbar-title">{title}</h1>}
      {status && <div className="pr-topbar-status">{status}</div>}
      {controls && <div className="pr-topbar-controls">{controls}</div>}
    </div>
  );
}

export default TopBar;
