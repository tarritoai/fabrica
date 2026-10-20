import React from "react";
import { mono } from "../fonts";
import { AbsoluteFill, random, useCurrentFrame, useVideoConfig } from "remotion";


// A broken laptop screen in the future: cracked, flickering, the date stuck on screen.
// broken = false: the same screen today, intact and calm (bookends a jump back to the present).
export type DateGlitchProps = { date: string; time: string; broken?: boolean };

export const DateGlitch: React.FC<DateGlitchProps> = ({ date, time, broken = true }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  if (!broken) {
    return (
      <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 45%, #1b2030 0%, #0c0f16 75%)", alignItems: "center", justifyContent: "center" }}>
        <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 250, color: "#eef2ff", textShadow: "0 0 30px rgba(160,190,255,0.5)", letterSpacing: 10 }}>{date}</div>
        <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 70, color: "#aab4d0", marginTop: 10 }}>{time}</div>
      </AbsoluteFill>
    );
  }
  const flicker = random(`f${Math.floor(t * 12)}`) > 0.86 ? 0.35 : 1;
  const shift = random(`s${Math.floor(t * 8)}`) > 0.8 ? (random(`x${frame}`) - 0.5) * 40 : 0;
  const cracks = [
    "M 640 300 L 520 120 L 470 0", "M 640 300 L 820 180 L 1000 160 L 1216 60", "M 640 300 L 700 520 L 660 800",
    "M 640 300 L 380 360 L 120 330 L 0 420", "M 640 300 L 560 460 L 300 640", "M 820 180 L 900 0", "M 700 520 L 980 600 L 1216 700",
  ];
  return (
    <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 45%, #2a0606 0%, #080202 75%)", opacity: flicker }}>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", transform: `translateX(${shift}px)` }}>
        <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 250, color: "#ff3b2f", textShadow: "0 0 40px #ff3b2f, 6px 0 0 rgba(0,200,255,0.35)", letterSpacing: 10 }}>
          {date}
        </div>
        <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 70, color: "#ff6a5a", opacity: 0.85, marginTop: 10 }}>{time}</div>
      </AbsoluteFill>
      {/* Scanlines */}
      <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, rgba(0,0,0,0.35) 0 3px, transparent 3px 7px)" }} />
      <svg width="1216" height="800" style={{ position: "absolute", inset: 0 }}>
        {cracks.map((d, i) => (
          <path key={i} d={d} stroke="rgba(255,255,255,0.75)" strokeWidth={i < 4 ? 4 : 2} fill="none" />
        ))}
        <circle cx="640" cy="300" r="26" fill="rgba(255,255,255,0.35)" />
      </svg>
    </AbsoluteFill>
  );
};
