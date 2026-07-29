import type { ReactNode } from "react";

export interface SidebarSection {
  label?: string;
  items: SidebarNavItem[];
}

export interface SidebarNavItem {
  id: string;
  label: string;
  icon?: ReactNode;
  badge?: string | number;
  badgeVariant?: "default" | "success" | "warning" | "error" | "info";
  disabled?: boolean;
}

export interface SidebarProps {
  sections: SidebarSection[];
  activeId?: string;
  collapsed?: boolean;
  onNavigate?: (id: string) => void;
  header?: ReactNode;
  footer?: ReactNode;
  title?: string;
  onToggleCollapse?: () => void;
}

function Sidebar({
  sections,
  activeId,
  collapsed = false,
  onNavigate,
  header,
  footer,
  title,
  onToggleCollapse,
}: SidebarProps) {
  return (
    <>
      <div className="pr-sidebar-header">
        {onToggleCollapse && (
          <button
            className="pr-sidebar-toggle"
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand" : "Collapse"}
          >
            {collapsed ? "\u2192" : "\u2190"}
          </button>
        )}
        {!collapsed && title && <span className="pr-sidebar-title">{title}</span>}
        {!collapsed && header}
      </div>
      <nav className="pr-sidebar-nav" role="navigation" aria-label="Main navigation">
        {sections.map((section, idx) => (
          <div key={idx}>
            {!collapsed && section.label && (
              <div className="pr-sidebar-section-label">{section.label}</div>
            )}
            {section.items.map((item) => (
              <button
                key={item.id}
                className="pr-sidebar-item"
                role="menuitem"
                aria-current={activeId === item.id ? "page" : undefined}
                aria-label={collapsed ? item.label : undefined}
                disabled={item.disabled}
                title={collapsed ? item.label : undefined}
                onClick={() => onNavigate?.(item.id)}
              >
                {item.icon && <span className="pr-sidebar-item-icon">{item.icon}</span>}
                {!collapsed && (
                  <>
                    <span className="pr-sidebar-item-label">{item.label}</span>
                    {item.badge !== undefined && (
                      <span className="pr-sidebar-item-badge">
                        <span
                          className={`pr-badge pr-badge-sm pr-badge-${item.badgeVariant || "default"}`}
                        >
                          {item.badge}
                        </span>
                      </span>
                    )}
                  </>
                )}
              </button>
            ))}
          </div>
        ))}
      </nav>
      {!collapsed && footer && <div className="pr-sidebar-footer">{footer}</div>}
    </>
  );
}

export default Sidebar;
