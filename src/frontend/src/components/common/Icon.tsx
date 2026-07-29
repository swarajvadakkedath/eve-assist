import type { ReactNode, HTMLAttributes } from "react";

export interface IconProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  size?: number;
  label?: string;
}

function Icon({ children, size = 16, label, className = "", ...rest }: IconProps) {
  return (
    <span
      className={`pr-icon ${className}`.trim()}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={!label}
      style={{ width: size, height: size }}
      {...rest}
    >
      {children}
    </span>
  );
}

export default Icon;
