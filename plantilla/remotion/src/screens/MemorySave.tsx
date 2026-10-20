import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily, mono } from "../fonts";


// Matches the laptop screen in blender/props.py (0.158 x 0.104 half-extents).
export const LAPTOP_WIDTH = 1216;
export const LAPTOP_HEIGHT = 800;

const TYPE_SPEED = 0.055; // s per character, mirrors reels/schema.py
const TYPE_START = 0.3;
const AMBER = "#ffb45a";
const VISIBLE = 2; // lines that fit on the laptop screen at once

export type MemorySaveProps = {
  title: string;
  lines: string[];
  // Characters (all lines joined) already on screen when the clip starts, and where typing stops (null = end).
  from_char: number;
  to_char: number | null;
  // Read aloud while written: the timeline paces the typing to the voice.
  type_start?: number;
  type_speed?: number;
};

export const MemorySave: React.FC<MemorySaveProps> = ({ title, lines, from_char, to_char, type_start = TYPE_START, type_speed = TYPE_SPEED }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const dots = ".".repeat(1 + (Math.floor(t * 2.2) % 3));
  const pulse = 0.55 + 0.45 * Math.sin(t * 5);

  // One cursor across all lines: from_char + typed so far, capped at to_char.
  const total = lines.reduce((n, l) => n + l.length, 0);
  const stop = Math.min(total, to_char ?? total);
  const cursor = Math.min(stop, (from_char ?? 0) + Math.max(0, Math.floor((t - type_start) / type_speed)));
  let left = cursor;
  const shown = lines.map((line) => {
    const n = Math.max(0, Math.min(line.length, left));
    left -= line.length;
    return line.slice(0, n);
  });
  const typingNow = cursor < stop;
  let caretLine = shown.findIndex((s, i) => s.length < lines[i].length);
  if (caretLine === -1) caretLine = lines.length - 1;
  const caretOn = Math.floor(t * 2.4) % 2 === 0 || typingNow;

  return (
    <AbsoluteFill style={{ background: "radial-gradient(circle at 30% 20%, #241c1a 0%, #120f14 70%)", padding: "70px 80px", color: "#f3e7d3" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 26, fontFamily, fontWeight: 500, fontSize: 46, color: AMBER }}>
        <div style={{ width: 30, height: 30, borderRadius: 15, background: AMBER, opacity: pulse, boxShadow: `0 0 ${30 * pulse}px ${AMBER}` }} />
        <span>
          {title.replace(/…$/, "")}
          <span style={{ display: "inline-block", width: 60 }}>{title.endsWith("…") ? dots : ""}</span>
        </span>
      </div>
      <div style={{ height: 3, background: "rgba(255,180,90,0.25)", margin: "44px 0 50px" }} />
      <div style={{ fontFamily: mono, fontSize: 58, lineHeight: 1.35, display: "flex", flexDirection: "column", gap: 30 }}>
        {shown.map((s, i) =>
          // Long notes scroll like a chat: only the last VISIBLE lines (the one being written and the ones before).
          (s.length > 0 || i === caretLine) && i > caretLine - VISIBLE ? (
            <div key={i} style={{ display: "flex", gap: 28, opacity: i < caretLine ? 0.6 : 1 }}>
              <span style={{ color: AMBER }}>›</span>
              <span>
                {s}
                {i === caretLine && caretOn && <span style={{ background: "#f3e7d3", display: "inline-block", width: 30, height: 62, marginLeft: 4, verticalAlign: "-10px" }} />}
              </span>
            </div>
          ) : null,
        )}
      </div>
    </AbsoluteFill>
  );
};
