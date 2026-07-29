import { useState, useCallback, useRef, type ReactNode, type HTMLAttributes } from "react";

export interface SplitPaneProps extends HTMLAttributes<HTMLDivElement> {
  children: [ReactNode, ReactNode];
  direction?: "horizontal" | "vertical";
  defaultSize?: number;
  minSize?: number;
  maxSize?: number;
}

function SplitPane({
  children,
  direction = "horizontal",
  defaultSize = 300,
  minSize = 100,
  maxSize = 800,
  className = "",
  ...rest
}: SplitPaneProps) {
  const [splitSize, setSplitSize] = useState(defaultSize);
  const dragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = direction === "horizontal" ? "col-resize" : "row-resize";
    document.body.style.userSelect = "none";
  }, [direction]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!dragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    let newSize: number;
    if (direction === "horizontal") {
      newSize = e.clientX - rect.left;
    } else {
      newSize = e.clientY - rect.top;
    }
    setSplitSize(Math.max(minSize, Math.min(maxSize, newSize)));
  }, [direction, minSize, maxSize]);

  const handleMouseUp = useCallback(() => {
    if (!dragging.current) return;
    dragging.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  const sizeProp = direction === "horizontal" ? "width" : "height";

  return (
    <div
      ref={containerRef}
      className={`pr-split-pane pr-split-pane-${direction} ${className}`.trim()}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      role="group"
      aria-label="Split pane"
      {...rest}
    >
      <div className="pr-split-pane-panel" style={{ [sizeProp]: splitSize, flex: "0 0 auto" }}>
        {children[0]}
      </div>
      <div
        className="pr-split-pane-gutter"
        onMouseDown={handleMouseDown}
        role="separator"
        aria-label="Resize"
        aria-valuemin={minSize}
        aria-valuemax={maxSize}
        aria-valuenow={splitSize}
        tabIndex={0}
        onKeyDown={(e) => {
          const step = direction === "horizontal" ? 20 : 20;
          if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
            setSplitSize(Math.max(minSize, splitSize - step));
          } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
            setSplitSize(Math.min(maxSize, splitSize + step));
          }
        }}
      />
      <div className="pr-split-pane-panel">
        {children[1]}
      </div>
    </div>
  );
}

export default SplitPane;
