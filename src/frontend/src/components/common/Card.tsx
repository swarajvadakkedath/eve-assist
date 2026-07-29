import type { ReactNode, HTMLAttributes } from "react";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  padding?: "none" | "sm" | "md" | "lg";
  variant?: "elevated" | "outlined" | "filled";
}

const paddingClass: Record<string, string> = {
  none: "pr-card-padding-none",
  sm: "pr-card-padding-sm",
  md: "pr-card-padding-md",
  lg: "pr-card-padding-lg",
};

const variantClass: Record<string, string> = {
  elevated: "pr-card-elevated",
  outlined: "pr-card-outlined",
  filled: "pr-card-filled",
};

function Card({
  children,
  padding = "md",
  variant = "outlined",
  className = "",
  ...rest
}: CardProps) {
  const classes = [
    "pr-card",
    variantClass[variant],
    paddingClass[padding],
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}

export default Card;
