import type { ReactNode, HTMLAttributes } from "react";

export interface StatusBarItem {
  id: string;
  label?: string;
  dot?: string;
  children?: ReactNode;
}

export interface StatusBarProps extends HTMLAttributes<HTMLDivElement> {
  items?: StatusBarItem[];
  left?: ReactNode;
  right?: ReactNode;
}

function StatusBar({ items, left, right, className = "", ...rest }: StatusBarProps) {
  return (
    <div
      className={`pr-statusbar ${className}`.trim()}
      role="status"
      aria-label="Application status"
      {...rest}
    >
      {left}
      {items?.map((item) => (
        <div key={item.id} className="pr-statusbar-section">
          {item.dot && (
            <span
              className="pr-statusbar-dot"
              style={{ backgroundColor: item.dot }}
              aria-hidden="true"
            />
          )}
          {item.label && <span className="pr-statusbar-label">{item.label}</span>}
          {item.children}
        </div>
      ))}
      <div className="pr-statusbar-spacer" />
      {right}
    </div>
  );
}

export default StatusBar;
