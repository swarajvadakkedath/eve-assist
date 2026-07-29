import type { ReactNode } from "react";

export interface AppShellProps {
  sidebar: ReactNode;
  children: ReactNode;
  className?: string;
}

function AppShell({ sidebar, children, className = "" }: AppShellProps) {
  return (
    <div className={`pr-app-shell ${className}`.trim()}>
      {sidebar}
      {children}
    </div>
  );
}

export default AppShell;
