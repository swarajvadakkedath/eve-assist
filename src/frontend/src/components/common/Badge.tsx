import type { ReactNode, HTMLAttributes } from "react";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info";
  size?: "sm" | "md";
}

const variantClass: Record<string, string> = {
  default: "pr-badge-default",
  success: "pr-badge-success",
  warning: "pr-badge-warning",
  error: "pr-badge-error",
  info: "pr-badge-info",
};

const sizeClass: Record<string, string> = {
  sm: "pr-badge-sm",
  md: "pr-badge-md",
};

function Badge({
  children,
  variant = "default",
  size = "md",
  className = "",
  ...rest
}: BadgeProps) {
  const classes = [
    "pr-badge",
    variantClass[variant],
    sizeClass[size],
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <span className={classes} role="status" {...rest}>
      {children}
    </span>
  );
}

export default Badge;
