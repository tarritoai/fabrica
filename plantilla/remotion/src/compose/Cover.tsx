import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { fontFamily } from "../fonts";

export type CoverProps = {
  image: string; // a full-quality still of the episode (public dir path)
  title: string; // 1-3 words
  mark?: string | null; // series part, e.g. "1/3"
  handle?: string;
  position?: "bottom" | "center"; // where the title sits (bottom by default)
};

// Instagram shows reels on the profile grid cropped to 3:4 around the centre (1080x1440 of 1080x1920):
// everything that matters lives between y=240 and y=1680.
const SAFE_TOP = 240;
const SAFE_BOTTOM = 1680;
// The grid draws the play/views counter over the bottom of the thumbnail: keep the title clear of it.
const TITLE_BOTTOM = SAFE_BOTTOM - 250;

export const Cover: React.FC<CoverProps> = ({ image, title, mark, handle = "", position = "bottom" }) => (
  <AbsoluteFill style={{ background: "black" }}>
    <Img src={staticFile(image)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    {/* A soft dark band under the title so it reads on any frame, without boxing it. */}
    <AbsoluteFill
      style={{
        background:
          position === "center"
            ? "radial-gradient(ellipse 70% 18% at 50% 50%, rgba(8,6,16,0.55), rgba(8,6,16,0) 100%)"
            : `linear-gradient(180deg, rgba(0,0,0,0) ${TITLE_BOTTOM - 520}px, rgba(8,6,16,0.62) ${TITLE_BOTTOM - 200}px, rgba(8,6,16,0.55) ${SAFE_BOTTOM}px, rgba(0,0,0,0) 1920px)`,
      }}
    />
    <div
      style={{
        position: "absolute",
        left: 80,
        right: 80,
        ...(position === "center" ? { top: "50%", transform: "translateY(-50%)" } : { bottom: 1920 - TITLE_BOTTOM }),
        textAlign: "center",
        fontFamily,
        color: "#fbf3e4",
      }}
    >
      <div style={{ fontSize: 132, fontWeight: 900, lineHeight: 1.0, letterSpacing: -2, textShadow: "0 4px 24px rgba(0,0,0,0.55)" }}>{title}</div>
      {mark && <div style={{ marginTop: 22, fontSize: 52, fontWeight: 500, letterSpacing: 8, opacity: 0.85 }}>{mark}</div>}
    </div>
    <div
      style={{
        position: "absolute",
        top: SAFE_TOP + 40,
        width: "100%",
        textAlign: "center",
        fontFamily,
        fontWeight: 500,
        fontSize: 34,
        letterSpacing: 2,
        color: "rgba(251,243,228,0.8)",
        textShadow: "0 2px 10px rgba(0,0,0,0.5)",
      }}
    >
      {handle}
    </div>
  </AbsoluteFill>
);
