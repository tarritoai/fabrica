// The engine: draws any episodes/<slug>/timeline.json. Shots (a background + actors), events anchored to words
// (already turned into frames by Python), the lettering layer and the sound. An episode never needs its own Reel:
// what changes from one story to another is the script and, if it needs them, new pieces.
import React, { useMemo } from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Defs, Puff, Sparkles, SpeedLines } from "./effects";
import { Bubble, Captions, Counter, Label, PaperTexture, Question, Stamp, Tags, TitleCard } from "./overlays";
import { PaletteContext, palette } from "./style";
import type { Piece, TActor, TEvent, TShot, Timeline, Word } from "./types";
import { num } from "./types";
import { transition } from "./draw";
import "./fonts";

export type Pieces = Record<string, Piece>;

const easeInOut = (t: number) => (t < 0 ? 0 : t > 1 ? 1 : t * t * (3 - 2 * t));

type ActorNow = {
  actor: TActor;
  piece: string;
  scale: number;
  x: number;
  y: number;
  props: Record<string, unknown>;
  prev: Record<string, unknown>;
  since: number;
  visible: boolean;
  enter: { at: number; from: string } | null;
  exit: { at: number; to: string } | null;
  reveal: { at: number; piece: string; scale: number; props: Record<string, unknown> } | null; // the one before
  pendingReveal: boolean;
  moving: number; // -1/0/1: running left/right
  cues: Record<string, number>;
};

/** Where an actor is and what it looks like at `frame`, folding every event of its shot up to then. */
const actorAt = (a: TActor, shot: TShot, events: TEvent[], frame: number, fps: number): ActorNow => {
  const st: ActorNow = {
    actor: a, piece: a.piece, scale: a.scale, x: a.x, y: a.y, props: { ...a.props }, prev: { ...a.props },
    since: frame - shot.from, visible: !a.hidden, enter: null, exit: null, reveal: null, pendingReveal: false, moving: 0, cues: {},
  };
  for (const ev of events) {
    if (ev.actor !== a.id) continue;
    if (ev.type === "cue" && ev.name) st.cues[ev.name] = ev.frame;
    if (ev.frame > frame) {
      if (ev.type === "reveal") st.pendingReveal = true;
      continue;
    }
    switch (ev.type) {
      case "act":
        st.prev = st.props;
        st.props = { ...st.props, ...(ev.props ?? {}) };
        st.since = frame - ev.frame;
        break;
      case "reveal":
        st.reveal = { at: ev.frame, piece: st.piece, scale: st.scale, props: st.props };
        st.piece = ev.piece ?? st.piece;
        if (ev.scale) st.scale = ev.scale;
        st.prev = st.props;
        st.props = { ...st.props, ...(ev.props ?? {}) };
        st.since = frame - ev.frame;
        break;
      case "enter":
        st.visible = true;
        st.enter = { at: ev.frame, from: (ev.from as string) ?? "pop" };
        st.since = frame - ev.frame; // a piece that animates itself starts when it appears, not at the cut
        break;
      case "exit":
        st.exit = { at: ev.frame, to: typeof ev.to === "string" ? ev.to : "pop" };
        break;
      case "move": {
        const dur = Math.max(1, Math.round((ev.seconds ?? 0.6) * fps));
        const k = easeInOut((frame - ev.frame) / dur);
        const tx = ev.x ?? st.x;
        const ty = ev.y ?? st.y;
        if (frame - ev.frame < dur) st.moving = Math.sign(tx - st.x);
        st.x = st.x + (tx - st.x) * k;
        st.y = st.y + (ty - st.y) * k;
        break;
      }
      default:
        break;
    }
  }
  return st;
};

const talkOf = (words: Word[], voice: string | null, frame: number, fps: number): number => {
  if (!voice) return 0;
  const t = frame / fps;
  return words.some((w) => w.voice === voice && t >= w.start - 0.02 && t <= w.end + 0.02) ? 1 : 0;
};

const Missing: React.FC<{ name: string }> = ({ name }) => (
  <g>
    <rect x={-120} y={-300} width={240} height={300} fill="#ffffff" fillOpacity={0.6} stroke="#C92A23" strokeWidth={6} strokeDasharray="18 12" />
    <text x={0} y={-140} textAnchor="middle" fontSize={34} fontFamily="Big Shoulders" fontWeight={900} fill="#C92A23">FALTA</text>
    <text x={0} y={-100} textAnchor="middle" fontSize={30} fontFamily="Big Shoulders" fontWeight={800} fill="#C92A23">{name}</text>
  </g>
);

const ActorView: React.FC<{ st: ActorNow; pieces: Pieces; frame: number; t: number; talk: number; seed: number }> = ({ st, pieces, frame, t, talk, seed }) => {
  if (!st.visible) return null;
  let dx = 0;
  let dy = 0;
  let pop = 1;
  if (st.enter) {
    const k = easeInOut((frame - st.enter.at) / 10);
    const off = 760 * (1 - k);
    if (st.enter.from === "left") dx = -off;
    else if (st.enter.from === "right") dx = off;
    else if (st.enter.from === "top") dy = -off * 1.6;
    else if (st.enter.from === "bottom") dy = off;
    else pop = interpolate(frame - st.enter.at, [0, 5, 8], [0, 1.12, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  }
  if (st.exit) {
    const k = easeInOut((frame - st.exit.at) / 10);
    if (k >= 1) return null;
    const off = 760 * k;
    if (st.exit.to === "left") dx -= off;
    else if (st.exit.to === "right") dx += off;
    else if (st.exit.to === "top") dy -= off * 1.6;
    else if (st.exit.to === "bottom") dy += off;
    else pop *= 1 - k;
  }
  const revealK = st.reveal ? frame - st.reveal.at : 999;
  const bounce = revealK < 7 ? 1 + 0.12 * (1 - revealK / 7) : 1;
  const Comp = pieces[st.piece];
  const sx = st.scale * (st.actor.flip ? -1 : 1) * pop * bounce;
  const sy = st.scale * pop * bounce;
  const shake = st.pendingReveal ? Math.sin(frame / 2.6) * 3 : 0;
  const base = st.actor.rot ?? 0;
  const rot = transition(num(st.prev.rot, base), num(st.props.rot, base), st.since, 8, 0.1); // `act` can tilt it
  return (
    <g transform={`translate(${st.x + dx + shake} ${st.y + dy}) rotate(${rot})`}>
      {st.moving !== 0 && <g transform={`translate(0 ${-150 * st.scale})`}><SpeedLines frame={frame} dir={st.moving} spread={260 * st.scale} /></g>}
      <g filter={st.actor.shadow ? "url(#sombra)" : undefined}>
        <g transform={`scale(${sx} ${sy})`}>
          {Comp ? (
            <Comp frame={frame} t={t} props={st.props} prev={st.prev} since={st.since} talk={talk} cues={st.cues} seed={seed}
              place={{ x: st.x, y: st.y, scale: st.scale, flip: st.actor.flip }} />
          ) : (
            <Missing name={st.piece} />
          )}
        </g>
      </g>
      {st.pendingReveal && <g transform={`translate(0 ${-60 * st.scale})`}><Sparkles frame={frame} n={8} w={460 * st.scale} h={560 * st.scale} /></g>}
      {st.reveal && revealK < 14 && <g transform={`translate(0 ${-230 * st.scale})`}><Puff p={revealK / 14} r={260 * st.scale} /></g>}
    </g>
  );
};

const hash = (s: string) => {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
};

export const ReelScene: React.FC<{ tl: Timeline; pieces: Pieces; frame: number; withSound: boolean }> = ({ tl, pieces, frame, withSound }) => {
  const fps = tl.fps;
  const data = useMemo(() => {
    const byShot = new Map<number, TEvent[]>();
    for (const ev of [...tl.events].sort((a, b) => a.frame - b.frame)) {
      byShot.set(ev.shot, [...(byShot.get(ev.shot) ?? []), ev]);
    }
    const counts = tl.events.filter((e) => e.type === "count").map((e) => ({ frame: e.frame, value: e.value ?? 0 }));
    const broken = tl.events.find((e) => e.type === "count_break")?.frame ?? null;
    const wordsByBeat = new Map<number, Word[]>();
    for (const w of tl.words) wordsByBeat.set(w.beat, [...(wordsByBeat.get(w.beat) ?? []), w]);
    return { byShot, counts, broken, wordsByBeat };
  }, [tl]);

  const shot = tl.shots.find((s) => frame >= s.from && frame < s.to) ?? tl.shots[tl.shots.length - 1];
  const events = shot ? data.byShot.get(shot.index) ?? [] : [];
  const t = shot ? frame - shot.from : frame;

  // camera: slow push over the shot, a punch on the cut, shakes
  let cam = "";
  if (shot) {
    const len = Math.max(1, shot.to - shot.from);
    const k = easeInOut(t / len);
    const punch = shot.camera.punch ? 1 + 0.06 * Math.max(0, 1 - t / 6) : 1;
    const z = (1 + shot.camera.zoom * k) * punch;
    const [fx, fy] = shot.camera.focus;
    const [px, py] = shot.camera.pan;
    let sx = 0;
    let sy = 0;
    for (const ev of tl.events) {
      if (ev.type !== "shake" || frame < ev.frame || frame > ev.frame + 12) continue;
      const a = (ev.strength ?? 1) * 16 * (1 - (frame - ev.frame) / 12);
      sx += Math.sin(frame * 2.7) * a;
      sy += Math.cos(frame * 3.3) * a * 0.6;
    }
    cam = `translate(${px * k + sx} ${py * k + sy}) translate(${fx} ${fy}) scale(${z}) translate(${-fx} ${-fy})`;
  }

  const flash = tl.events.filter((e) => e.type === "flash" && frame >= e.frame && frame < e.frame + 8).map((e) => 1 - (frame - e.frame) / 8)[0] ?? 0;
  const Scene = shot ? pieces[shot.scene] : undefined;
  const actors = shot ? shot.actors.map((a) => actorAt(a, shot, events, frame, fps)).sort((a, b) => a.actor.z - b.actor.z || a.y - b.y) : [];
  const stamps = tl.events.filter((e) => e.type === "stamp" && frame >= e.frame && (e.until === undefined || frame <= e.until));
  const labels = tl.events.filter((e) => e.type === "label");
  const question = tl.events.find((e) => e.type === "question");
  const sparkles = tl.events.filter((e) => e.type === "sparkle" && frame >= e.frame && frame < e.frame + 18);
  const pal = palette(tl.palette);
  /** Where an actor's head is (frame coordinates) at a given frame: speech bubbles point there. */
  const headOf = (actorId: string | null, at: number): [number, number] | null => {
    if (!actorId) return null;
    const s = tl.shots.find((x) => at >= x.from && at < x.to) ?? shot;
    const a = s?.actors.find((x) => x.id === actorId);
    if (!s || !a) return null;
    const st = actorAt(a, s, data.byShot.get(s.index) ?? [], Math.max(at, frame), fps);
    const head = pieces[st.piece]?.head?.(st.props) ?? [0, -480];
    return [st.x + head[0] * st.scale * (a.flip ? -1 : 1), st.y + head[1] * st.scale];
  };

  return (
    <PaletteContext.Provider value={pal}>
      <AbsoluteFill style={{ backgroundColor: pal.papel }}>
        <svg width={tl.width} height={tl.height} viewBox={`0 0 ${tl.width} ${tl.height}`}>
          <Defs />
          <g transform={cam}>
            {shot && (Scene ? (
              <Scene frame={frame} t={t} props={shot.options} prev={shot.options} since={t} talk={0} cues={{}} seed={shot.index}
                place={{ x: 0, y: 0, scale: 1, flip: false }} />
            ) : (
              <g><rect width={tl.width} height={tl.height} fill={pal.papel} /><g transform="translate(540 1000)"><Missing name={shot.scene} /></g></g>
            ))}
            {actors.map((st) => (
              <ActorView key={st.actor.id} st={st} pieces={pieces} frame={frame} t={t} seed={hash(st.actor.id)}
                talk={talkOf(tl.words, st.actor.voice, frame, fps)} />
            ))}
            {sparkles.map((e, i) => (
              <g key={i} transform={`translate(${e.x ?? 540} ${e.y ?? 900}) scale(${1 + (frame - e.frame) / 30})`} opacity={1 - (frame - e.frame) / 18}>
                <Sparkles frame={frame} n={9} w={420} h={420} />
              </g>
            ))}
          </g>
        </svg>
        <PaperTexture />
        <svg width={tl.width} height={tl.height} viewBox={`0 0 ${tl.width} ${tl.height}`} style={{ position: "absolute", inset: 0 }}>
          <Defs />
          {tl.title_card && (
            <TitleCard frame={frame} lines={tl.title_card.lines} highlight={tl.title_card.highlight} series={tl.series}
              from={tl.title_card.from} to={tl.title_card.to} />
          )}
          {tl.tags_from !== null && <Tags frame={frame} series={tl.series} work={tl.work} from={tl.tags_from} />}
          {tl.counter && <Counter frame={frame} counter={tl.counter} values={data.counts} broken={data.broken} />}
          {stamps.map((e, i) => (
            <Stamp key={i} frame={frame} at={e.frame} text={e.text ?? ""} x={e.x ?? 540} y={e.y ?? 900} rot={e.rot} size={e.size} color={e.color} until={e.until} />
          ))}
          {labels.map((e, i) => (
            <Label key={i} frame={frame} at={e.frame} until={e.until ?? tl.frames} x={e.x ?? 540} y={e.y ?? 800} text={e.text ?? ""} rot={e.rot} size={e.size} />
          ))}
          {tl.beats.map((b, i) => {
            const words = data.wordsByBeat.get(b.id) ?? [];
            const next = tl.beats[i + 1];
            if (b.bubble) {
              const until = next ? Math.min(b.end + 0.4, next.start - 0.05) : Math.min(b.end + 0.6, tl.ending_from / fps - 0.02);
              if (frame / fps < b.start - 0.2 || frame / fps > until) return null;
              return <Bubble key={b.id} frame={frame} words={words} bubble={b.bubble} until={until} anchor={headOf(b.bubble.actor, b.from)} />;
            }
            if (!b.captions) return null;
            return <Captions key={b.id} index={i} frame={frame} words={words} highlight={b.highlight} y={tl.captions.y} size={tl.captions.size} cutAt={next?.start} />;
          })}
          {question && <Question frame={frame} at={question.frame} text={question.text ?? ""} />}
        </svg>
        {flash > 0 && <AbsoluteFill style={{ backgroundColor: pal.papelLuz, opacity: flash * 0.85 }} />}
      </AbsoluteFill>
      {withSound && <Sound tl={tl} />}
    </PaletteContext.Provider>
  );
};

const Sound: React.FC<{ tl: Timeline }> = ({ tl }) => {
  const m = tl.audio.music;
  return (
    <>
      {m && (
        <Sequence from={m.from}>
          <Audio src={staticFile(m.file)} loop={m.loop !== false} volume={(f) => interpolate(f + m.from, [m.from, m.from + 8, tl.frames - m.fade_out, tl.frames], [0, m.volume, m.volume, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
        </Sequence>
      )}
      {tl.audio.voices.map((v, i) => (
        <Sequence key={`v${i}`} from={v.frame}>
          <Audio src={staticFile(v.file)} volume={v.volume} />
        </Sequence>
      ))}
      {tl.audio.sfx.filter((s) => s.frame >= 0).map((s, i) => (
        <Sequence key={`s${i}`} from={s.frame}>
          <Audio src={staticFile(s.file)} volume={s.volume} />
        </Sequence>
      ))}
    </>
  );
};

/** The reel, with sound. */
export const makeReel = (pieces: Pieces): React.FC<{ timeline: Timeline }> => {
  const Reel: React.FC<{ timeline: Timeline }> = ({ timeline }) => {
    const frame = useCurrentFrame();
    return <ReelScene tl={timeline} pieces={pieces} frame={frame} withSound />;
  };
  return Reel;
};

/** Key frames of the reel as an image sequence (one per «frame» of this composition), silent: for the eye. */
export const makeStills = (pieces: Pieces): React.FC<{ timeline: Timeline; frames: number[] }> => {
  const Stills: React.FC<{ timeline: Timeline; frames: number[] }> = ({ timeline, frames }) => {
    const i = useCurrentFrame();
    return <ReelScene tl={timeline} pieces={pieces} frame={frames[Math.min(i, frames.length - 1)] ?? 0} withSound={false} />;
  };
  return Stills;
};
