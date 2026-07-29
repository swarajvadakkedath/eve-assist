import type { HTMLAttributes } from "react";

export interface BreadcrumbItem {
  label: string;
  id: string;
}

export interface MemoryBreadcrumbsProps extends HTMLAttributes<HTMLDivElement> {
  items: readonly BreadcrumbItem[];
  onNavigate?: (item: BreadcrumbItem) => void;
}

export function MemoryBreadcrumbs({
  items,
  onNavigate,
  className = "",
  ...rest
}: MemoryBreadcrumbsProps) {
  if (items.length === 0) return null;

  const classes = ["mw-breadcrumbs", className].filter(Boolean).join(" ");

  return (
    <nav className={classes} aria-label="Breadcrumb" {...rest}>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;

        return (
          <span key={item.id} className="mw-breadcrumb-item">
            {index > 0 && (
              <span className="mw-breadcrumb-separator" aria-hidden="true">/</span>
            )}
            {isLast ? (
              <span className="active" aria-current="page">{item.label}</span>
            ) : (
              <span
                role="link"
                tabIndex={0}
                onClick={() => onNavigate?.(item)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onNavigate?.(item);
                }}
              >
                {item.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
