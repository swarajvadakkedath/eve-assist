import { useState, useEffect, useRef } from "react";
import { voiceService } from "../../services/voice";

interface TranscriptPanelProps {
  maxItems?: number;
  compact?: boolean;
}

interface TranscriptItem {
  id: string;
  text: string;
  timestamp: number;
  isFinal: boolean;
}

export default function TranscriptPanel({ maxItems = 50, compact = false }: TranscriptPanelProps) {
  const [transcripts, setTranscripts] = useState<TranscriptItem[]>([]);
  const [partialText, setPartialText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const idCounter = useRef(0);

  useEffect(() => {
    const unsub1 = voiceService.on("voice:transcript:partial", (e) => {
      setPartialText(e.data?.text || "");
    });

    const unsub2 = voiceService.on("voice:transcript:final", (e) => {
      const text = e.data?.text || "";
      if (!text.trim()) return;
      setPartialText("");
      setTranscripts((prev) => {
        const next = [
          ...prev,
          {
            id: `t-${idCounter.current++}`,
            text,
            timestamp: Date.now(),
            isFinal: true,
          },
        ];
        return next.slice(-maxItems);
      });
    });

    return () => {
      unsub1();
      unsub2();
    };
  }, [maxItems]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcripts, partialText]);

  if (compact && transcripts.length === 0 && !partialText) return null;

  return (
    <div className={`transcript-panel ${compact ? "transcript-compact" : ""}`} ref={scrollRef}>
      {transcripts.map((t) => (
        <div key={t.id} className="transcript-item transcript-final">
          <span className="transcript-text">{t.text}</span>
        </div>
      ))}
      {partialText && (
        <div className="transcript-item transcript-partial">
          <span className="transcript-text">{partialText}</span>
          <span className="transcript-cursor">|</span>
        </div>
      )}
      {transcripts.length === 0 && !partialText && !compact && (
        <div className="transcript-empty">Transcript will appear here...</div>
      )}
    </div>
  );
}
