import { useState, useEffect, useRef } from "react";
import { voiceService } from "../../services/voice";

interface VoiceButtonProps {
  onTranscript?: (text: string) => void;
  onStateChange?: (state: string) => void;
  pushToTalkKey?: string;
}

export default function VoiceButton({ onTranscript, onStateChange, pushToTalkKey = "v" }: VoiceButtonProps) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [showTooltip, setShowTooltip] = useState(false);
  const pushToTalkHeld = useRef(false);

  useEffect(() => {
    const unsub1 = voiceService.on("voice:listening:start", () => {
      setIsListening(true);
      onStateChange?.("listening");
    });
    const unsub2 = voiceService.on("voice:listening:stop", () => {
      setIsListening(false);
      onStateChange?.("idle");
    });
    const unsub3 = voiceService.on("voice:speaking:start", () => {
      setIsSpeaking(true);
      onStateChange?.("speaking");
    });
    const unsub4 = voiceService.on("voice:speaking:stop", () => {
      setIsSpeaking(false);
      onStateChange?.("idle");
    });
    const unsub5 = voiceService.on("voice:audio:level", (e) => {
      setAudioLevel(e.data?.level || 0);
    });
    const unsub6 = voiceService.on("voice:transcript:final", (e) => {
      if (e.data?.text) {
        onTranscript?.(e.data.text);
      }
    });

    return () => {
      unsub1();
      unsub2();
      unsub3();
      unsub4();
      unsub5();
      unsub6();
    };
  }, [onTranscript, onStateChange]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === pushToTalkKey && !e.repeat && !isTargetInput(e)) {
        e.preventDefault();
        pushToTalkHeld.current = true;
        toggleListening();
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === pushToTalkKey && pushToTalkHeld.current) {
        e.preventDefault();
        pushToTalkHeld.current = false;
        if (isListening) {
          toggleListening();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [isListening, pushToTalkKey]);

  const toggleListening = async () => {
    try {
      await voiceService.connect();
      if (isListening) {
        await voiceService.stopListening();
      } else {
        await voiceService.startListening();
      }
    } catch (e) {
      console.error("voice toggle error", e);
    }
  };

  const getButtonClass = () => {
    if (isListening) return "voice-btn listening";
    if (isSpeaking) return "voice-btn speaking";
    return "voice-btn";
  };

  return (
    <div
      className="voice-button-wrapper"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <button
        className={getButtonClass()}
        onClick={toggleListening}
        title={`Push-to-talk: ${pushToTalkKey.toUpperCase()} key`}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="voice-mic-icon">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
        {isListening && (
          <div className="voice-audio-ring">
            <div
              className="voice-audio-level"
              style={{ transform: `scale(${1 + audioLevel * 0.5})` }}
            />
          </div>
        )}
      </button>
      {showTooltip && (
        <div className="voice-tooltip">
          {isListening ? "Listening..." : isSpeaking ? "Speaking..." : `Press ${pushToTalkKey.toUpperCase()} to talk`}
        </div>
      )}
    </div>
  );
}

function isTargetInput(e: KeyboardEvent): boolean {
  const target = e.target as HTMLElement;
  return target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;
}
