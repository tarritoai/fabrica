// Drawing primitives of the house style: «tube» limbs, hands, eyes, mouths and brows, plus the body's pulse (blink,
// breathing) and smooth transitions of a changing value. Every piece draws with these, so any new character looks like
// part of the same family.
import React from "react";
import { interpolate } from "remotion";
import { LINE, usePalette } from "./style";

export type Pt = [number, number];

/** «Tube» limb: the same stroke twice (ink below, colour on top). Posed with 2 or 3 points. */
export const Limb: React.FC<{ p: Pt[]; color: string; width?: number; curve?: boolean }> = ({ p, color, width = 18, curve = true }) => {
  const ink = usePalette().tinta;
  let d = `M${p[0][0]} ${p[0][1]}`;
  if (p.length === 3 && curve) d += ` Q${p[1][0]} ${p[1][1]} ${p[2][0]} ${p[2][1]}`;
  else for (const [x, y] of p.slice(1)) d += ` L${x} ${y}`;
  return (
    <g strokeLinecap="round" strokeLinejoin="round" fill="none">
      <path d={d} stroke={ink} strokeWidth={width + LINE * 2} />
      <path d={d} stroke={color} strokeWidth={width} />
    </g>
  );
};

export const Hand: React.FC<{ x: number; y: number; color: string; r?: number }> = ({ x, y, color, r = 14 }) => (
  <circle cx={x} cy={y} r={r} fill={color} stroke={usePalette().tinta} strokeWidth={LINE - 1} />
);

/** Deterministic blink (1 = open). Each character gets its own phase so they never blink together. */
export const blink = (frame: number, phase = 0, every = 97) => {
  const k = (frame + phase) % every;
  return k < 2 ? 0.08 : k < 4 ? 0.45 : 1;
};

/** Breathing: a soft sway, in pixels. */
export const breathe = (frame: number, phase = 0, amp = 1) => Math.sin((frame + phase) / 15) * amp;

/** From `before` to `now` over `dur` frames since the change (`since` = frames since it changed), with a little spring. */
export const transition = (before: number, now: number, since: number, dur = 9, bounce = 0.12) => {
  if (since >= dur * 2) return now;
  const t = Math.max(0, since / dur);
  const e = t >= 1 ? 1 + Math.sin(Math.min(1, t - 1) * Math.PI) * bounce * Math.exp(-(t - 1) * 3) : 1 - Math.pow(1 - t, 3);
  return before + (now - before) * e;
};

/** 0 → 1 between frames a and b, eased. */
export const ease = (frame: number, a: number, b: number) =>
  interpolate(frame, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (t) => t * t * (3 - 2 * t) });

export type EyeStyle = "punto" | "blanco";

/** Eye: «punto» (ink oval with a glint) or «blanco» (white with a pupil that looks). mx, my: where it looks (-1..1). */
export const Eye: React.FC<{
  x: number; y: number; style?: EyeStyle; r?: number; mx?: number; my?: number; open?: number; scared?: boolean;
}> = ({ x, y, style = "punto", r = 13, mx = 0, my = 0, open = 1, scared = false }) => {
  const p = usePalette();
  const a = Math.max(0.08, open);
  if (a < 0.2) {
    return <path d={`M${x - r} ${y} Q${x} ${y + r * 0.45} ${x + r} ${y}`} stroke={p.tinta} strokeWidth={LINE - 1} fill="none" strokeLinecap="round" />;
  }
  if (style === "punto" && !scared) {
    return (
      <g transform={`translate(${x + mx * r * 0.35} ${y + my * r * 0.3}) scale(1 ${a})`}>
        <ellipse rx={r * 0.62} ry={r} fill={p.tinta} />
        <circle cx={r * 0.18} cy={-r * 0.42} r={r * 0.24} fill={p.papelLuz} />
      </g>
    );
  }
  const rx = scared ? r * 1.25 : r;
  const ry = scared ? r * 1.45 : r * 1.2;
  const pr = scared ? r * 0.32 : r * 0.5;
  return (
    <g transform={`translate(${x} ${y}) scale(1 ${a})`}>
      <ellipse rx={rx} ry={ry} fill={p.papelLuz} stroke={p.tinta} strokeWidth={LINE - 2} />
      <circle cx={mx * (rx - pr - 2)} cy={my * (ry - pr - 3)} r={pr} fill={p.tinta} />
      <circle cx={mx * (rx - pr - 2) + pr * 0.35} cy={my * (ry - pr - 3) - pr * 0.4} r={pr * 0.3} fill={p.papelLuz} />
    </g>
  );
};

export type MouthShape = "sonrisa" | "risa" | "triste" | "recta" | "o" | "grito" | "picara" | "dientes";

/** Mouth. open: 0..1 (the voice moves it). With the mouth closed, the shape says the emotion. */
export const Mouth: React.FC<{ x: number; y: number; open?: number; width?: number; shape?: MouthShape }> = ({
  x, y, open = 0, width = 18, shape = "recta",
}) => {
  const p = usePalette();
  const tongue = "#E07A7A";
  const throat = "#5A2028";
  if (open > 0.15 || shape === "grito" || shape === "o" || shape === "risa") {
    const base = shape === "grito" ? 1.25 : shape === "o" ? 0.55 : shape === "risa" ? 0.85 : 0.5 + open * 0.5;
    const h = (shape === "grito" ? 24 : shape === "risa" ? 13 : shape === "o" ? 10 : 6) + open * 13;
    const w = width * base;
    if (shape === "risa" || shape === "sonrisa") {
      const d = `M${-w} ${-h * 0.3} Q0 ${-h * 0.1} ${w} ${-h * 0.3} Q${w * 0.75} ${h} 0 ${h} Q${-w * 0.75} ${h} ${-w} ${-h * 0.3} Z`;
      return (
        <g transform={`translate(${x} ${y})`}>
          <path d={d} fill={throat} stroke={p.tinta} strokeWidth={LINE - 2} strokeLinejoin="round" />
          <path d={`M${-w * 0.5} ${h * 0.6} Q0 ${h * 0.15} ${w * 0.5} ${h * 0.6} Q0 ${h * 0.95} ${-w * 0.5} ${h * 0.6} Z`} fill={tongue} />
        </g>
      );
    }
    return (
      <g transform={`translate(${x} ${y})`}>
        <ellipse rx={w} ry={h} fill={throat} stroke={p.tinta} strokeWidth={LINE - 2} />
        <ellipse cy={h * 0.45} rx={w * 0.55} ry={h * 0.38} fill={tongue} />
      </g>
    );
  }
  const a = width;
  if (shape === "dientes") {
    return (
      <g>
        <path d={`M${x - a} ${y - 4} Q${x} ${y + 13} ${x + a} ${y - 4} Z`} fill={p.papelLuz} stroke={p.tinta} strokeWidth={LINE - 2} strokeLinejoin="round" />
        <path d={`M${x - a * 0.35} ${y - 2} L${x - a * 0.35} ${y + 5} M${x + a * 0.35} ${y - 2} L${x + a * 0.35} ${y + 5}`} stroke={p.tinta} strokeWidth={2.5} />
      </g>
    );
  }
  const d =
    shape === "sonrisa" ? `M${x - a} ${y - 4} Q${x} ${y + 14} ${x + a} ${y - 4}` :
    shape === "triste" ? `M${x - a} ${y + 7} Q${x} ${y - 9} ${x + a} ${y + 7}` :
    shape === "picara" ? `M${x - a} ${y + 2} Q${x + a * 0.2} ${y + 10} ${x + a} ${y - 8}` :
    `M${x - a * 0.7} ${y} L${x + a * 0.7} ${y}`;
  return <path d={d} stroke={p.tinta} strokeWidth={LINE - 1} strokeLinecap="round" fill="none" />;
};

/** Brow: height (−1 down … 1 up) and tilt (−1 angry … 1 sad). side −1 = the character's right brow (screen left). */
export const Brow: React.FC<{ x: number; y: number; side: -1 | 1; up?: number; tilt?: number; length?: number; color?: string; width?: number }> = ({
  x, y, side, up = 0, tilt = 0, length = 26, color, width = 8,
}) => {
  const p = usePalette();
  const yy = y - up * 10;
  const inner = x - (length / 2) * side; // the end near the nose
  const outer = x + (length / 2) * side;
  return <path d={`M${inner} ${yy - tilt * 8} L${outer} ${yy + tilt * 8}`} stroke={color ?? p.tinta} strokeWidth={width} strokeLinecap="round" />;
};

export const Cheeks: React.FC<{ x: number; y: number; sep: number; r?: number; opacity?: number }> = ({ x, y, sep, r = 11, opacity = 0.55 }) => {
  const p = usePalette();
  return (
    <g opacity={opacity}>
      <ellipse cx={x - sep} cy={y} rx={r} ry={r * 0.7} fill={p.mejilla} />
      <ellipse cx={x + sep} cy={y} rx={r} ry={r * 0.7} fill={p.mejilla} />
    </g>
  );
};

/** Mouth opening while speaking: opens and closes ~7 times a second while a word of that voice sounds. */
export const talkMouth = (frame: number, talk: number) => (talk <= 0 ? 0 : [0.9, 0.55, 0.2, 0.7][Math.floor(frame / 2.2) % 4] * talk);
