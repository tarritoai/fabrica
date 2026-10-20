// Mirrors episodes/<slug>/timeline.json (written by reels/timeline.py).
export type Word = { text: string; start: number; end: number };
export type Viseme = { start: number; end: number; viseme: string };

export type TimelineBeat = {
  id: number;
  speaker: string | null;
  line: string | null;
  camera: string;
  event: { component: string; props: Record<string, unknown> } | null;
  sfx: string[];
  sfx_at?: number[];
  start_frame: number;
  end_frame: number;
  subtitle_color?: string;
  audio: { file: string; offset: number; duration: number; words: Word[]; visemes?: Viseme[]; gain?: number } | null;
  nonverbal_audio?: { file: string; offset: number } | null;
  ambience?: string | null;
};

export type Timeline = {
  slug: string;
  title: string;
  tone?: string;
  hook?: string | null;
  series?: { name: string; part: number; of?: number | null } | null;
  fps: number;
  width: number;
  height: number;
  total_frames: number;
  beats: TimelineBeat[];
};

export type FinalProps = {
  timeline: Timeline;
  // Paths relative to the episode dir, which is passed as --public-dir.
  video: string;
  videoOffset?: number;
  music?: { file: string; score?: boolean; swell_at_beat: number | null; cut_at_beat?: number | null; start_at_beat?: number | null; resume_at_beat?: number | null; fade_in?: number; align_end?: boolean; duration?: number | null; swell_level?: number; start_delay?: number; restart?: boolean; duck?: number[] | null; duck_db?: number; cut_fade?: number | null } | null;
};
