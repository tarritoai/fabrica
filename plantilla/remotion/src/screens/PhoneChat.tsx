import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily } from "../fonts";

// A generic AI chat app (no real logos or brand UI): the user's bubbles on the right, the assistant's on the left.
export type ChatMessage = { from_user: boolean; text: string };
export type PhoneChatProps = {
  app_name: string;
  messages: ChatMessage[];
  // Seconds into the clip when the last message pops in (null = everything already there).
  last_at: number | null;
};

export const PhoneChat: React.FC<PhoneChatProps> = ({ app_name, messages, last_at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{ fontFamily, background: "#0f1115", color: "#eef0f4" }}>
      <div style={{ height: 150, display: "flex", alignItems: "flex-end", padding: "0 44px 26px", gap: 22, borderBottom: "2px solid #1d2028" }}>
        <div style={{ width: 64, height: 64, borderRadius: 32, background: "linear-gradient(140deg,#6b7280,#3b4252)" }} />
        <div style={{ fontSize: 44, fontWeight: 700 }}>{app_name}</div>
      </div>
      {/* Messages sit in the upper half: the hand holding the phone covers the bottom. */}
      <div style={{ display: "flex", flexDirection: "column", gap: 34, padding: "90px 36px", justifyContent: "flex-start", flex: 1 }}>
        {messages.map((m, i) => {
          const isLast = i === messages.length - 1 && last_at !== null;
          const k = isLast ? interpolate(t, [last_at!, last_at! + 0.2], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
          return (
            <div
              key={i}
              style={{
                alignSelf: m.from_user ? "flex-end" : "flex-start",
                maxWidth: "78%",
                padding: "26px 34px",
                borderRadius: 40,
                fontSize: 66,
                fontWeight: 600,
                lineHeight: 1.25,
                background: m.from_user ? "#3a6df0" : "#22262f",
                opacity: k,
                transform: `translateY(${(1 - k) * 30}px)`,
              }}
            >
              {m.text}
            </div>
          );
        })}
      </div>
      <div style={{ height: 130, margin: "0 30px 40px", borderRadius: 65, background: "#1a1d24" }} />
    </AbsoluteFill>
  );
};
