import type { ReactNode, ButtonHTMLAttributes } from "react";
import Badge from "../common/Badge";

export interface SidebarItemProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  label: string;
  active?: boolean;
  badge?: string | number;
  badgeVariant?: "default" | "success" | "warning" | "error" | "info";
  collapsed?: boolean;
}

function SidebarItem({
  icon,
  label,
  active = false,
  badge,
  badgeVariant = "default",
  collapsed = false,
  className = "",
  ...rest
}: SidebarItemProps) {
  return (
    <button
      className={`pr-sidebar-item ${className}`.trim()}
      role="menuitem"
      aria-current={active ? "page" : undefined}
      aria-label={label}
      title={collapsed ? label : undefined}
      {...rest}
    >
      {icon && <span className="pr-sidebar-item-icon">{icon}</span>}
      {!collapsed && (
        <>
          <span className="pr-sidebar-item-label">{label}</span>
          {badge !== undefined && (
            <span className="pr-sidebar-item-badge">
              <Badge size="sm" variant={badgeVariant}>{badge}</Badge>
            </span>
          )}
        </>
      )}
    </button>
  );
}

export default SidebarItem;
