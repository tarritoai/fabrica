import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily, mono } from "../fonts";


// A calm system message on the novato's laptop: a notice, or a countdown that really ticks
// (countdown_from seconds at the start of the beat, down to zero). Generous margins: the laptop
// bezel and the camera angle eat the edges of the screen.
// battery: a laptop running on its last charge, shown big (it drains beat by beat: each beat sets its own value;
// 0 = the screen goes black).
export type SystemNoticeProps = { title: string; text?: string; countdown_from?: number | null; battery?: number | null };

const Battery: React.FC<{ level: number }> = ({ level }) => {
  const color = level <= 3 ? "#ff5a5a" : level <= 10 ? "#ffb347" : "#7ddc8a";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 48, marginTop: 40 }}>
      <div style={{ display: "flex", alignItems: "center" }}>
        <div style={{ width: 300, height: 150, border: "10px solid #eef2ff", borderRadius: 30, padding: 14, boxSizing: "border-box" }}>
          <div style={{ width: `${Math.max(4, level)}%`, height: "100%", borderRadius: 12, background: color, boxShadow: `0 0 30px ${color}` }} />
        </div>
        <div style={{ width: 22, height: 60, background: "#eef2ff", borderRadius: "0 10px 10px 0" }} />
      </div>
      <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 170, color, textShadow: `0 0 30px ${color}66` }}>{level}%</div>
    </div>
  );
};

const pad = (n: number) => String(n).padStart(2, "0");

export const SystemNotice: React.FC<SystemNoticeProps> = ({ title, text = "", countdown_from = null, battery = null }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  // Battery at zero: the screen is dead.
  if (battery === 0) return <AbsoluteFill style={{ background: "#000" }} />;
  const left = countdown_from === null ? null : Math.max(0, Math.ceil(countdown_from - t));
  return (
    <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 40%, #1b2030 0%, #0c0f16 80%)", padding: "120px 130px", justifyContent: "center", color: "#eef2ff" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 22, fontFamily, fontWeight: 600, fontSize: 44, color: "#aab4d0" }}>
        <div style={{ width: 22, height: 22, borderRadius: 11, background: "#8fb0ff", boxShadow: "0 0 18px #8fb0ff" }} />
        {title}
      </div>
      {battery !== null ? (
        <Battery level={battery} />
      ) : left !== null ? (
        <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 170, letterSpacing: 6, marginTop: 30, textShadow: "0 0 30px rgba(160,190,255,0.45)" }}>
          00:{pad(Math.floor(left / 60))}:{pad(left % 60)}
        </div>
      ) : (
        <div style={{ fontFamily, fontWeight: 600, fontSize: 64, lineHeight: 1.3, marginTop: 34 }}>{text}</div>
      )}
    </AbsoluteFill>
  );
};
