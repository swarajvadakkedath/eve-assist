import { useEffect, useRef, useState } from "react";
import { api } from "../../services/api";

interface LivePreviewProps {
  interval?: number;
  autoStart?: boolean;
  onClose?: () => void;
}

export default function LivePreview({ interval = 2000, autoStart = false, onClose }: LivePreviewProps) {
  const [active, setActive] = useState(autoStart);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [error, setError] = useState("");

  const capture = async () => {
    try {
      const data = await api.vision.capture("full_screen") as { image: string };
      setImageUrl(data.image);
      setError("");
    } catch {
      // silent for live preview
    }
  };

  useEffect(() => {
    if (active) {
      capture();
      intervalRef.current = setInterval(capture, interval);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [active, interval]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActive(false);
        onClose?.();
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  return (
    <div className="vision-live-preview">
      <div className="vision-live-header">
        <h3>Live Preview</h3>
        <div className="vision-live-controls">
          <button
            className={`vision-btn ${active ? "active" : ""}`}
            onClick={() => setActive(!active)}
          >
            {active ? "Stop" : "Start"}
          </button>
          {onClose && <button className="vision-btn" onClick={onClose}>Close</button>}
        </div>
      </div>

      {error && <div className="vision-error">{error}</div>}

      <div className="vision-live-content">
        {imageUrl ? (
          <img src={imageUrl} alt="Live screen" className="vision-live-image" />
        ) : (
          <div className="vision-live-placeholder">
            {active ? "Capturing..." : "Click Start to begin live capture"}
          </div>
        )}
        {active && <div className="vision-live-indicator">● Live</div>}
      </div>
    </div>
  );
}
