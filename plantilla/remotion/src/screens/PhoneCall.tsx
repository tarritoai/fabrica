import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily } from "../fonts";
import { style } from "../style";

export type PhoneCallProps = {
  contact: string;
  // Seconds ringing before the call connects; null = nobody answers.
  connect_after: number | null;
};

const pad = (n: number) => String(n).padStart(2, "0");

const RoundButton: React.FC<{ color: string; label: string; glyph: string }> = ({ color, label, glyph }) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
    <div
      style={{
        width: 128,
        height: 128,
        borderRadius: 64,
        background: color,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 54,
        color: "white",
      }}
    >
      {glyph}
    </div>
    <span style={{ fontSize: 26, color: "#c9ccd6" }}>{label}</span>
  </div>
);

export const PhoneCall: React.FC<PhoneCallProps> = ({ contact, connect_after }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const connected = connect_after !== null && t >= connect_after;
  const elapsed = connected ? Math.floor(t - (connect_after ?? 0)) : 0;
  const dots = ".".repeat(1 + (Math.floor(t * 2.5) % 3));
  const ring = connected ? 0 : (t * 1.2) % 1;

  return (
    <AbsoluteFill
      style={{
        fontFamily,
        background: `radial-gradient(circle at 50% 30%, #2a2f45 0%, ${style.background_blue} 55%, #000 100%)`,
        alignItems: "center",
        color: "white",
      }}
    >
      <div style={{ marginTop: 230, position: "relative", width: 260, height: 260 }}>
        {!connected && (
          <div
            style={{
              position: "absolute",
              inset: -60 * ring,
              borderRadius: "50%",
              border: `4px solid rgba(255,255,255,${interpolate(ring, [0, 1], [0.5, 0])})`,
            }}
          />
        )}
        <div
          style={{
            width: 260,
            height: 260,
            borderRadius: 130,
            background: "linear-gradient(160deg, #8a7bb8, #4b5a8f)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 130,
            fontWeight: 500,
          }}
        >
          {contact.slice(0, 1).toUpperCase()}
        </div>
      </div>
      <div style={{ fontSize: 92, fontWeight: 500, marginTop: 60 }}>{contact}</div>
      <div style={{ fontSize: 40, color: "#c9ccd6", marginTop: 14, height: 50 }}>
        {connected ? `${pad(Math.floor(elapsed / 60))}:${pad(elapsed % 60)}` : `llamando${dots}`}
      </div>
      <div style={{ position: "absolute", bottom: 170, display: "flex", gap: 90 }}>
        <RoundButton color="rgba(255,255,255,0.18)" label="silencio" glyph="🎙" />
        <RoundButton color="#ff3b30" label="colgar" glyph="✆" />
        <RoundButton color="rgba(255,255,255,0.18)" label="altavoz" glyph="🔊" />
      </div>
    </AbsoluteFill>
  );
};
