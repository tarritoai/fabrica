// Small effects every reel reuses: the paper «puff» of a reveal, sparkles, speed lines, floating hearts, the halftone
// dots of a title background, and the shared <defs> (hard shadow, worn stamp ink).
import React from "react";
import { LINE, SHADOW, usePalette } from "./style";

/** Shared SVG definitions. `sombra` = the hard shadow under every cut-out piece. */
export const Defs: React.FC = () => {
  const p = usePalette();
  return (
    <defs>
      <filter id="sombra" x="-30%" y="-30%" width="160%" height="160%" colorInterpolationFilters="sRGB">
        <feFlood floodColor={p.sombra} floodOpacity={p.sombraOpacidad} result="c" />
        <feComposite in="c" in2="SourceAlpha" operator="in" result="s" />
        <feOffset in="s" dx={SHADOW[0]} dy={SHADOW[1]} result="o" />
        <feMerge>
          <feMergeNode in="o" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <filter id="sombra-texto" x="-10%" y="-30%" width="120%" height="160%" colorInterpolationFilters="sRGB">
        <feFlood floodColor={p.sombra} floodOpacity={0.55} result="c" />
        <feComposite in="c" in2="SourceAlpha" operator="in" result="s" />
        <feOffset in="s" dx={6} dy={7} result="o" />
        <feMerge>
          <feMergeNode in="o" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      {/* worn rubber-stamp ink: a fixed noise eats small bits of the stamp */}
      <filter id="gastado" x="0%" y="0%" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves={2} seed={11} result="n" />
        <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -9 0 0 0 7.0" result="a" />
        <feComposite in="SourceGraphic" in2="a" operator="in" />
      </filter>
    </defs>
  );
};

/** Paper puff for a fantasy → reality swap. p: 0..1 progress (nothing outside). */
export const Puff: React.FC<{ p: number; r?: number }> = ({ p, r = 260 }) => {
  const pal = usePalette();
  if (p <= 0 || p >= 1) return null;
  const s = 0.45 + p * 0.85;
  return (
    <g opacity={1 - p * p} transform={`scale(${s})`}>
      {Array.from({ length: 9 }, (_, i) => {
        const a = (i / 9) * Math.PI * 2 + 0.3;
        return (
          <circle key={i} cx={Math.cos(a) * r * 0.55} cy={Math.sin(a) * r * 0.42} r={r * (0.27 + (i % 3) * 0.04)}
            fill={pal.papelLuz} stroke={pal.tinta} strokeWidth={LINE} />
        );
      })}
      <circle r={r * 0.52} fill={pal.papelLuz} />
      {Array.from({ length: 7 }, (_, i) => {
        const a = (i / 7) * Math.PI * 2;
        const d = r * (0.9 + p * 0.9);
        return <rect key={`b${i}`} x={Math.cos(a) * d - 9} y={Math.sin(a) * d - 6} width={18} height={12} rx={1}
          transform={`rotate(${i * 47 + p * 200} ${Math.cos(a) * d} ${Math.sin(a) * d})`} fill={i % 2 ? pal.kraft : pal.acento} />;
      })}
    </g>
  );
};

/** Four-point sparkles inside a w×h area above the origin (they pulse). */
export const Sparkles: React.FC<{ frame: number; n?: number; w?: number; h?: number; color?: string }> = ({ frame, n = 7, w = 500, h = 600, color }) => {
  const p = usePalette();
  return (
    <g>
      {Array.from({ length: n }, (_, i) => {
        const x = ((i * 137) % w) - w / 2;
        const y = -((i * 211) % h);
        const s = 0.45 + 0.55 * Math.abs(Math.sin(frame / 7 + i * 1.7));
        return (
          <path key={i} transform={`translate(${x} ${y}) scale(${s}) rotate(${(frame * 2 + i * 40) % 90})`}
            d="M0 -24 L5 -5 L24 0 L5 5 L0 24 L-5 5 L-24 0 L-5 -5 Z" fill={color ?? p.papelLuz} stroke={p.tinta} strokeWidth={3} strokeLinejoin="round" />
        );
      })}
    </g>
  );
};

/** Horizontal speed lines behind something that runs to the right (dir = 1) or left (dir = -1). */
export const SpeedLines: React.FC<{ frame: number; dir?: number; n?: number; length?: number; spread?: number; opacity?: number }> = ({
  frame, dir = 1, n = 5, length = 220, spread = 300, opacity = 0.9,
}) => {
  const p = usePalette();
  return (
    <g opacity={opacity}>
      {Array.from({ length: n }, (_, i) => {
        const y = -spread / 2 + (i * spread) / Math.max(1, n - 1) + Math.sin(frame + i) * 6;
        const off = ((frame * 23 + i * 61) % 80) * dir;
        const x0 = -dir * (90 + i * 18) - off;
        return <line key={i} x1={x0} x2={x0 - dir * (length - i * 25)} y1={y} y2={y} stroke={p.papelLuz} strokeWidth={11} strokeLinecap="round" />;
      })}
    </g>
  );
};

export const Hearts: React.FC<{ frame: number; n?: number; color?: string }> = ({ frame, n = 3, color }) => {
  const p = usePalette();
  return (
    <g>
      {Array.from({ length: n }, (_, i) => {
        const k = (frame * 2 + i * 27) % 80;
        return (
          <path key={i} transform={`translate(${i * 46 - 46} ${-k * 3}) scale(${0.8 + i * 0.18})`} opacity={1 - k / 80}
            d="M0 10 C-20 -10 -30 -26 -14 -34 C-4 -38 0 -30 0 -26 C0 -30 4 -38 14 -34 C30 -26 20 -10 0 10 Z"
            fill={color ?? p.rojo} stroke={p.tinta} strokeWidth={4} />
        );
      })}
    </g>
  );
};

/** Halftone dots: big at the edges, small in the middle (a printed-comic background). */
export const Halftone: React.FC<{ w: number; h: number; cx: number; cy: number; color: string; step?: number; max?: number; drift?: number }> = ({
  w, h, cx, cy, color, step = 46, max = 17, drift = 0,
}) => {
  const dots: React.ReactNode[] = [];
  const diag = Math.hypot(Math.max(cx, w - cx), Math.max(cy, h - cy));
  for (let row = -1; row * step < h + step; row++) {
    for (let col = -1; col * step < w + step; col++) {
      const x = col * step + (row % 2 ? step / 2 : 0) + drift;
      const y = row * step;
      const d = Math.hypot(x - cx, y - cy) / diag;
      const r = max * Math.max(0, d * 1.25 - 0.18);
      if (r > 1.2) dots.push(<circle key={`${row}-${col}`} cx={x} cy={y} r={Math.min(max, r)} fill={color} />);
    }
  }
  return <g>{dots}</g>;
};
