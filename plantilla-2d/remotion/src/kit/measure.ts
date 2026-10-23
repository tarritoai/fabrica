// Text width in pixels, measured by the browser with the real (bundled) font: captions, tags and bubbles fit their
// paper to the words instead of guessing. Cached: the same text is measured once per render.
const cache = new Map<string, number>();
let ctx: CanvasRenderingContext2D | null = null;

export const measure = (text: string, size: number, family: string, weight = 900, stretch = "100%"): number => {
  const key = `${family}|${weight}|${stretch}|${size}|${text}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  if (!ctx) ctx = document.createElement("canvas").getContext("2d");
  let w = text.length * size * 0.45;
  if (ctx) {
    ctx.font = `${weight} ${stretch === "100%" ? "" : `${stretchKeyword(stretch)} `}${size}px "${family}"`;
    w = ctx.measureText(text).width;
  }
  cache.set(key, w);
  return w;
};

const stretchKeyword = (s: string) => {
  const v = parseFloat(s);
  if (v <= 75) return "condensed";
  if (v <= 90) return "semi-condensed";
  if (v >= 120) return "expanded";
  if (v >= 110) return "semi-expanded";
  return "normal";
};

/** Greedy line wrap with the real font. */
export const wrap = (words: string[], maxWidth: number, size: number, family: string, weight = 700): string[] => {
  const lines: string[] = [];
  let cur = "";
  for (const w of words) {
    const next = cur ? `${cur} ${w}` : w;
    if (cur && measure(next, size, family, weight) > maxWidth) {
      lines.push(cur);
      cur = w;
    } else cur = next;
  }
  if (cur) lines.push(cur);
  return lines;
};
