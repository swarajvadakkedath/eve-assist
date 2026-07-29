import type { ReactNode, HTMLAttributes } from "react";

export interface PanelProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  header?: ReactNode;
  footer?: ReactNode;
}

function Panel({ children, header, footer, className = "", ...rest }: PanelProps) {
  return (
    <div className={`pr-panel ${className}`.trim()} {...rest}>
      {header && <div className="pr-panel-header">{header}</div>}
      <div className="pr-panel-body">{children}</div>
      {footer && <div className="pr-panel-footer">{footer}</div>}
    </div>
  );
}

export default Panel;
