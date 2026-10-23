// The lettering layer of the house style: captions on torn-off paper strips (word by word, with the voice), speech
// bubbles that type themselves, the series tag, the title card, the rolling counter, rubber stamps, labels and the
// closing question. Everything sits in the phone-safe area (top 150 px and bottom 420 px are Instagram's).
import React from "react";
import { Img, interpolate, spring } from "remotion";
import { DISPLAY, STENCIL, TEXT } from "./fonts";
import { measure, wrap } from "./measure";
import { FPS, LINE, usePalette } from "./style";
import type { TBubble, TCounter, Word } from "./types";
import paperTexture from "./papel.png";

export const pop = (frame: number, at: number, damping = 12, stiffness = 230) =>
  spring({ frame: frame - at, fps: FPS, config: { damping, stiffness, mass: 0.6 } });

export const norm = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-zñ0-9]/g, "");

/** The paper grain over the whole frame (a 512 px tile, multiplied very softly). */
export const PaperTexture: React.FC<{ opacity?: number }> = ({ opacity = 0.32 }) => (
  <div style={{ position: "absolute", inset: 0, backgroundImage: `url(${paperTexture})`, backgroundSize: "512px 512px",
    mixBlendMode: "overlay", opacity, pointerEvents: "none" }}>
    <Img src={paperTexture} style={{ display: "none" }} />
  </div>
);

// ---------------------------------------------------------------------------------------------- captions

/** Group words into strips of 1–3 (a strip ends at punctuation). */
export const chunks = (words: Word[]): Word[][] => {
  const out: Word[][] = [];
  let cur: Word[] = [];
  for (const w of words) {
    cur.push(w);
    if (cur.length >= 3 || /[.,:;?!…]$/.test(w.text)) {
      out.push(cur);
      cur = [];
    }
  }
  if (cur.length) out.push(cur);
  return out;
};

/** Captions: the words of one beat, on a paper strip that grows as each word is said. Highlighted words in the accent. */
export const Captions: React.FC<{ frame: number; words: Word[]; highlight: string[]; y: number; size: number; cutAt?: number; index: number }> = ({
  frame, words, highlight, y, size, cutAt, index,
}) => {
  const p = usePalette();
  const t = frame / FPS;
  const strips = chunks(words);
  const i = strips.findIndex((s, k) =>
    t >= s[0].start - 0.04 &&
    (k + 1 >= strips.length ? t <= Math.min(s[s.length - 1].end + 0.4, (cutAt ?? 1e9) - 0.1) : t < strips[k + 1][0].start - 0.04));
  if (i < 0) return null;
  const strip = strips[i];
  const hl = new Set(highlight.map(norm));
  const items = strip.map((w) => ({ w, txt: w.text.toUpperCase(), on: t >= w.start - 0.04 }));
  const space = size * 0.22;
  const full = items.reduce((a, it) => a + measure(it.txt, size, DISPLAY, 900), 0) + space * (items.length - 1);
  const fit = Math.min(1, 860 / (full + 60));
  const shown = items.filter((it) => it.on);
  const shownW = shown.reduce((a, it) => a + measure(it.txt, size, DISPLAY, 900), 0) + space * Math.max(0, shown.length - 1);
  const padX = 30;
  const h = size * 1.08;
  const grow = pop(frame, Math.round(strip[0].start * FPS) - 2, 14, 260);
  const rot = (index + i) % 2 ? 1.4 : -1.2;
  let x = -full / 2;
  return (
    <g transform={`translate(540 ${y}) scale(${fit}) rotate(${rot})`}>
      <g filter="url(#sombra)">
        <path d={tornStrip(-full / 2 - padX, -h / 2, (shownW + padX * 2) * Math.min(1, grow) + 0.01, h, index * 7 + i)} fill={p.papelLuz} />
      </g>
      {items.map((it, k) => {
        const wpx = measure(it.txt, size, DISPLAY, 900);
        const x0 = x;
        x += wpx + space;
        if (!it.on) return null;
        const s = pop(frame, Math.round(it.w.start * FPS) - 1, 11, 300);
        const accent = hl.has(norm(it.w.text));
        return (
          <text key={k} x={x0 + wpx / 2} y={size * 0.35} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={size}
            fill={accent ? p.acento : p.tinta} transform={`translate(${x0 + wpx / 2} 0) scale(${0.82 + 0.18 * s}) translate(${-(x0 + wpx / 2)} 0)`}>
            {it.txt}
          </text>
        );
      })}
    </g>
  );
};

/** A strip of paper with slightly irregular (torn) short edges. */
const tornStrip = (x: number, y: number, w: number, h: number, seed: number): string => {
  const j = (k: number) => ((Math.sin(seed * 12.9898 + k * 78.233) * 43758.5453) % 1 + 1) % 1;
  const left = Array.from({ length: 6 }, (_, k) => `L${x + (j(k) - 0.5) * 9} ${y + h - (h * (k + 1)) / 6}`).join(" ");
  const right = Array.from({ length: 6 }, (_, k) => `L${x + w + (j(k + 9) - 0.5) * 9} ${y + (h * (k + 1)) / 6}`).join(" ");
  return `M${x} ${y} L${x + w} ${y} ${right} L${x} ${y + h} ${left} Z`;
};

// ---------------------------------------------------------------------------------------------- speech bubble

/** anchor: where the speaker's head is (the bubble sits above it and its tail points there). */
export const Bubble: React.FC<{ frame: number; words: Word[]; bubble: TBubble; until: number; anchor: [number, number] | null }> = ({ frame, words, bubble, until, anchor }) => {
  const p = usePalette();
  if (!words.length) return null;
  const t = frame / FPS;
  const a = words[0].start - 0.12;
  if (t < a || t > until) return null;
  const s = pop(frame, Math.round(a * FPS), 11);
  const shout = bubble.shout;
  const size = shout ? 92 : 54;
  const family = shout ? DISPLAY : TEXT;
  const weight = shout ? 900 : 750;
  const all = words.map((w) => (shout ? w.text.toUpperCase() : w.text));
  const inner = bubble.width - 64;
  const lines = wrapMeasured(all, inner, size, family, weight);
  const visible = words.filter((w) => t >= w.start - 0.03).length;
  const lh = size * (shout ? 1.0 : 1.18);
  const h = lines.length * lh + (shout ? 46 : 50);
  const w = bubble.width;
  const fill = shout ? p.acento : p.papelLuz;
  const head = anchor ?? [540, 900];
  const cx = bubble.x ?? Math.max(w / 2 + 30, Math.min(1050 - w / 2, head[0]));
  const cy = bubble.y ?? Math.max(340 + h / 2, Math.min(1300 - h / 2, head[1] - 120 - h / 2));
  const tx = Math.max(-w / 2 + 40, Math.min(w / 2 - 40, head[0] - cx));
  const ty = Math.max(h / 2 + 30, head[1] - 40 - cy);
  // tail: from the bottom edge towards the head
  const bx = Math.max(-w / 2 + 50, Math.min(w / 2 - 50, tx * 0.45));
  let shownSoFar = 0;
  return (
    <g transform={`translate(${cx} ${cy}) scale(${s})`}>
      <g filter="url(#sombra)">
        <path d={`M${bx - 30} ${h / 2 - 4} L${tx} ${ty} L${bx + 26} ${h / 2 - 4} Z`} fill={fill} stroke={p.tinta} strokeWidth={LINE} strokeLinejoin="round" />
        <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={shout ? 3 : 10} fill={fill} stroke={p.tinta} strokeWidth={shout ? LINE + 2 : LINE} />
        <rect x={bx - 27} y={h / 2 - 12} width={50} height={14} fill={fill} />
      </g>
      {lines.map((ln, i) => {
        const ws = ln.split(" ");
        const from = shownSoFar;
        shownSoFar += ws.length;
        const vis = ws.slice(0, Math.max(0, Math.min(ws.length, visible - from))).join(" ");
        const full = measure(ln, size, family, weight);
        return (
          <text key={i} x={-full / 2} y={-h / 2 + (shout ? 28 : 30) + size * 0.82 + i * lh} fontFamily={family} fontWeight={weight}
            fontSize={size} fill={p.tinta}>{vis}</text>
        );
      })}
    </g>
  );
};

const wrapMeasured = (words: string[], max: number, size: number, family: string, weight: number) => wrap(words, max, size, family, weight);

// ---------------------------------------------------------------------------------------------- tags, title, question

/** A kraft luggage tag: punched hole + text. */
export const Tag: React.FC<{ x: number; y: number; text: string; size?: number; fill?: string; color?: string; rot?: number; hole?: boolean; family?: string }> = ({
  x, y, text, size = 46, fill, color, rot = -2, hole = true, family = DISPLAY,
}) => {
  const p = usePalette();
  const tw = measure(text, size, family, 900);
  const padL = hole ? 50 : 24;
  const w = tw + padL + 26;
  const h = size + 24;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot})`}>
      <g filter="url(#sombra)">
        <path d={`M0 ${h * 0.28} L${h * 0.28} 0 L${w} 0 L${w} ${h} L${h * 0.28} ${h} L0 ${h * 0.72} Z`} fill={fill ?? p.kraft} stroke={p.tinta} strokeWidth={LINE - 2} strokeLinejoin="round" />
      </g>
      {hole && <circle cx={22} cy={h / 2} r={8} fill={p.papelLuz} stroke={p.tinta} strokeWidth={3} />}
      <text x={padL} y={h / 2 + size * 0.35} fontFamily={family} fontWeight={900} fontSize={size} fill={color ?? p.tinta}>{text}</text>
    </g>
  );
};

/** Series + work tags in the top-left corner (from `from` on). */
export const Tags: React.FC<{ frame: number; series: string | null; work: string | null; from: number }> = ({ frame, series, work, from }) => {
  const p = usePalette();
  if (frame < from || (!series && !work)) return null;
  const s = pop(frame, from, 13);
  const sw = series ? measure(series, 52, DISPLAY, 900) + 76 : 0;
  return (
    <g transform={`translate(${-360 * (1 - s)} 0)`}>
      {series && <Tag x={36} y={160} text={series} size={52} />}
      {work && <Tag x={48 + sw} y={170} text={work} size={38} fill={p.papelLuz} hole={false} rot={1.5} />}
    </g>
  );
};

/** The title card of the first seconds: a paper card with the question, the series tag pinned on it. */
export const TitleCard: React.FC<{ frame: number; lines: string[]; highlight: string[]; series: string | null; from: number; to: number }> = ({
  frame, lines, highlight, series, from, to,
}) => {
  const p = usePalette();
  if (frame < from || frame > to + 8) return null;
  const s = from <= 2 ? 1 : pop(frame, from, 10);
  const out = interpolate(frame, [to, to + 8], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const size = 118;
  const widths = lines.map((l) => measure(l.toUpperCase(), size, DISPLAY, 900));
  const w = Math.min(980, Math.max(...widths) + 110);
  const fit = Math.min(1, (w - 110) / Math.max(...widths));
  const lh = size * 0.98;
  const h = lines.length * lh * fit + 90;
  const hl = new Set(highlight.map(norm));
  return (
    <g transform={`translate(540 ${330 + h / 2}) scale(${s * (0.7 + 0.3 * out)}) rotate(-2.5)`} opacity={out}>
      <g filter="url(#sombra)">
        <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={3} fill={p.papelLuz} stroke={p.tinta} strokeWidth={LINE} />
      </g>
      <rect x={-w / 2 + 16} y={-h / 2 + 16} width={w - 32} height={h - 32} fill="none" stroke={p.tinta} strokeWidth={2} opacity={0.35} />
      {lines.map((l, i) => {
        const ws = l.toUpperCase().split(" ");
        const total = measure(l.toUpperCase(), size, DISPLAY, 900);
        let x = -total / 2;
        return (
          <g key={i} transform={`scale(${fit})`}>
            {ws.map((wd, k) => {
              const ww = measure(wd, size, DISPLAY, 900);
              const sp = measure(" ", size, DISPLAY, 900);
              const el = (
                <text key={k} x={x} y={-h / 2 / fit + 45 / fit + size * 0.82 + i * lh} fontFamily={DISPLAY} fontWeight={900} fontSize={size}
                  fill={hl.has(norm(wd)) ? p.acento : p.tinta}>{wd}</text>
              );
              x += ww + sp;
              return el;
            })}
          </g>
        );
      })}
      {series && <Tag x={-w / 2 + 10} y={-h / 2 - 62} text={series} size={50} rot={-3} />}
    </g>
  );
};

export const Question: React.FC<{ frame: number; at: number; text: string }> = ({ frame, at, text }) => {
  const p = usePalette();
  if (frame < at) return null;
  const s = pop(frame, at, 10);
  const size = 54;
  const tw = measure(text, size, DISPLAY, 900);
  const fit = Math.min(1, 900 / (tw + 60));
  return (
    <g transform={`translate(540 395) scale(${s * fit})`}>
      <Tag x={-(tw + 50 + 26) / 2} y={0} text={text} size={size} fill={p.acento} rot={-1.5} />
    </g>
  );
};

/** A free label in the world (a clock, «6:00», a name): small paper tag. */
export const Label: React.FC<{ frame: number; at: number; until: number; x: number; y: number; text: string; rot?: number; size?: number }> = ({
  frame, at, until, x, y, text, rot = 3, size = 40,
}) => {
  if (frame < at || frame > until) return null;
  const s = pop(frame, at, 11);
  const p = usePalette();
  const tw = measure(text, size, DISPLAY, 900);
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <Tag x={-(tw + 50) / 2} y={-(size + 24) / 2} text={text} size={size} fill={p.papelLuz} hole={false} rot={rot} />
    </g>
  );
};

// ---------------------------------------------------------------------------------------------- stamp

export const Stamp: React.FC<{ frame: number; at: number; text: string; x: number; y: number; rot?: number; size?: number; color?: string; until?: number }> = ({
  frame, at, text, x, y, rot = -8, size = 96, color, until,
}) => {
  const p = usePalette();
  if (frame < at || (until !== undefined && frame > until)) return null;
  const k = interpolate(frame, [at, at + 4], [0, 1], { extrapolateRight: "clamp" });
  const s = 1.9 - 0.9 * k;
  const family = size >= 110 ? STENCIL : DISPLAY;
  const tw = measure(text, size, family, 900);
  const w = tw + 76;
  const h = size + 44;
  const ink = color ?? p.sello;
  const jolt = frame - at < 8 ? [4, -3, 2, -1, 1, 0, 0, 0][frame - at] : 0;
  return (
    <g transform={`translate(${x + jolt} ${y}) rotate(${rot}) scale(${s})`} opacity={0.3 + 0.7 * k}>
      <g filter="url(#gastado)">
        <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={4} fill={p.papelLuz} fillOpacity={0.55} stroke={ink} strokeWidth={9} />
        <rect x={-w / 2 + 12} y={-h / 2 + 12} width={w - 24} height={h - 24} rx={2} fill="none" stroke={ink} strokeWidth={3.5} />
        <text x={0} y={size * 0.35} textAnchor="middle" fontFamily={family} fontWeight={900} fontSize={size} fill={ink} letterSpacing={2}>{text}</text>
      </g>
    </g>
  );
};

// ---------------------------------------------------------------------------------------------- counter

/** The recurring counter (top right): a kraft tab with what is counted and a night plate with rolling digits
 *  («rodillo»), or a row of squares that fill («barra»). `broken`: crossed out (the twist). */
export const Counter: React.FC<{ frame: number; counter: TCounter; values: { frame: number; value: number }[]; broken: number | null }> = ({
  frame, counter, values, broken,
}) => {
  const p = usePalette();
  if (frame < counter.from) return null;
  const s = pop(frame, counter.from, 13);
  const done = values.filter((v) => frame >= v.frame);
  const last = done.length ? done[done.length - 1] : null;
  const before = done.length > 1 ? done[done.length - 2].value : counter.start;
  const value = last ? last.value : counter.start;
  const since = last ? frame - last.frame : 999;
  const bump = 1 + 0.16 * Math.max(0, 1 - since / 8);
  const shake = broken !== null && frame >= broken && frame < broken + 14 ? Math.sin(frame * 3) * 9 : 0;
  const labelSize = 31;
  const W = Math.max(measure(counter.label, labelSize, DISPLAY, 800) + 36, 250);
  const plateH = 124;
  return (
    <g transform={`translate(${1040 + shake} 150) scale(${s}) translate(${-W} 0)`}>
      <g filter="url(#sombra)">
        <rect x={0} y={0} width={W} height={52} rx={2} fill={p.kraft} stroke={p.tinta} strokeWidth={LINE - 2} />
        <rect x={0} y={50} width={W} height={plateH} rx={2} fill={counter.kind === "rodillo" ? p.cifra : p.papelLuz} stroke={p.tinta} strokeWidth={LINE - 2} />
      </g>
      <text x={W / 2} y={37} textAnchor="middle" fontFamily={DISPLAY} fontWeight={800} fontSize={labelSize} fill={p.tinta} letterSpacing={1}>{counter.label}</text>
      <g transform={`translate(${W / 2} ${50 + plateH / 2}) scale(${bump})`}>
        {counter.kind === "rodillo" ? (
          <Odometer from={before} to={value} since={since} plateH={plateH} suffix={counter.suffix} />
        ) : (
          <Bar value={value} max={counter.max} since={since} width={W - 30} />
        )}
      </g>
      {broken !== null && frame >= broken && (
        <g transform={`translate(${W / 2} ${50 + plateH / 2})`}>
          <path d={`M${-W * 0.42} ${-plateH * 0.36} L${-W * 0.42 + W * 0.84 * Math.min(1, (frame - broken) / 5)} ${-plateH * 0.36 + plateH * 0.72 * Math.min(1, (frame - broken) / 5)}`}
            stroke={p.sello} strokeWidth={15} strokeLinecap="round" />
          <path d={`M${W * 0.42} ${-plateH * 0.36} L${W * 0.42 - W * 0.84 * Math.min(1, Math.max(0, (frame - broken - 3) / 5))} ${-plateH * 0.36 + plateH * 0.72 * Math.min(1, Math.max(0, (frame - broken - 3) / 5))}`}
            stroke={p.sello} strokeWidth={15} strokeLinecap="round" />
        </g>
      )}
    </g>
  );
};

const Odometer: React.FC<{ from: number; to: number; since: number; plateH: number; suffix: string }> = ({ from, to, since, plateH, suffix }) => {
  const p = usePalette();
  const size = 100;
  const k = Math.min(1, since / 10);
  const e = 1 - Math.pow(1 - k, 3);
  const a = String(from);
  const b = String(to);
  const shownOld = k < 1;
  return (
    <g>
      <clipPath id="odo"><rect x={-200} y={-plateH / 2 + 6} width={400} height={plateH - 12} /></clipPath>
      <g clipPath="url(#odo)">
        {shownOld && (
          <text x={0} y={size * 0.35 - e * plateH} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={size} fill={p.cifraTexto}>{a}{suffix}</text>
        )}
        <text x={0} y={size * 0.35 + (1 - e) * plateH} textAnchor="middle" fontFamily={DISPLAY} fontWeight={900} fontSize={size} fill={p.cifraTexto}>{b}{suffix}</text>
      </g>
    </g>
  );
};

const Bar: React.FC<{ value: number; max: number; since: number; width: number }> = ({ value, max, since, width }) => {
  const p = usePalette();
  const n = Math.max(1, Math.min(12, max));
  const gap = 8;
  const cw = (width - gap * (n - 1)) / n;
  return (
    <g transform={`translate(${-width / 2} 0)`}>
      {Array.from({ length: n }, (_, i) => {
        const on = i < value;
        const fresh = i === value - 1 && since < 8;
        return (
          <rect key={i} x={i * (cw + gap)} y={-34 - (fresh ? 6 : 0)} width={cw} height={68} rx={2}
            fill={on ? p.acento : p.papel} stroke={p.tinta} strokeWidth={3} />
        );
      })}
    </g>
  );
};
