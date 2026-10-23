// The compositions of the 2D factory. The CLI writes one entry per episode (src/generado/<slug>.ts) that calls
// makeRoot() with that episode's own pieces, so a broken drawing in one episode never breaks another.
import React from "react";
import { AbsoluteFill, Composition } from "remotion";
import * as base from "../piezas";
import * as characters from "../personajes";
import { Defs } from "./effects";
import { DISPLAY, TEXT } from "./fonts";
import { PaperTexture } from "./overlays";
import { makeReel, makeStills, type Pieces } from "./Reel";
import { FPS, HEIGHT, PaletteContext, WIDTH, palette } from "./style";
import type { Piece, Timeline } from "./types";
import "./fonts";

/** Every exported component whose name starts with a capital letter is a piece. */
export const collect = (...mods: Record<string, unknown>[]): Pieces => {
  const out: Pieces = {};
  for (const m of mods) {
    for (const [k, v] of Object.entries(m)) {
      if (/^[A-Z]/.test(k) && typeof v === "function") out[k] = v as Piece;
    }
  }
  return out;
};

const EMPTY: Timeline = {
  slug: "vacio", title: "", series: "¿Y SI…?", work: null, palette: "alfar", fps: FPS, width: WIDTH, height: HEIGHT, frames: 30,
  words: [], beats: [], shots: [{ index: 0, from: 0, to: 30, scene: "Campo", options: {}, camera: { zoom: 0, focus: [540, 1000], punch: false, pan: [0, 0] }, actors: [] }],
  events: [], counter: null, title_card: null, tags_from: 0, audio: { voices: [], music: null, sfx: [] }, ending_from: 30,
  captions: { y: 1390, size: 104 },
};

export type SheetProps = {
  piece: string;
  title: string;
  palette: string;
  base: Record<string, unknown>;
  variants: { label: string; props: Record<string, unknown> }[];
  cols: number;
  cell: [number, number];
  scale: number;
  ground: number; // y of the feet inside a cell
};

/** A character sheet: the same piece in every variant (expressions, poses), on a grid with labels. */
const makeSheet = (pieces: Pieces): React.FC<SheetProps> => {
  const Sheet: React.FC<SheetProps> = ({ piece, title, palette: pal, base: baseProps, variants, cols, cell, scale, ground }) => {
    const p = palette(pal);
    const Comp = pieces[piece];
    if (!variants.length) variants = Comp?.sheet ?? [{ label: piece, props: {} }];
    const rows = Math.ceil(variants.length / cols);
    const W = cols * cell[0];
    const H = rows * cell[1] + 110;
    return (
      <PaletteContext.Provider value={p}>
        <AbsoluteFill style={{ backgroundColor: p.papel }}>
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
            <Defs />
            <text x={30} y={72} fontFamily={DISPLAY} fontWeight={900} fontSize={56} fill={p.tinta}>{title}</text>
            {variants.map((v, i) => {
              const cx = (i % cols) * cell[0];
              const cy = 110 + Math.floor(i / cols) * cell[1];
              const props = { ...baseProps, ...v.props };
              const talk = typeof v.props._talk === "number" ? (v.props._talk as number) : 0;
              if (Comp?.kind === "fondo") {
                // a background: a miniature of the whole frame (1080×1920) fitted in the cell
                const k = Math.min((cell[0] - 16) / 1080, (cell[1] - 60) / 1920);
                return (
                  <g key={i} transform={`translate(${cx} ${cy})`}>
                    <clipPath id={`c${i}`}><rect x={8} y={8} width={1080 * k} height={1920 * k} /></clipPath>
                    <g clipPath={`url(#c${i})`}>
                      <g transform={`translate(8 8) scale(${k})`}>
                        <Comp frame={40} t={40} props={props} prev={props} since={99} talk={0} cues={{}} seed={i * 13}
                          place={{ x: 0, y: 0, scale: 1, flip: false }} />
                      </g>
                    </g>
                    <rect x={8} y={8} width={1080 * k} height={1920 * k} fill="none" stroke={p.tinta} strokeWidth={2} />
                    <text x={cell[0] / 2} y={cell[1] - 26} textAnchor="middle" fontFamily={TEXT} fontWeight={700} fontSize={26} fill={p.tinta}>{v.label}</text>
                  </g>
                );
              }
              return (
                <g key={i} transform={`translate(${cx} ${cy})`}>
                  <rect x={8} y={8} width={cell[0] - 16} height={cell[1] - 16} fill={p.papelLuz} stroke={p.tinta} strokeWidth={2} opacity={0.9} />
                  <g transform={`translate(${cell[0] / 2} ${ground})`}>
                    <g filter="url(#sombra)">
                      <g transform={`scale(${scale})`}>
                        {Comp ? <Comp frame={40} t={40} props={props} prev={props} since={99} talk={talk} cues={{}} seed={i * 13}
                          place={{ x: cx + cell[0] / 2, y: cy + ground, scale, flip: false }} /> : null}
                      </g>
                    </g>
                  </g>
                  <text x={cell[0] / 2} y={cell[1] - 26} textAnchor="middle" fontFamily={TEXT} fontWeight={700} fontSize={26} fill={p.tinta}>{v.label}</text>
                </g>
              );
            })}
          </svg>
          <PaperTexture opacity={0.25} />
        </AbsoluteFill>
      </PaletteContext.Provider>
    );
  };
  return Sheet;
};

export const makeRoot = (episode: Record<string, unknown> = {}): React.FC => {
  const pieces = collect(base, characters, episode);
  const Reel = makeReel(pieces);
  const Stills = makeStills(pieces);
  const Sheet = makeSheet(pieces);
  const Root: React.FC = () => (
    <>
      <Composition id="Reel" component={Reel} fps={FPS} width={WIDTH} height={HEIGHT} durationInFrames={30}
        defaultProps={{ timeline: EMPTY }}
        calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, props.timeline.frames), fps: props.timeline.fps,
          width: props.timeline.width, height: props.timeline.height })} />
      <Composition id="Fotogramas" component={Stills} fps={FPS} width={WIDTH} height={HEIGHT} durationInFrames={1}
        defaultProps={{ timeline: EMPTY, frames: [0] }}
        calculateMetadata={({ props }) => ({ durationInFrames: Math.max(1, props.frames.length), width: props.timeline.width, height: props.timeline.height })} />
      <Composition id="Hoja" component={Sheet} fps={FPS} width={1200} height={900} durationInFrames={1}
        defaultProps={{ piece: "Persona", title: "Persona", palette: "alfar", base: {}, variants: [{ label: "neutral", props: {} }], cols: 4, cell: [300, 420] as [number, number], scale: 0.6, ground: 360 }}
        calculateMetadata={({ props }) => {
          const n = props.variants.length || pieces[props.piece]?.sheet?.length || 1;
          return { width: props.cols * props.cell[0], height: Math.ceil(n / props.cols) * props.cell[1] + 110 };
        }} />
    </>
  );
  return Root;
};
