// What Python (reels/tiempos.py) hands to Remotion: episodes/<slug>/timeline.json. Every time is already resolved to
// frames there (events anchored to words, shots, the ending); this side only draws.
import type React from "react";

export type Pt = [number, number];

export type Word = { text: string; start: number; end: number; beat: number; voice: string }; // seconds

export type TActor = {
  id: string;
  piece: string;
  x: number;
  y: number;
  scale: number;
  rot: number;
  props: Record<string, unknown>;
  voice: string | null; // whose words move its mouth
  z: number;
  flip: boolean;
  hidden: boolean; // starts hidden (an «enter» event shows it)
  shadow: boolean;
};

export type TCamera = { zoom: number; focus: Pt; punch: boolean; pan: Pt };

export type TShot = {
  index: number;
  from: number;
  to: number;
  scene: string;
  options: Record<string, unknown>;
  camera: TCamera;
  actors: TActor[];
};

export type TEvent = {
  frame: number;
  type:
    | "act" | "cue" | "reveal" | "enter" | "exit" | "move" | "stamp" | "count" | "count_break" | "label"
    | "shake" | "flash" | "sfx" | "question" | "sparkle";
  shot: number; // index of the shot it belongs to
  beat: number | null;
  actor?: string;
  props?: Record<string, unknown>;
  name?: string;
  piece?: string;
  scale?: number;
  from?: string; // enter: left | right | top | bottom | pop
  to?: string | Pt;
  x?: number;
  y?: number;
  seconds?: number;
  text?: string;
  rot?: number;
  size?: number;
  color?: string;
  until?: number; // frame
  value?: number;
  strength?: number;
};

export type TBubble = { actor: string | null; x: number | null; y: number | null; shout: boolean; width: number };

export type TBeat = {
  id: number;
  voice: string;
  line: string;
  start: number; // seconds of the first word
  end: number; // seconds of the last word
  from: number; // frames (first word)
  to: number;
  highlight: string[];
  bubble: TBubble | null;
  captions: boolean;
};

export type TCounter = { label: string; kind: "rodillo" | "barra"; start: number; max: number; from: number; suffix: string };

export type Timeline = {
  slug: string;
  title: string;
  series: string | null;
  work: string | null;
  palette: string;
  fps: number;
  width: number;
  height: number;
  frames: number;
  words: Word[];
  beats: TBeat[];
  shots: TShot[];
  events: TEvent[];
  counter: TCounter | null;
  title_card: { lines: string[]; highlight: string[]; from: number; to: number } | null;
  tags_from: number | null;
  audio: {
    voices: { file: string; frame: number; volume: number }[];
    music: { file: string; volume: number; from: number; fade_out: number; loop?: boolean } | null;
    sfx: { file: string; frame: number; volume: number }[];
  };
  ending_from: number;
  captions: { y: number; size: number };
};

/** What every piece (character, object, background) receives. */
export type PieceProps = {
  frame: number; // absolute frame of the reel
  t: number; // frames since its shot started
  props: Record<string, unknown>; // current props (after every «act» so far)
  prev: Record<string, unknown>; // props before the last change
  since: number; // frames since the last change of props
  talk: number; // 0..1: its voice is sounding now
  cues: Record<string, number>; // named moments (absolute frames) of this actor
  seed: number; // stable per actor: phase for blinks and sways
  place: { x: number; y: number; scale: number; flip: boolean }; // where it stands in the frame (to aim at other things)
};

/** A piece is a React component plus optional metadata: where its head is (speech bubbles point there), its height,
 *  and the variants its character sheet shows (reels personaje / reels hoja). */
export type Piece = React.FC<PieceProps> & {
  head?: (props: Record<string, unknown>) => Pt;
  sheet?: { label: string; props: Record<string, unknown> }[];
  kind?: "fondo" | "actor" | "objeto";
  about?: string; // one line for docs/piezas.md and the catalogue
};

export const num = (v: unknown, d: number): number => (typeof v === "number" && Number.isFinite(v) ? v : d);
export const str = (v: unknown, d: string): string => (typeof v === "string" && v ? v : d);
export const bool = (v: unknown, d = false): boolean => (typeof v === "boolean" ? v : d);
