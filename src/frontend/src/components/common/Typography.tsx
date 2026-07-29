import type { ReactNode, ElementType, HTMLAttributes } from "react";

export type TypographyVariant =
  | "h1"
  | "h2"
  | "h3"
  | "h4"
  | "h5"
  | "h6"
  | "body"
  | "body-sm"
  | "caption"
  | "label";

export interface TypographyProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  variant?: TypographyVariant;
  as?: ElementType;
  color?: "primary" | "secondary" | "accent" | "error" | "success" | "warning";
}

const variantTag: Record<TypographyVariant, ElementType> = {
  h1: "h1",
  h2: "h2",
  h3: "h3",
  h4: "h4",
  h5: "h5",
  h6: "h6",
  body: "p",
  "body-sm": "p",
  caption: "span",
  label: "span",
};

const colorStyle: Record<string, string> = {
  primary: "var(--text-primary)",
  secondary: "var(--text-secondary)",
  accent: "var(--accent)",
  error: "var(--error)",
  success: "var(--success)",
  warning: "var(--warning)",
};

const variantStyle: Record<TypographyVariant, React.CSSProperties> = {
  h1: { fontSize: "var(--text-3xl)", fontWeight: "var(--weight-bold)", lineHeight: "var(--leading-tight)" },
  h2: { fontSize: "var(--text-2xl)", fontWeight: "var(--weight-bold)", lineHeight: "var(--leading-tight)" },
  h3: { fontSize: "var(--text-xl)", fontWeight: "var(--weight-semibold)", lineHeight: "var(--leading-tight)" },
  h4: { fontSize: "var(--text-lg)", fontWeight: "var(--weight-semibold)", lineHeight: "var(--leading-normal)" },
  h5: { fontSize: "var(--text-base)", fontWeight: "var(--weight-medium)", lineHeight: "var(--leading-normal)" },
  h6: { fontSize: "var(--text-sm)", fontWeight: "var(--weight-medium)", lineHeight: "var(--leading-normal)" },
  body: { fontSize: "var(--text-base)", fontWeight: "var(--weight-normal)", lineHeight: "var(--leading-relaxed)" },
  "body-sm": { fontSize: "var(--text-sm)", fontWeight: "var(--weight-normal)", lineHeight: "var(--leading-normal)" },
  caption: { fontSize: "var(--text-xs)", fontWeight: "var(--weight-normal)", lineHeight: "var(--leading-normal)" },
  label: { fontSize: "var(--text-sm)", fontWeight: "var(--weight-medium)", lineHeight: "var(--leading-normal)" },
};

function Typography({
  children,
  variant = "body",
  as,
  color,
  style,
  ...rest
}: TypographyProps) {
  const Component = as || variantTag[variant];
  const combinedStyle: React.CSSProperties = {
    ...variantStyle[variant],
    ...(color ? { color: colorStyle[color] } : {}),
    ...style,
  };

  return (
    <Component style={combinedStyle} {...rest}>
      {children}
    </Component>
  );
}

export default Typography;
