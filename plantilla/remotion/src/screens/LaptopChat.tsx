import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily, mono } from "../fonts";
import type { ChatMessage } from "./PhoneChat";


// A generic AI chat open on the novato's laptop (no real logos or brand UI). Big type and generous margins:
// it has to read in screen_closeup, and the bezel and the camera angle eat the edges.
// code: an optional snippet under the assistant's last reply (small; a detail for whoever pauses the video).
// variant: the regenerate button (↻) and the "n/n" answer counter under the last reply; every regen_at press
// bumps the counter and pops the reply in again (regenerar-coro).
// theme: "tarro" (cream) / "tarro_noche" (warm dark) dress the chat in our jar's own clay and glaze, with the jar
// as its icon, so it reads as *his* chat without copying any real app.
export type LaptopChatTheme = "neutral" | "tarro" | "tarro_noche";

const THEMES: Record<LaptopChatTheme, Record<string, string>> = {
  neutral: { bg: "#0f1115", fg: "#eef0f4", title: "#c7ccd8", rule: "#1d2028", user: "#3a6df0", userFg: "#eef0f4", ai: "#22262f",
             aiFg: "#eef0f4", btn: "#1a1d25", btnOn: "#3a4152", btnBorder: "#2c313d", btnFg: "#aab1c0", count: "#8b92a3" },
  tarro: { bg: "#f4ede1", fg: "#2b1a12", title: "#5a3020", rule: "#e3d6c3", user: "#e6d9c6", userFg: "#2b1a12", ai: "#a84f2c",
           aiFg: "#fff6ec", btn: "#ebe0cf", btnOn: "#d8c6ad", btnBorder: "#d2c0a6", btnFg: "#7a4a32", count: "#7a4a32" },
  tarro_noche: { bg: "#1d1410", fg: "#f6e9dc", title: "#e7c3a6", rule: "#33241c", user: "#3a2a21", userFg: "#f6e9dc", ai: "#a84f2c",
                 aiFg: "#fff6ec", btn: "#2a1d17", btnOn: "#4a3328", btnBorder: "#4a3328", btnFg: "#e7c3a6", count: "#c9a184" },
};

// Our jar (clay body, glazed lid with a knob), not any real logo.
const JarIcon: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 40 40">
    <rect x="6" y="14" width="28" height="22" rx="7" fill="#a84f2c" />
    <ellipse cx="20" cy="14" rx="16" ry="5" fill="#1f9e9a" />
    <circle cx="20" cy="8.5" r="3" fill="#1f9e9a" />
    <circle cx="15" cy="23" r="2" fill="#2b1a12" />
    <circle cx="25" cy="23" r="2" fill="#2b1a12" />
  </svg>
);

export type LaptopChatProps = {
  app_name: string;
  messages: ChatMessage[];
  code?: string | null;
  last_at?: number | null; // seconds into the clip when the last message pops in (null = all there)
  variant?: number | null;
  regen_at?: number[];
  theme?: LaptopChatTheme;
  text_scale?: number; // bigger bubbles for a short chat that has to read in the first second (1 = default)
};

const PRESS = 0.16; // seconds the button looks pressed

export const LaptopChat: React.FC<LaptopChatProps> = ({ app_name, messages, code = null, last_at = null, variant = null, regen_at = [], theme = "neutral", text_scale = 1 }) => {
  const z = text_scale;
  const c = THEMES[theme] ?? THEMES.neutral;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const presses = regen_at.filter((p) => p <= t);
  const lastPress = presses.length ? presses[presses.length - 1] : null;
  const pressed = lastPress !== null && t - lastPress < PRESS;
  const popAt = lastPress ?? last_at;
  return (
    <AbsoluteFill style={{ fontFamily, background: c.bg, color: c.fg, padding: "56px 110px 40px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18, paddingBottom: 22, borderBottom: `2px solid ${c.rule}` }}>
        {theme === "neutral" ? (
          <div style={{ width: 40, height: 40, borderRadius: 20, background: "linear-gradient(140deg,#6b7280,#3b4252)" }} />
        ) : (
          <JarIcon size={48} />
        )}
        <div style={{ fontSize: 34, fontWeight: 700, color: c.title }}>{app_name}</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 26 * z, paddingTop: 34 }}>
        {messages.map((m, i) => {
          // A regenerated answer blinks out with the press and pops back in.
          const isLast = i === messages.length - 1 && popAt !== null;
          const from = popAt! + (lastPress !== null ? PRESS : 0);
          const k = isLast ? interpolate(t, [from, from + 0.2], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
          return (
            <div
              key={i}
              style={{
                alignSelf: m.from_user ? "flex-end" : "flex-start",
                maxWidth: z > 1 ? "100%" : "82%",
                padding: `${18 * z}px ${28 * z}px`,
                borderRadius: 30,
                fontSize: 50 * z,
                fontWeight: 600,
                lineHeight: 1.22,
                background: m.from_user ? c.user : c.ai,
                color: m.from_user ? c.userFg : c.aiFg,
                opacity: k,
                transform: `translateY(${(1 - k) * 24}px)`,
              }}
            >
              {m.text}
            </div>
          );
        })}
        {variant !== null && (
          <div style={{ display: "flex", alignItems: "center", gap: 26, marginTop: 4, paddingLeft: 4, color: c.count }}>
            <div
              style={{
                width: 104,
                height: 104,
                borderRadius: 52,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: `3px solid ${c.btnBorder}`,
                background: pressed ? c.btnOn : c.btn,
                color: pressed ? c.fg : c.btnFg,
                transform: `scale(${pressed ? 0.9 : 1})`,
              }}
            >
              {/* ↻ drawn, not typed: the UI font has no arrow glyphs */}
              <svg width="66" height="66" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 12a8 8 0 1 1-2.34-5.66" />
                <path d="M20 4v5h-5" />
              </svg>
            </div>
            <div style={{ fontSize: 64, fontWeight: 700, letterSpacing: 1 }}>
              {variant + presses.length}/{variant + presses.length}
            </div>
          </div>
        )}
        {code && (
          <pre
            style={{
              margin: 0,
              alignSelf: "flex-start",
              maxWidth: "82%",
              padding: "18px 26px",
              borderRadius: 18,
              background: "#161922",
              border: "2px solid #232838",
              fontFamily: mono,
              fontSize: 26,
              lineHeight: 1.45,
              color: "#9fb4e8",
              whiteSpace: "pre-wrap",
            }}
          >
            {code}
          </pre>
        )}
      </div>
    </AbsoluteFill>
  );
};
