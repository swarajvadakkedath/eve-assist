import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: ReactNode;
}

const sizeClass: Record<string, string> = {
  sm: "pr-btn-sm",
  md: "pr-btn-md",
  lg: "pr-btn-lg",
};

const variantClass: Record<string, string> = {
  primary: "pr-btn-primary",
  secondary: "pr-btn-secondary",
  ghost: "pr-btn-ghost",
  danger: "pr-btn-danger",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      icon,
      children,
      className = "",
      disabled,
      type = "button",
      ...rest
    },
    ref,
  ) => {
    const classes = [
      "pr-btn",
      variantClass[variant],
      sizeClass[size],
      loading ? "pr-btn-loading" : "",
      icon && !children ? "pr-btn-icon-only" : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <button
        ref={ref}
        type={type}
        className={classes}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...rest}
      >
        {loading ? <span className="pr-btn-spinner" aria-hidden="true" /> : icon}
        {children && <span>{children}</span>}
      </button>
    );
  },
);

Button.displayName = "Button";

export default Button;
