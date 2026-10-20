import React from "react";
import { AbsoluteFill, Audio, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CounterReveal, CounterRevealProps } from "./CounterReveal";
import { fontFamily } from "../fonts";
import { Subtitle, subtitleTiming } from "./Subtitle";
import { FinalProps, Timeline, TimelineBeat } from "./types";

// Music bed (PLAN §5b): it sits under the conversation as a whole instead of pumping on every line.
// Lines closer than BRIDGE are one dialogue block; the music dips once for the block (slow ramps)
// and only comes back up in real silences (reactions, screens), then swells at the chosen beat.
const MUSIC_BASE = 0.24;
const UNDER_DIALOGUE = 0.62; // ≈ -4 dB: a gentle dip, never a hole
const SWELL = 0.6;
const BRIDGE = 1.8; // s: shorter silences don't lift the music
const ATTACK = 1.0; // s: starts dipping before the first word of a block
const RELEASE = 1.8; // s: comes back up slowly after the last word
const CUT_DELAY = 0.25; // s into the cut beat: the new shot lands, then the music dies
const CUT_FADE = 2; // frames: a dead stop without a click

const dialogueBlocks = (tl: Timeline): [number, number][] => {
  const spans = tl.beats
    .filter((b) => b.audio)
    .map((b): [number, number] => {
      const s = b.start_frame + Math.round(b.audio!.offset * tl.fps);
      return [s, s + Math.round(b.audio!.duration * tl.fps)];
    })
    .sort((a, b) => a[0] - b[0]);
  const blocks: [number, number][] = [];
  for (const [a, b] of spans) {
    const last = blocks[blocks.length - 1];
    if (last && a - last[1] < BRIDGE * tl.fps) last[1] = Math.max(last[1], b);
    else blocks.push([a, b]);
  }
  return blocks;
};

const smooth = (x: number) => x * x * (3 - 2 * x);

const musicVolume = (
  frame: number,
  tl: Timeline,
  blocks: [number, number][],
  swellFrame: number | null,
  cutFrame: number | null,
  startFrame: number | null = null,
  ownEnding = false,
  swellLevel = SWELL,
  resumeFrame: number | null = null,
  fadeSecs = 1.5,
  cutFade = CUT_FADE,
): number => {
  // 1 = fully under dialogue, 0 = free.
  let under = 0;
  for (const [a, b] of blocks) {
    const inA = interpolate(frame, [a - ATTACK * tl.fps, a], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    const outB = interpolate(frame, [b, b + RELEASE * tl.fps], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    under = Math.max(under, smooth(Math.min(inA, outB)));
  }
  let level = MUSIC_BASE * (1 - under * (1 - UNDER_DIALOGUE));
  if (swellFrame !== null && frame >= swellFrame) {
    const k = smooth(interpolate(frame, [swellFrame, swellFrame + tl.fps * 1.5], [0, 1], { extrapolateRight: "clamp" }));
    level += (swellLevel * (1 - under * 0.4) - level) * k;
  }
  const fadeIn = interpolate(frame, [0, tl.fps * 0.8], [0, 1], { extrapolateRight: "clamp" });
  // A clip aligned to end with the video brings its own ending: only a hair of fade to avoid a click.
  const fadeOut = interpolate(frame, [tl.total_frames - tl.fps * (ownEnding ? 0.15 : 1.5), tl.total_frames], [1, 0], { extrapolateLeft: "clamp" });
  let cut = cutFrame === null ? 1 : smooth(interpolate(frame, [cutFrame, cutFrame + cutFade], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  // After a cut the music can come back (music.resume_at_beat): it kept playing silently, so it returns further on.
  if (resumeFrame !== null && frame >= resumeFrame) cut = smooth(interpolate(frame, [resumeFrame, resumeFrame + tl.fps * fadeSecs], [0, 1], { extrapolateRight: "clamp" }));
  // A late entrance (music.start_at_beat): silence until then, then a slow fade in.
  const enter = startFrame === null ? 1 : smooth(interpolate(frame, [startFrame, startFrame + tl.fps * fadeSecs], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return level * (startFrame === null ? fadeIn : 1) * fadeOut * cut * enter;
};

// Colour grade on the 3D image only (subtitles and overlays stay true): livelier colour and deeper
// contrast so the first frame pops in the feed. The renders come out a little flat and dark at night.
const GRADE = "saturate(1.22) contrast(1.1) brightness(1.04)";

// Room tone (night rain + hum) so the gaps between lines sound like a room, not digital silence.
const AMBIENCE_VOLUME: Record<string, number> = { agridulce: 0.35, comedia: 0.25, serie: 0.3 };
// Other backgrounds a beat can switch to (beat.ambience), with hard cuts: they mark a change of time or place.
// fade (s): most cut hard (a change of place); the murmur of the people's lights swells in and out.
const AMBIENCES: Record<string, { file: string; volume: number; fade?: number }> = {
  ruinas: { file: "sfx/amb_ruinas.wav", volume: 0.28 },
  luces: { file: "sfx/amb_luces.wav", volume: 0.5, fade: 2.0 },
};

// [start, end, kind] spans of each background along the timeline.
const ambienceSpans = (tl: Timeline): [number, number, string][] => {
  const spans: [number, number, string][] = [];
  let kind = "noche";
  let from = 0;
  for (const b of tl.beats) {
    if (b.ambience && b.ambience !== kind) {
      spans.push([from, b.start_frame, kind]);
      kind = b.ambience;
      from = b.start_frame;
    }
  }
  spans.push([from, tl.total_frames, kind]);
  return spans;
};

const SFX_VOLUME: Record<string, number> = { tension: 0.55, typing_tiny: 0.5, click: 0.5, toc: 0.55, ding: 0.6, ding_alarm: 0.75, whoosh: 0.4, error: 0.6, portal_rumble: 0.7, tunnel_whoosh: 0.8, sky_burst: 0.7, cadena: 0.55, grifo: 0.45 };

// The AI writing its memory (MemorySave): one soft digital tick per character, no keyboard
// (it writes with its mind; its thinking light pulses with the same clock). Mirrors screens/MemorySave.tsx.
const TYPE_SPEED = 0.055;
const TYPE_START = 0.3;
const TICK_VOLUME = 0.32;

const typing = (beat: TimelineBeat): { start: number; speed: number } => {
  const props = (beat.event?.props ?? {}) as { type_start?: number; type_speed?: number };
  return { start: props.type_start ?? TYPE_START, speed: props.type_speed ?? TYPE_SPEED };
};

const typedChars = (beat: TimelineBeat): string => {
  if (beat.event?.component !== "MemorySave") return "";
  const props = beat.event.props as { lines?: string[]; from_char?: number; to_char?: number | null };
  const all = (props.lines ?? []).join("");
  return all.slice(props.from_char ?? 0, props.to_char ?? all.length);
};

const BeatSounds: React.FC<{ beat: TimelineBeat; fps: number }> = ({ beat, fps }) => {
  const stagger = Number(beat.event?.props.stagger ?? 0.45);
  const delay = Number(beat.event?.props.delay ?? 0.3);
  return (
    <>
      {beat.audio && (
        <Sequence from={beat.start_frame + Math.round(beat.audio.offset * fps)} layout="none">
          <Audio src={staticFile(beat.audio.file)} volume={beat.audio.gain ?? 1} />
        </Sequence>
      )}
      {beat.nonverbal_audio && (
        <Sequence from={beat.start_frame + Math.round(beat.nonverbal_audio.offset * fps)} layout="none">
          <Audio src={staticFile(beat.nonverbal_audio.file)} />
        </Sequence>
      )}
      {[...typedChars(beat)].map((ch, i) =>
        ch === " " ? null : (
          <Sequence key={`tick-${i}`} from={beat.start_frame + Math.round((typing(beat).start + i * typing(beat).speed) * fps)} durationInFrames={4} layout="none">
            {/* Slight level variation so it doesn't sound like a metronome. */}
            <Audio src={staticFile("sfx/tick.wav")} volume={TICK_VOLUME * (0.75 + 0.25 * Math.abs(Math.sin(i * 2.3)))} />
          </Sequence>
        ),
      )}
      {beat.sfx.map((name, i) => (
        // With a screen event, sfx[i] lands with notification i; otherwise at the cut.
        <Sequence
          key={i}
          from={beat.start_frame + (beat.sfx_at?.[i] != null ? Math.round(beat.sfx_at[i] * fps) : beat.event ? Math.round((delay + i * stagger) * fps) : 0)}
          layout="none"
        >
          <Audio src={staticFile(`sfx/${name}.wav`)} volume={SFX_VOLUME[name] ?? 0.6} />
        </Sequence>
      ))}
    </>
  );
};

// The subtitle shows from the first sound of the line (a long pause_before would show it early otherwise).
const subtitleFor = (beat: TimelineBeat, fps: number) => {
  const a = beat.audio;
  if (!a || !beat.line) return { from: beat.start_frame, times: undefined as number[] | undefined };
  const lead = beat.start_frame + Math.round(a.offset * fps);
  const maxSpan = Math.max(0.1, (beat.end_frame - lead) / fps - 0.2);
  const { start, times } = subtitleTiming(beat.line, a.visemes, maxSpan);
  const from = Math.min(lead + Math.round(start * fps), beat.end_frame - 1);
  return { from, times };
};

// Opening hook text (timeline.hook): small and clean at the top, under the app's own header, for ~2.5 s.
// It answers "what is this about?" before the thumb decides; it never covers a face (faces sit mid-frame).
const HOOK_SECS = 2.6;
const HookText: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const t = frame / fps;
  const k = interpolate(t, [0, 0.12, HOOK_SECS - 0.3, HOOK_SECS], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div
      style={{
        position: "absolute",
        top: height * 0.13,
        left: 90,
        right: 140,
        textAlign: "center",
        fontFamily,
        fontWeight: 800,
        fontSize: 54,
        lineHeight: 1.15,
        color: "#fff7ea",
        opacity: k,
        transform: `translateY(${(1 - k) * -12}px)`,
        textShadow: "0 2px 4px rgba(0,0,0,0.9), 0 0 18px rgba(0,0,0,0.6)",
      }}
    >
      {text}
    </div>
  );
};

const SeriesMark: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12], [0, 0.85], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ opacity, color: "#f2ead8", fontFamily, fontWeight: 600, fontSize: 64, letterSpacing: 6 }}>{text}</div>
    </AbsoluteFill>
  );
};

export const Final: React.FC<FinalProps> = ({ timeline, video, music, videoOffset }) => {
  const fps = timeline.fps;
  const blocks = dialogueBlocks(timeline);
  const swellBeat = music?.swell_at_beat != null ? timeline.beats.find((b) => b.id === music.swell_at_beat) : undefined;
  const swellFrame = swellBeat ? swellBeat.start_frame : null;
  const cutBeat = music?.cut_at_beat != null ? timeline.beats.find((b) => b.id === music.cut_at_beat) : undefined;
  // music.cut_fade: instead of dying in a blink, the music melts away over that many seconds from the cut beat.
  const cutFade = music?.cut_fade ? Math.round(music.cut_fade * fps) : CUT_FADE;
  const cutFrame = cutBeat ? cutBeat.start_frame + (music?.cut_fade ? 0 : Math.round(CUT_DELAY * fps)) : null;
  const startBeat = music?.start_at_beat != null ? timeline.beats.find((b) => b.id === music.start_at_beat) : undefined;
  const musicStart = startBeat ? startBeat.start_frame + Math.round((music?.start_delay ?? 0) * fps) : null;
  const resumeBeat = music?.resume_at_beat != null ? timeline.beats.find((b) => b.id === music.resume_at_beat) : undefined;
  const resumeFrame = resumeBeat ? resumeBeat.start_frame : null;
  // music.duck: a stretch where the music sits a few dB lower (eases in/out over a second).
  const duckFrom = music?.duck ? timeline.beats.find((b) => b.id === music.duck![0])?.start_frame : undefined;
  const duckTo = music?.duck ? timeline.beats.find((b) => b.id === music.duck![1])?.end_frame : undefined;
  const duckGain = Math.pow(10, (music?.duck_db ?? -3) / 20);
  const duck = (f: number) =>
    duckFrom == null || duckTo == null
      ? 1
      : interpolate(f, [duckFrom - fps, duckFrom, duckTo, duckTo + fps], [1, duckGain, duckGain, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const spans = ambienceSpans(timeline);
  const nightAt = (f: number) => {
    const span = spans.find(([a, z]) => f >= a && f < z);
    return !span || span[2] === "noche" ? 1 : 0;
  };
  return (
    <AbsoluteFill style={{ background: "black" }}>
      {/* Partial previews pass a clip that starts at videoOffset. */}
      <Sequence from={videoOffset ?? 0} layout="none">
        <OffthreadVideo src={staticFile(video)} muted style={{ filter: GRADE }} />
      </Sequence>
      <Audio
        src={staticFile("sfx/amb_night.wav")}
        loop
        volume={(f) =>
          (AMBIENCE_VOLUME[timeline.tone ?? "comedia"] ?? 0.3) *
          nightAt(f) *
          // Reels loop: the room tone runs to the last frame (a fade-out would mark the seam).
          interpolate(f, [0, fps * 0.1], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })
        }
      />
      {spans
        .filter(([, , kind]) => AMBIENCES[kind])
        .map(([a, z, kind]) => (
          <Sequence key={`amb-${a}`} from={a} durationInFrames={z - a} layout="none">
            <Audio
              src={staticFile(AMBIENCES[kind].file)}
              loop
              volume={(f) => {
                const fd = Math.max(3, Math.min((z - a) / 2 - 1, Math.round((AMBIENCES[kind].fade ?? 0.1) * fps)));
                return AMBIENCES[kind].volume * interpolate(f, [0, fd, z - a - fd, z - a], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
              }}
            />
          </Sequence>
        ))}
      {music?.score && (
        // Musical episode (episode.score): the mix was written for these frames; it plays as is.
        <Audio src={staticFile(music.file)} />
      )}
      {music && !music.score && !music.align_end && !(music.restart && musicStart != null) && (
        <Audio src={staticFile(music.file)} loop volume={(f) => duck(f) * musicVolume(f, timeline, blocks, swellFrame, cutFrame, musicStart, false, SWELL, resumeFrame, music.fade_in ?? 1.5, cutFade)} />
      )}
      {music && !music.score && !music.align_end && music.restart && musicStart != null && (
        // Starts from the top of the song at its entrance (a hit), e.g. bursting out into a new world.
        <Sequence from={musicStart} layout="none">
          <Audio src={staticFile(music.file)} loop volume={(f) => duck(f + musicStart) * musicVolume(f + musicStart, timeline, blocks, swellFrame, cutFrame, musicStart, false, SWELL, resumeFrame, music.fade_in ?? 1.5, cutFade)} />
        </Sequence>
      )}
      {music && !music.score && music.align_end && music.duration && (
        // The clip's own ending (its climax) lands on the last frame: start that far before the end.
        <Sequence from={musicStart ?? 0} layout="none">
          <Audio
            src={staticFile(music.file)}
            startFrom={Math.max(0, Math.round(music.duration * fps) - (timeline.total_frames - (musicStart ?? 0)))}
            volume={(f) => duck(f + (musicStart ?? 0)) * musicVolume(f + (musicStart ?? 0), timeline, blocks, swellFrame, cutFrame, musicStart, true, music.swell_level ?? SWELL, resumeFrame, music.fade_in ?? 1.5, cutFade)}
          />
        </Sequence>
      )}
      {timeline.beats
        .filter((b) => b.event?.component === "CounterReveal")
        .map((b) => (
          <Sequence key={`ov-${b.id}`} from={b.start_frame} durationInFrames={b.end_frame - b.start_frame} layout="none">
            <CounterReveal {...(b.event!.props as CounterRevealProps)} durationInFrames={b.end_frame - b.start_frame} />
          </Sequence>
        ))}
      {timeline.beats.map((beat) => (
        <React.Fragment key={beat.id}>
          <BeatSounds beat={beat} fps={fps} />
          {beat.line && beat.event?.component !== "MemorySave" && (
            // From the first word, not the beat's start: a long pause_before would show the line before it's said.
            <Sequence from={subtitleFor(beat, fps).from} durationInFrames={beat.end_frame - subtitleFor(beat, fps).from} layout="none">
              <Subtitle
                text={beat.line}
                color={beat.subtitle_color ?? "white"}
                camera={beat.camera}
                tone={timeline.tone}
                times={subtitleFor(beat, fps).times}
              />
            </Sequence>
          )}
        </React.Fragment>
      ))}
      {timeline.hook && (
        <Sequence from={0} durationInFrames={Math.round(HOOK_SECS * fps)} layout="none">
          <HookText text={timeline.hook} />
        </Sequence>
      )}
      {/* Series cliffhanger: a small "1/3" fades in on the final black (never a big "Parte 1"). */}
      {(() => {
        const last = timeline.beats[timeline.beats.length - 1];
        const sr = timeline.series;
        if (!last || last.camera !== "negro" || !sr?.of) return null;
        return (
          <Sequence from={last.start_frame + Math.round(0.35 * fps)} layout="none">
            <SeriesMark text={`${sr.part}/${sr.of}`} />
          </Sequence>
        );
      })()}
    </AbsoluteFill>
  );
};
