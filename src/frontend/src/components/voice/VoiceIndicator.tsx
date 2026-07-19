import { useState, useEffect } from "react";
import { voiceService } from "../../services/voice";

interface VoiceIndicatorProps {
  compact?: boolean;
}

export default function VoiceIndicator({ compact = false }: VoiceIndicatorProps) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [state, setState] = useState("idle");

  useEffect(() => {
    const update = () => {
      const s = voiceService.state;
      setIsListening(s.isListening);
      setIsSpeaking(s.isSpeaking);
      setState(s.state);
    };

    const unsubs = [
      voiceService.on("voice:listening:start", update),
      voiceService.on("voice:listening:stop", update),
      voiceService.on("voice:speaking:start", update),
      voiceService.on("voice:speaking:stop", update),
      voiceService.on("voice:state:change", update),
    ];

    update();

    return () => unsubs.forEach((u) => u());
  }, []);

  if (state === "idle" && !isListening && !isSpeaking) return null;

  const indicatorClass = isListening ? "listening" : isSpeaking ? "speaking" : "idle";
  const label = isListening
    ? "Listening"
    : isSpeaking
    ? "Speaking"
    : "Idle";

  if (compact) {
    return (
      <div className={`voice-indicator-compact ${indicatorClass}`}>
        <span className="voice-indicator-dot" />
      </div>
    );
  }

  return (
    <div className={`voice-indicator ${indicatorClass}`}>
      <span className="voice-indicator-dot" />
      <span className="voice-indicator-pulse" />
      <span className="voice-indicator-label">{label}</span>
    </div>
  );
}
