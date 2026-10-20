import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily } from "../fonts";
import { style } from "../style";
import type { Viseme } from "./types";

// Vertical centre of the subtitle per camera preset, as a fraction of height.
// Keeps clear of faces and of the bottom 15 % where the app UI sits.
const Y_BY_CAMERA: Record<string, number> = {
  two_shot: 0.7,
  medium_novato_low: 0.72,
  closeup_novato: 0.72,
  closeup_ai: 0.72,
  phone_closeup: 0.8,
  // Over a phone or laptop screen the subtitle goes below the content: at 0.7 it sat among the chat bubbles and
  // read as one more message.
  phone_screen: 0.85,
  screen_closeup: 0.85,
};

// Comedy keeps the loud meme look; quieter episodes get film-like subtitles that don't fight the image.
const LOOKS = {
  loud: { fontSize: 68, fontWeight: 900, stroke: 10, shadow: "0 6px 18px rgba(0,0,0,0.7)", tint: 0 },
  soft: { fontSize: 62, fontWeight: 700, stroke: 0, shadow: "0 2px 3px rgba(0,0,0,0.95), 0 0 14px rgba(0,0,0,0.75), 0 0 34px rgba(0,0,0,0.45)", tint: 0.45 },
};
// Film-like subtitles everywhere (decided 2026-10-16): the thick meme outline read as template-made.
export const subtitleLook = (_tone?: string) => LOOKS.soft;

// Speaker colour mixed towards a warm white (soft look): still tells who speaks, without shouting.
const towardsWhite = (hex: string, t: number) => {
  if (!hex.startsWith("#") || t === 0) return hex;
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const w = [255, 246, 234];
  return `rgb(${c.map((v, i) => Math.round(v + (w[i] - v) * t)).join(",")})`;
};

// When each word of the line appears. Whisper's word times are unreliable (often before the audio even
// starts), so timing comes from the mouth: the viseme track gives the real stretches of speech and their
// pauses. Each phrase (split at . , … ? !) goes to its stretch when the counts match; inside, words are
// spread by length. Everything lands before the shot cuts.
export const tokensOf = (text: string) => text.split(/\s+/).filter(Boolean);

const speechRuns = (visemes: Viseme[], minGap = 0.15) => {
  const runs: { start: number; end: number }[] = [];
  for (const v of visemes) {
    if (v.viseme === "mouth_rest") continue;
    const last = runs[runs.length - 1];
    if (last && v.start - last.end < minGap) last.end = v.end;
    else runs.push({ start: v.start, end: v.end });
  }
  return runs;
};

// Chunks of one short line: first cut at punctuation, then each phrase is split into equal parts of at most
// 4 words / ~24 characters ("me he olvidado | la contraseña de Instagram"), so nothing is left hanging.
const MAX_WORDS = 4;
const MAX_CHARS = 24;
export const chunksOf = (tokens: string[]): number[][] => {
  const phrases: number[][] = [[]];
  tokens.forEach((tok, i) => {
    phrases[phrases.length - 1].push(i);
    if (/[.,…?!:;]["»”']?$/.test(tok) && i < tokens.length - 1) phrases.push([]);
  });
  const out: number[][] = [];
  for (const ph of phrases) {
    const chars = ph.reduce((a, i) => a + tokens[i].length + 1, 0);
    const k = Math.max(Math.ceil(ph.length / MAX_WORDS), Math.ceil(chars / MAX_CHARS), 1);
    const size = Math.ceil(ph.length / k);
    for (let j = 0; j < ph.length; j += size) out.push(ph.slice(j, j + size));
  }
  return out.filter((c) => c.length);
};

export const subtitleTiming = (line: string, visemes: Viseme[] | undefined, maxSpan: number) => {
  const tokens = tokensOf(line);
  const runs = visemes ? speechRuns(visemes) : [];
  const t0 = runs.length ? runs[0].start : 0; // the subtitle appears with the first sound
  const phrases: number[][] = [[]];
  tokens.forEach((tok, i) => {
    phrases[phrases.length - 1].push(i);
    if (/[.,…?!:;]["»”']?$/.test(tok) && i < tokens.length - 1) phrases.push([]);
  });
  const spans =
    runs.length && phrases.length === runs.length
      ? runs.map((r) => [r.start - t0, r.end - t0])
      : [[0, runs.length ? runs[runs.length - 1].end - t0 : tokens.length * 0.28]];
  const groups = spans.length === phrases.length ? phrases : [tokens.map((_, i) => i)];
  const times = new Array(tokens.length).fill(0);
  groups.forEach((idx, g) => {
    const [a, b] = spans[g];
    const chars = idx.map((i) => tokens[i].length + 1);
    const sum = chars.reduce((x, y) => x + y, 0);
    let acc = 0;
    idx.forEach((i, j) => {
      times[i] = a + (acc / sum) * (b - a) * 0.9; // a word shows as it starts, not as it ends
      acc += chars[j];
    });
  });
  // Never let the end of a line miss the shot: squeeze it in if it would land too late.
  const last = times[times.length - 1] || 0;
  const k = last > maxSpan ? maxSpan / last : 1;
  return { start: t0, times: times.map((x) => x * k) };
};

// The line builds up word by word as it is said: a full line read ahead of the voice spoils the punch.
// Unsaid words keep their place (invisible), so nothing reflows. Comedy words pop in; quiet episodes fade in.

export const Subtitle: React.FC<{ text: string; color: string; camera: string; tone?: string; times?: number[] }> = ({
  text,
  color,
  camera,
  tone,
  times,
}) => {
  const look = subtitleLook(tone);
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const popFrames = Math.max(1, Math.round(0.08 * fps));
  const scale = interpolate(frame, [0, popFrames], [0.9, 1], { extrapolateRight: "clamp" });
  const opacity = interpolate(frame, [0, popFrames], [0, 1], { extrapolateRight: "clamp" });
  const y = (Y_BY_CAMERA[camera] ?? 0.7) * height;

  return (
    <div
      style={{
        position: "absolute",
        top: y,
        left: 70,
        // Extra right margin: platform buttons live on the right edge.
        right: 130,
        transform: `translateY(-50%) scale(${scale})`,
        opacity,
        textAlign: "center",
        fontFamily,
        fontWeight: look.fontWeight,
        fontSize: look.fontSize,
        lineHeight: 1.18,
        color: towardsWhite(color, look.tint),
        WebkitTextStroke: look.stroke ? `${look.stroke}px ${style.subtitle_stroke}` : undefined,
        paintOrder: "stroke fill",
        textShadow: look.shadow,
      }}
    >
      {(() => {
        const tokens = tokensOf(text);
        const at = times && times.length === tokens.length ? times : tokens.map(() => 0);
        const t = frame / fps;
        const loud = tone === "comedia"; // comedy words still pop in; quieter episodes fade them in
        // One short line at a time: the line is cut into chunks (at punctuation, or every 3-4 words) and only the
        // chunk being said is on screen, filling in word by word; the next one replaces it.
        const chunks = chunksOf(tokens);
        const live = chunks.reduce((cur, c, n) => (t - at[c[0]] + 0.04 >= 0 ? n : cur), 0);
        const shownIdx = new Set(chunks[live]);
        return tokens.map((w, i) => {
          if (!shownIdx.has(i)) return null;
          // Each word shows a hair before it is heard (reading lags the eye a little).
          const since = t - at[i] + 0.04;
          const pop = loud ? interpolate(since, [0, 0.07, 0.14], [0.75, 1.08, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;
          const shown = interpolate(since, [0, loud ? 0.05 : 0.18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <React.Fragment key={i}>
              {i > chunks[live][0] && " "}
              <span
                style={{
                  display: "inline-block",
                  // Room for the pop: the scaled word must not touch its neighbours.
                  padding: "0 0.06em",
                  transform: `scale(${pop})`,
                  opacity: shown,
                }}
              >
                {w}
              </span>
            </React.Fragment>
          );
        });
      })()}
    </div>
  );
};
