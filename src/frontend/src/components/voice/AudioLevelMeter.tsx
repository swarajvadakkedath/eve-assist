import { useState, useEffect, useRef } from "react";
import { voiceService } from "../../services/voice";

interface AudioLevelMeterProps {
  barCount?: number;
  height?: number;
  width?: number;
}

export default function AudioLevelMeter({
  barCount = 20,
  height = 24,
  width = 120,
}: AudioLevelMeterProps) {
  const [level, setLevel] = useState(0);
  const [active, setActive] = useState(false);
  const animRef = useRef<number>();

  useEffect(() => {
    const unsub1 = voiceService.on("voice:listening:start", () => setActive(true));
    const unsub2 = voiceService.on("voice:listening:stop", () => {
      setActive(false);
      setLevel(0);
    });
    const unsub3 = voiceService.on("voice:audio:level", (e) => {
      setLevel(e.data?.level || 0);
    });

    const animate = () => {
      if (active) {
        setLevel((prev) => {
          const s = voiceService.state.audioLevel;
          return s > 0 ? s : Math.max(0, prev - 0.02);
        });
      }
      animRef.current = requestAnimationFrame(animate);
    };
    animRef.current = requestAnimationFrame(animate);

    return () => {
      unsub1();
      unsub2();
      unsub3();
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [active]);

  if (!active) return null;

  return (
    <div className="audio-level-meter" style={{ width, height }}>
      {Array.from({ length: barCount }).map((_, i) => {
        const barLevel = Math.max(0, Math.min(1, (i + 1) / barCount));
        const isActive = level >= barLevel;
        return (
          <div
            key={i}
            className={`audio-level-bar ${isActive ? "active" : ""}`}
            style={{
              height: `${((i + 1) / barCount) * 100}%`,
            }}
          />
        );
      })}
    </div>
  );
}
