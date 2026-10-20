import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily } from "../fonts";
import { formatMoney, mixColor, style } from "../style";

export type PhoneNotificationsProps = {
  date?: string;
  time: string;
  app_name: string;
  items?: number[];
  // Text notifications instead of charges (same escalation from blue to red).
  messages?: { app: string; text: string }[];
  currency: "$" | "€";
  stagger: number;
  // Seconds before the first notification lands (lets the shot settle).
  delay?: number;
};

export const PHONE_WIDTH = 720;
export const PHONE_HEIGHT = 1440;

const Card: React.FC<{
  index: number;
  total: number;
  amount?: number;
  message?: { app: string; text: string };
  props: PhoneNotificationsProps;
  appearFrame: number;
}> = ({ index, total, amount, message, props, appearFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const local = frame - appearFrame;
  if (local < 0) return null;

  const t = total > 1 ? index / (total - 1) : 1;
  const accent = mixColor(style.info, style.danger, t);
  const enter = spring({ frame: local, fps, config: { damping: 14, stiffness: 180 } });
  const shake = t > 0.7 ? Math.sin(local * 2.2) * interpolate(local, [0, 10], [10, 0], { extrapolateRight: "clamp" }) : 0;

  return (
    <div
      style={{
        transform: `translateY(${(1 - enter) * -80}px) translateX(${shake}px) scale(${0.92 + 0.08 * enter})`,
        opacity: enter,
        background: "rgba(30, 32, 40, 0.88)",
        borderRadius: 34,
        padding: "20px 26px",
        marginBottom: 14,
        display: "flex",
        gap: 22,
        alignItems: "center",
        border: `3px solid ${accent}`,
        boxShadow: `0 0 ${20 + 30 * t}px ${accent}55`,
      }}
    >
      <div
        style={{
          width: 76,
          height: 76,
          borderRadius: 20,
          background: accent,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 48,
          fontWeight: 900,
          color: "white",
          flexShrink: 0,
        }}
      >
        {(message?.app ?? props.app_name).slice(0, 1).toUpperCase()}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 26, color: "#b9bcc6" }}>
          <span style={{ fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>{message?.app ?? props.app_name}</span>
          <span>ahora</span>
        </div>
        {message ? (
          <div style={{ fontSize: 36, fontWeight: 700, color: "white", marginTop: 6, lineHeight: 1.25 }}>{message.text}</div>
        ) : (
          <>
            <div style={{ fontSize: 34, fontWeight: 700, color: "white", marginTop: 6 }}>Cargo en tu tarjeta</div>
            <div style={{ fontSize: 46, fontWeight: 900, color: accent, marginTop: 2 }}>
              {formatMoney(amount ?? 0, props.currency)}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export const PhoneNotifications: React.FC<PhoneNotificationsProps> = (props) => {
  const { fps } = useVideoConfig();
  const delay = props.delay ?? 0.3;
  const items = props.items ?? [];
  const messages = props.messages ?? [];
  const count = messages.length || items.length;
  const appear = Array.from({ length: count }, (_, i) => i).map((_, i) => Math.round((delay + i * props.stagger) * fps));

  return (
    <AbsoluteFill
      style={{
        fontFamily,
        background: `radial-gradient(circle at 30% 20%, #1d2a4d 0%, ${style.background_blue} 45%, #000 100%)`,
        padding: "0 36px",
      }}
    >
      <div style={{ textAlign: "center", color: "white", marginTop: 90 }}>
        <div style={{ fontSize: 34, fontWeight: 500, opacity: 0.85, minHeight: 41 }}>{props.date ?? ""}</div>
        <div style={{ fontSize: 190, fontWeight: 300, lineHeight: 1, letterSpacing: -6 }}>{props.time}</div>
      </div>
      {/* Newest on top, like a real lock screen. */}
      <div style={{ marginTop: 50, display: "flex", flexDirection: "column-reverse" }}>
        {appear.map((frame, i) => (
          <Card key={i} index={i} total={count} amount={items[i]} message={messages[i]} props={props} appearFrame={frame} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
