import { useEffect, useState, useCallback } from "react";
import { api } from "../../services/api";

interface Observation {
  id: string;
  summary: string;
  ocrText: string;
  ocrConfidence: number;
  elementCount: number;
  uiElements: Array<{ type: string; text: string; x: number; y: number; w: number; h: number }>;
  layout: Array<{ type: string; x: number; y: number; w: number; h: number; label: string }>;
  durationMs: number;
}

interface ObservationPanelProps {
  onClose?: () => void;
}

export default function ObservationPanel({ onClose }: ObservationPanelProps) {
  const [observation, setObservation] = useState<Observation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchObservation = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.vision.analyze("full_screen");
      setObservation(data as unknown as Observation);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to observe screen");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchObservation();
  }, [fetchObservation]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  return (
    <div className="vision-panel">
      <div className="vision-panel-header">
        <h3>Screen Observation</h3>
        <div className="vision-panel-actions">
          <button className="vision-btn" onClick={fetchObservation} disabled={loading}>
            {loading ? "Analyzing..." : "Refresh"}
          </button>
          {onClose && <button className="vision-btn" onClick={onClose}>Close</button>}
        </div>
      </div>

      {error && <div className="vision-error">{error}</div>}

      {observation && (
        <div className="vision-observation-content">
          <div className="vision-obs-summary">{observation.summary}</div>

          <div className="vision-obs-stats">
            <div className="vision-stat">
              <span className="vision-stat-value">{observation.elementCount}</span>
              <span className="vision-stat-label">UI Elements</span>
            </div>
            <div className="vision-stat">
              <span className="vision-stat-value">{(observation.ocrConfidence * 100).toFixed(0)}%</span>
              <span className="vision-stat-label">OCR Confidence</span>
            </div>
            <div className="vision-stat">
              <span className="vision-stat-value">{observation.durationMs.toFixed(0)}ms</span>
              <span className="vision-stat-label">Duration</span>
            </div>
          </div>

          {observation.ocrText && (
            <div className="vision-section">
              <button
                className="vision-section-header"
                onClick={() => setExpanded(expanded === "ocr" ? null : "ocr")}
              >
                <span>OCR Text</span>
                <span>{expanded === "ocr" ? "▾" : "▸"}</span>
              </button>
              {expanded === "ocr" && (
                <pre className="vision-ocr-text">{observation.ocrText}</pre>
              )}
            </div>
          )}

          {observation.uiElements.length > 0 && (
            <div className="vision-section">
              <button
                className="vision-section-header"
                onClick={() => setExpanded(expanded === "elements" ? null : "elements")}
              >
                <span>UI Elements ({observation.uiElements.length})</span>
                <span>{expanded === "elements" ? "▾" : "▸"}</span>
              </button>
              {expanded === "elements" && (
                <div className="vision-element-list">
                  {observation.uiElements.map((el, i) => (
                    <div key={i} className="vision-element-item">
                      <span className="vision-element-type">{el.type}</span>
                      <span className="vision-element-text">{el.text}</span>
                      <span className="vision-element-pos">{el.x},{el.y} {el.w}×{el.h}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {observation.layout.length > 0 && (
            <div className="vision-section">
              <button
                className="vision-section-header"
                onClick={() => setExpanded(expanded === "layout" ? null : "layout")}
              >
                <span>Layout Regions ({observation.layout.length})</span>
                <span>{expanded === "layout" ? "▾" : "▸"}</span>
              </button>
              {expanded === "layout" && (
                <div className="vision-layout-list">
                  {observation.layout.map((r, i) => (
                    <div key={i} className="vision-layout-item">
                      <span className="vision-layout-type">{r.type}</span>
                      <span className="vision-layout-label">{r.label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
