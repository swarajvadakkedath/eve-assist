import { useState, useCallback, useRef, useEffect, type ReactNode, type HTMLAttributes } from "react";

export interface ResizableLayoutProps extends HTMLAttributes<HTMLDivElement> {
  sidebar: ReactNode;
  children: ReactNode;
  defaultSidebarWidth?: number;
  minSidebarWidth?: number;
  maxSidebarWidth?: number;
  collapsed?: boolean;
  onCollapsedChange?: (collapsed: boolean) => void;
  collapsible?: boolean;
}

function ResizableLayout({
  sidebar,
  children,
  defaultSidebarWidth = 260,
  minSidebarWidth = 200,
  maxSidebarWidth = 400,
  collapsed = false,
  onCollapsedChange,
  collapsible = true,
  className = "",
  ...rest
}: ResizableLayoutProps) {
  const [sidebarWidth, setSidebarWidth] = useState(defaultSidebarWidth);
  const dragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (collapsed) {
      setSidebarWidth(defaultSidebarWidth);
    }
  }, [collapsed, defaultSidebarWidth]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const newWidth = e.clientX - rect.left;
    setSidebarWidth(Math.max(minSidebarWidth, Math.min(maxSidebarWidth, newWidth)));
  }, [minSidebarWidth, maxSidebarWidth]);

  const handleMouseUp = useCallback(() => {
    if (!dragging.current) return;
    dragging.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  return (
    <div
      ref={containerRef}
      className={`pr-resizable-layout pr-resizable-layout-horizontal ${className}`.trim()}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      role="group"
      aria-label="Resizable layout"
      {...rest}
    >
      <div
        className={`pr-sidebar ${collapsed ? "pr-sidebar-collapsed" : "pr-sidebar-expanded"}`}
        style={collapsed ? {} : { width: sidebarWidth }}
        aria-label="Sidebar"
      >
        {sidebar}
        {collapsible && !collapsed && (
          <div
            className="pr-sidebar-resize-handle"
            onMouseDown={handleMouseDown}
            role="separator"
            aria-label="Resize sidebar"
            aria-valuemin={minSidebarWidth}
            aria-valuemax={maxSidebarWidth}
            aria-valuenow={sidebarWidth}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "ArrowLeft") {
                setSidebarWidth(Math.max(minSidebarWidth, sidebarWidth - 20));
              } else if (e.key === "ArrowRight") {
                setSidebarWidth(Math.min(maxSidebarWidth, sidebarWidth + 20));
              }
            }}
          />
        )}
      </div>
      <div className="pr-workspace">
        {children}
      </div>
    </div>
  );
}

export default ResizableLayout;
