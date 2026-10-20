import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily } from "../fonts";
import { style } from "../style";

export type CounterRevealProps = { value: number; label: string; footnote?: string | null };

// Full-screen data card over the darkened shot: the number counts up, lands, pulses.
export const CounterReveal: React.FC<CounterRevealProps & { durationInFrames: number }> = ({
  value,
  label,
  footnote,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const countEnd = Math.round(1.6 * fps);
  const shown = Math.round(
    interpolate(frame, [6, countEnd], [0, value], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }),
  );
  const backdrop = interpolate(frame, [0, 8, durationInFrames - 8, durationInFrames], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });
  const land = spring({ frame: frame - countEnd, fps, config: { damping: 9, stiffness: 160 } });
  const scale = 1 + 0.12 * land * (1 - land) * 4;
  const labelIn = interpolate(frame, [countEnd - 4, countEnd + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill
      style={{
        opacity: backdrop,
        background: "rgba(4, 6, 14, 0.72)",
        backdropFilter: "blur(14px)",
        alignItems: "center",
        justifyContent: "center",
        fontFamily,
        color: "white",
        textAlign: "center",
        padding: "0 90px",
      }}
    >
      <div
        style={{
          fontSize: 340,
          fontWeight: 900,
          lineHeight: 1,
          transform: `scale(${scale})`,
          textShadow: `0 0 60px ${style.accent}66`,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {shown.toLocaleString("es-ES")}
      </div>
      <div style={{ fontSize: 58, fontWeight: 700, marginTop: 30, opacity: labelIn, lineHeight: 1.2 }}>{label}</div>
      {footnote && (
        <div style={{ position: "absolute", bottom: 380, fontSize: 30, color: "#aab0c0", opacity: labelIn }}>{footnote}</div>
      )}
    </AbsoluteFill>
  );
};
