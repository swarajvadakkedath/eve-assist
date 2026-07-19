import { useRef, useState, useCallback, useEffect } from "react";

interface Region {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface RegionSelectionOverlayProps {
  onRegionSelected: (region: Region) => void;
  onCancel: () => void;
  imageUrl?: string;
}

export default function RegionSelectionOverlay({ onRegionSelected, onCancel, imageUrl }: RegionSelectionOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [start, setStart] = useState<{ x: number; y: number } | null>(null);
  const [current, setCurrent] = useState<{ x: number; y: number } | null>(null);
  const [selecting, setSelecting] = useState(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setStart({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setSelecting(true);
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!selecting || !start) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setCurrent({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  }, [selecting, start]);

  const handleMouseUp = useCallback(() => {
    if (!start || !current) return;
    const x = Math.min(start.x, current.x);
    const y = Math.min(start.y, current.y);
    const w = Math.abs(current.x - start.x);
    const h = Math.abs(current.y - start.y);
    if (w > 10 && h > 10) {
      onRegionSelected({ x, y, width: w, height: h });
    }
    setSelecting(false);
    setStart(null);
    setCurrent(null);
  }, [start, current, onRegionSelected]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onCancel]);

  const selectionStyle = start && current ? {
    left: Math.min(start.x, current.x),
    top: Math.min(start.y, current.y),
    width: Math.abs(current.x - start.x),
    height: Math.abs(current.y - start.y),
  } : null;

  return (
    <div className="vision-region-overlay" onClick={onCancel}>
      <div
        ref={containerRef}
        className="vision-region-container"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onClick={(e) => e.stopPropagation()}
      >
        {imageUrl && <img src={imageUrl} alt="Screen" className="vision-region-image" draggable={false} />}
        {selectionStyle && (
          <div className="vision-selection-box" style={selectionStyle}>
            <span className="vision-selection-size">{selectionStyle.width}×{selectionStyle.height}</span>
          </div>
        )}
        {!selecting && (
          <div className="vision-region-hint">Click and drag to select a region. Press Esc to cancel.</div>
        )}
      </div>
    </div>
  );
}
