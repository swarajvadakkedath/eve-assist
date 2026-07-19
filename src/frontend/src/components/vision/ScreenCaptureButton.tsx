import { useState } from "react";
import { api } from "../../services/api";

interface ScreenCaptureButtonProps {
  onCapture?: (data: { image: string; width: number; height: number }) => void;
  onError?: (error: string) => void;
}

export default function ScreenCaptureButton({ onCapture, onError }: ScreenCaptureButtonProps) {
  const [capturing, setCapturing] = useState(false);

  const handleCapture = async () => {
    setCapturing(true);
    try {
      const data = await api.vision.capture("full_screen");
      onCapture?.(data as { image: string; width: number; height: number });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Capture failed";
      onError?.(msg);
    } finally {
      setCapturing(false);
    }
  };

  return (
    <button
      className="vision-btn capture-btn"
      onClick={handleCapture}
      disabled={capturing}
      title="Capture screen"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
        <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
        <circle cx="12" cy="13" r="4" />
      </svg>
      {capturing ? "Capturing..." : "Screen"}
    </button>
  );
}
