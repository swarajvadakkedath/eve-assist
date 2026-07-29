import type { ReactNode, HTMLAttributes } from "react";

export type SurfaceVariant =
  | "primary"
  | "secondary"
  | "elevated"
  | "floating"
  | "panel";

export interface SurfaceProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: SurfaceVariant;
}

const variantClass: Record<SurfaceVariant, string> = {
  primary: "pr-surface",
  secondary: "pr-surface-secondary",
  elevated: "pr-surface-elevated",
  floating: "pr-surface-floating",
  panel: "pr-surface-panel",
};

function Surface({
  children,
  variant = "primary",
  className = "",
  ...rest
}: SurfaceProps) {
  return (
    <div
      className={`${variantClass[variant]} ${className}`.trim()}
      {...rest}
    >
      {children}
    </div>
  );
}

export default Surface;
