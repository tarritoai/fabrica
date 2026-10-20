import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily } from "../fonts";

// A generic streaming app's "who's watching?" profile picker on the novato's laptop (invented brand, no real UI).
// Big tiles: it has to read in screen_closeup. new_at: seconds into the clip when the profile flagged `is_new` pops in.
export type StreamProfile = { name: string; color: string; is_new?: boolean };
export type StreamProfilesProps = {
  app_name: string;
  title: string;
  profiles: StreamProfile[];
  new_at?: number | null; // null = the new profile is already there
};

export const StreamProfiles: React.FC<StreamProfilesProps> = ({ app_name, title, profiles, new_at = null }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{ fontFamily, background: "#101014", color: "#f1f1f4", padding: "48px 90px" }}>
      <div style={{ fontSize: 40, fontWeight: 900, letterSpacing: 2, color: "#e8505b" }}>{app_name}</div>
      <div style={{ textAlign: "center", fontSize: 60, fontWeight: 500, marginTop: 70 }}>{title}</div>
      <div style={{ display: "flex", justifyContent: "center", gap: 56, marginTop: 64 }}>
        {profiles.map((p, i) => {
          const k = p.is_new && new_at !== null
            ? interpolate(t, [new_at, new_at + 0.25], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
            : 1;
          return (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20, opacity: k,
              transform: `scale(${0.85 + 0.15 * k})` }}>
              <div style={{ position: "relative", width: 230, height: 230, borderRadius: 22, background: p.color,
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 120, fontWeight: 900,
                color: "rgba(255,255,255,0.92)", outline: p.is_new ? "6px solid #f1f1f4" : "none", outlineOffset: 6 }}>
                {p.name.charAt(0)}
                {p.is_new && (
                  <div style={{ position: "absolute", top: -22, right: -22, background: "#e8505b", borderRadius: 14,
                    padding: "6px 16px", fontSize: 30, fontWeight: 700, color: "#fff" }}>Nuevo</div>
                )}
              </div>
              <div style={{ fontSize: 50, fontWeight: 700, color: p.is_new ? "#ffffff" : "#a9a9b4" }}>{p.name}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
