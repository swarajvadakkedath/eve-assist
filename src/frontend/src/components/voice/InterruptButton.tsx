import { useState, useEffect } from "react";
import { voiceService } from "../../services/voice";

export default function InterruptButton() {
  const [isSpeaking, setIsSpeaking] = useState(false);

  useEffect(() => {
    const unsub1 = voiceService.on("voice:speaking:start", () => setIsSpeaking(true));
    const unsub2 = voiceService.on("voice:speaking:stop", () => setIsSpeaking(false));
    const unsub3 = voiceService.on("voice:state:change", (e) => {
      if (e.data?.state !== "speaking") setIsSpeaking(false);
    });
    return () => {
      unsub1();
      unsub2();
      unsub3();
    };
  }, []);

  if (!isSpeaking) return null;

  const handleInterrupt = async () => {
    try {
      await voiceService.bargeIn();
    } catch (e) {
      console.error("interrupt error", e);
    }
  };

  return (
    <button className="interrupt-button" onClick={handleInterrupt} title="Interrupt Eve">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="interrupt-icon">
        <rect x="6" y="4" width="4" height="16" />
        <rect x="14" y="4" width="4" height="16" />
      </svg>
      <span className="interrupt-label">Stop</span>
    </button>
  );
}
