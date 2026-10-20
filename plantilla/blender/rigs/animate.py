"""Bake per-frame animation for any character that follows the rig interface.

Everything is computed frame by frame in Python and written as whole F-curves:
emotions (eyes/brows/head), procedural actions (ctrl_body/ctrl_head), blinks,
talking motion and viseme mouth swaps.
"""

from __future__ import annotations

import math
import random
import zlib

from mathutils import Vector

from lib import bake, character_meta, find, lerp, rad, smoothstep

TRANSITION = 5  # frames to blend into a new beat's pose
CUT_CLEAN = 6  # frames after a camera cut with no blink in them

# brow_z: metres, brow_tilt: deg (+ = inner ends up / worried), eye_z/eye_s: scale factors,
# head_x: deg (+ = looks down), head_y: deg (side tilt), brow_asym: extra lift on brow_L.
EMOTIONS = {
    "neutral":   dict(brow_z=0.0,    brow_tilt=0,   eye_z=1.0,  eye_s=1.0,  head_x=0,   head_y=0,  brow_asym=0.0),
    "orgulloso": dict(brow_z=0.012,  brow_tilt=-10, eye_z=0.75, eye_s=1.0,  head_x=-10, head_y=4,  brow_asym=0.0),
    "confuso":   dict(brow_z=0.01,   brow_tilt=12,  eye_z=1.0,  eye_s=1.0,  head_x=0,   head_y=10, brow_asym=0.025),
    "alarma":    dict(brow_z=0.035,  brow_tilt=18,  eye_z=1.25, eye_s=1.15, head_x=-4,  head_y=0,  brow_asym=0.0),
    "juzgando":  dict(brow_z=-0.012, brow_tilt=-14, eye_z=0.4,  eye_s=1.0,  head_x=4,   head_y=-5, brow_asym=0.012),
    "hundido":   dict(brow_z=-0.005, brow_tilt=26,  eye_z=0.65, eye_s=0.95, head_x=16,  head_y=-3, brow_asym=0.0),
    "panico":    dict(brow_z=0.045,  brow_tilt=30,  eye_z=1.35, eye_s=1.25, head_x=-2,  head_y=0,  brow_asym=0.0),
    "aliviado":  dict(brow_z=0.008,  brow_tilt=10,  eye_z=0.55, eye_s=1.0,  head_x=-6,  head_y=3,  brow_asym=0.0),
}

# body_y/body_z: metres, body_x/body_yaw: deg (+x = lean forward), body_sz: scale, head_dx: deg added to the emotion's head_x.
ACTIONS = {
    "idle":            dict(body_y=0.0,   body_z=0.0,   body_x=0,   body_yaw=0,   body_sz=1.0,  head_dx=0),
    "talk_gesture":    dict(body_y=-0.02, body_z=0.0,   body_x=2,   body_yaw=0,   body_sz=1.0,  head_dx=0),
    "present_gesture": dict(body_y=0.0,   body_z=0.02,  body_x=-6,  body_yaw=-12, body_sz=1.03, head_dx=-6),
    "shrug":           dict(body_y=0.0,   body_z=0.0,   body_x=0,   body_yaw=0,   body_sz=1.0,  head_dx=0),
    "facepalm":        dict(body_y=0.0,   body_z=-0.02, body_x=4,  body_yaw=0,   body_sz=0.98, head_dx=28),
    "lean_in":         dict(body_y=-0.06, body_z=0.0,   body_x=6,   body_yaw=0,   body_sz=1.0,  head_dx=4),
    "look_phone":      dict(body_y=0.0,   body_z=0.0,   body_x=2,   body_yaw=0,   body_sz=1.0,  head_dx=22),
    # A startled jolt up with the head thrown back: the seated body already touches the backrest, so sliding or
    # tilting the body back pushes the chest through it (the grey backrest then shows in front of the torso).
    "recoil":          dict(body_y=0.0,   body_z=0.025, body_x=0,   body_yaw=0,   body_sz=1.0,  head_dx=-14),
    "slump":           dict(body_y=0.0,   body_z=-0.06, body_x=4,   body_yaw=0,   body_sz=0.93, head_dx=10),
    # Offended: turns half its back on the other one, chin up ("Pues vuelve con ella"); turns back on the next beat.
    "turn_away":       dict(body_y=0.0,   body_z=0.0,   body_x=-2,  body_yaw=110, body_sz=1.0,  head_dx=-8),
    # The novato's hands do these (rigs/arms.py); the body only leans in and looks down at them.
    "close_laptop":    dict(body_y=-0.02, body_z=0.0,   body_x=4,   body_yaw=0,   body_sz=1.0,  head_dx=12),
    "phone_down":      dict(body_y=0.0,   body_z=0.0,   body_x=3,   body_yaw=0,   body_sz=1.0,  head_dx=14),
    "phone_lower":     dict(body_y=0.0,   body_z=0.0,   body_x=2,   body_yaw=0,   body_sz=1.0,  head_dx=18),
    # Stretching at 3 a.m.: arms up (rigs/arms.py, or the stubby arms), chest up, head back.
    "stretch":         dict(body_y=0.0,   body_z=0.03,  body_x=-4,  body_yaw=0,   body_sz=1.04, head_dx=-12),
}

MOUTHS = ("mouth_rest", "mouth_M", "mouth_E", "mouth_A", "mouth_O", "mouth_smile")
SMILING = {"aliviado"}  # emotions that close the resting mouth into a smile (rigs that have mouth_smile)

# Stubby arms (small AIs): (forward deg, outward deg) for the left and right arm.
# They stay tucked most of the time; each gesture counts because it is rare.
ARM_POSES = {
    "rest": ((0, 4), (0, 4)),
    "wait": ((0, 6), (-25, 80)),  # "un momento": one arm up while making a point
    "shrug": ((-10, 55), (-10, 55)),
    "alarm": ((-20, 115), (-20, 115)),
    "droop": ((4, -4), (4, -4)),
    "soft": ((-8, 16), (-8, 16)),
    # At the laptop (beat.ai_move): typing into its memory, then one hand left on the keys.
    # Solved in Blender for the set's "laptop" slot: the right arm's tip lands on the keyboard.
    "type": ((-10, 22), (-24, 9)),
    "keys": ((0, 6), (-24, 9)),
    "stretch": ((-6, 150), (-6, 150)),
}
# Rubber-hose reach: at the laptop the stubby arm stretches to the keyboard (length factor, left/right).
ARM_STRETCH = {"type": (1.0, 2.3), "keys": (1.0, 2.3)}
TYPE_RATE = 23.0  # rad/s of the little alternating keystrokes

# Writing with its mind (MemorySave): the thinking light flashes on every character, the AI turns
# a little towards the laptop and lifts its lid in concentration. Mirrors the typing clock in Remotion.
TYPE_SPEED, TYPE_START = 0.055, 0.3
WRITE_TURN = -16.0  # deg of extra yaw towards the laptop
WRITE_LID = 0.035  # m: the lid lifts and the lit slit shows
LID_RATTLE = 0.012  # m: the lid jumps on every character, like a simmering pot ("se le va la olla")
AFTERGLOW = 2.6  # s: the light dies down slowly after the last character
WRITE_ARMS = 60.0  # deg: the stubby arms lift and "type in the air" to the same rhythm
LID_LAND = 0.45  # s after the last character: the lid drops back
PROUD = 1.4  # s of content squint after finishing


def _write_ticks(beats: list[dict], fps: int) -> list[float]:
    """Times (s) at which a non-space character appears on the laptop."""
    out = []
    for b in beats:
        if not _typing_beat(b):
            continue
        props = b["event"]["props"]
        text = "".join(props.get("lines", []))
        chunk = text[props.get("from_char", 0): props.get("to_char") if props.get("to_char") is not None else len(text)]
        # Read aloud while written: the timeline paces the typing to the voice (type_start/type_speed).
        t0 = b["start_frame"] / fps + props.get("type_start", TYPE_START)
        speed = props.get("type_speed", TYPE_SPEED)
        out += [t0 + i * speed for i, ch in enumerate(chunk) if ch != " "]
    return out


def _writing(t: float, ticks: list[float]) -> tuple[float, float, float]:
    """(engaged 0..1, flash 0..1, afterglow 0..1) at time t."""
    if not ticks:
        return 0.0, 0.0, 0.0
    # Engaged while ticks keep coming (gaps under 3 s are one writing session).
    engaged = 0.0
    for a in ticks:
        if a - 0.4 <= t <= a + 0.5:
            engaged = 1.0
            break
    near = [a for a in ticks if a <= t]
    flash = math.exp(-(t - near[-1]) / 0.035) if near else 0.0
    glow = math.exp(-(t - ticks[-1]) / AFTERGLOW) if t > ticks[-1] else 0.0
    return engaged, flash, glow


def _session_ends(ticks: list[float]) -> list[float]:
    """Last character of each writing session (ticks closer than 1 s belong together)."""
    return [a for a, b in zip(ticks, ticks[1:] + [math.inf]) if b - a > 1.0]


def _typing_beat(beat: dict) -> bool:
    ev = beat.get("event") or {}
    if ev.get("component") != "MemorySave":
        return False
    props = ev.get("props", {})
    total = sum(len(line) for line in props.get("lines", []))
    stop = props.get("to_char") if props.get("to_char") is not None else total
    return stop > props.get("from_char", 0)


# The lid (ceramic Claude): (lift m, tilt fwd deg, tilt side deg). "Se le va la olla" in alarm.
LID_POSES = {
    "neutral": (0.0, 0, 0),
    "orgulloso": (0.008, -3, 0),
    "confuso": (0.006, 0, -9),
    "juzgando": (0.004, 0, 7),
    "alarma": (0.1, -10, 5),
    "panico": (0.13, -12, -8),
    "hundido": (-0.016, 2, 0),  # closes the slit: the light goes out
    "aliviado": (0.01, 0, 2),
}


def _arm_pose(beat: dict, char_id: str, offscreen: frozenset) -> str:
    emotion, action, actor = _role(beat, char_id, offscreen)
    if emotion in ("alarma", "panico"):
        return "alarm"
    if emotion == "hundido":
        return "droop"
    if actor and action == "shrug":
        return "shrug"
    if actor and action == "stretch":
        return "stretch"
    if actor and beat["speaker"] == char_id and action in ("talk_gesture", "lean_in") and emotion in ("juzgando", "neutral"):
        return "wait"
    if emotion == "aliviado":
        return "soft"
    return "rest"


def _role(beat: dict, char_id: str, offscreen: frozenset = frozenset()) -> tuple[str, str, bool]:
    """(emotion, action, is_actor) for this character in this beat.

    Silent beats and lines spoken off-screen (a voice on the phone) are acted by the
    reactor, the novato by default.
    """
    speaker = beat["speaker"] if beat["speaker"] not in offscreen else None
    actor = speaker == char_id or (speaker is None and (beat.get("reactor") or "novato") == char_id)
    if actor:
        return beat["emotion"], beat["action"], True
    return beat["listener_emotion"], "idle", False


def _target(beat: dict, char_id: str, offscreen: frozenset = frozenset(), overrides: dict | None = None) -> dict:
    emotion, action, _ = _role(beat, char_id, offscreen)
    face = {**EMOTIONS.get(emotion, EMOTIONS["neutral"]), **(overrides or {}).get(emotion, {})}
    return {**face, **ACTIONS.get(action, ACTIONS["idle"])}


# Eyelid curves: a normal blink, and Claude's long slow blink (its signature "sigh").
BLINKS = {
    "normal": ((0.55, 0.1, 0.1, 0.55), (2.6, 4.4)),
    "slow": ((0.8, 0.5, 0.2, 0.06, 0.06, 0.06, 0.06, 0.2, 0.45, 0.7, 0.88), (3.5, 6.0)),
}


def _blink_frames(char_id: str, total: int, fps: int, style: str = "normal") -> dict[int, float]:
    curve, (lo, hi) = BLINKS.get(style, BLINKS["normal"])
    rng = random.Random(zlib.crc32(char_id.encode()))
    out, f = {}, int(fps * rng.uniform(0.8, 2.0))
    while f < total:
        for i, v in enumerate(curve):
            out[f + i] = v
        f += int(fps * rng.uniform(lo, hi))
    return out


def _think_level(beat: dict, char_id: str, t: float, offscreen: frozenset) -> float:
    """Thinking light: steady while talking, slow pulse while listening/thinking, bright when worried, dim when sad."""
    emotion, _, actor = _role(beat, char_id, offscreen)
    if emotion in ("alarma", "panico"):
        return 0.75 + 0.25 * math.sin(t * 6.0)
    if emotion == "hundido":
        return 0.08 + 0.04 * math.sin(t * 1.2)
    if beat["speaker"] == char_id:
        return 0.35
    return 0.3 + 0.18 * math.sin(t * 2.2)


# --- Acting that reads as alive (gaze, emphasis, reaction timing) ---------------------------------
# Eyes lead and the head follows: the pupils jump to a target in a couple of frames (saccade) and the
# head turns part of the way there, later and slower. Angles in degrees, relative to the face (-Y).
EYE_RANGE = {"novato": (0.016, 0.012), "default": (0.007, 0.006)}  # m of eye travel at full yaw / pitch
EYE_MAX = (30.0, 20.0)  # deg of gaze the eyes carry before saturating
HEAD_SHARE = (0.4, 0.3)  # part of the gaze yaw / pitch the head takes
HEAD_SHARE_AWAY = (0.8, 0.3)  # novato_away: the head turns to the door, or a close-up reads as talking to camera
HEAD_MAX = (28.0, 12.0)
EYE_TAU, HEAD_TAU = 0.03, 0.22  # s: saccade vs head follow
LISTEN_DELAY = 0.22  # s: the listener's face reacts a moment after the cut, not on it
AVERT = 0.45  # s: a speaker who is thinking looks away at the start of a line, then back
GAZE_BLINK = 14.0  # deg: big gaze shifts carry a blink (people blink when they move their eyes far)


def _gaze_target(beat: dict, char_id: str, off: frozenset, dirs: dict, t_beat: float) -> tuple[float, float]:
    """(yaw, pitch) this character wants to look at, before micro-saccades and smoothing."""
    emotion, action, actor = _role(beat, char_id, off)
    speaker = beat["speaker"] if beat["speaker"] not in off else None
    if beat.get("away") and "_door" in dirs and "novato" in dirs:
        # He is out of the room (beat.novato_away): whoever looks at him looks at where his voice comes from.
        dirs = {**dirs, "novato": dirs["_door"], "_other": dirs["_door"] if dirs.get("_other") == dirs["novato"] else dirs.get("_other")}
    other = dirs.get(speaker) if speaker and speaker != char_id else dirs.get("_other")
    other = other or (0.0, 0.0)
    if beat.get("gaze") and beat["gaze"] in dirs:  # directed by the script: look at someone / something
        return dirs[beat["gaze"]]
    if actor and (emotion == "hundido" or action in ("slump", "facepalm")):
        return other[0] * 0.25, -28.0  # eyes drop
    if actor and action == "look_phone":
        return 0.0, -32.0
    if actor and action == "phone_lower":
        return 0.0, -38.0  # eyes stay on the lowered phone
    if char_id == "novato" and beat["camera"] == "screen_closeup" and dirs.get("_screen"):
        return dirs["_screen"]
    if beat["speaker"] == char_id and char_id == "novato":
        audio = beat.get("audio") or {}
        dur = audio.get("duration", 0.0)
        start = audio.get("offset", 0.0)
        # Gaze aversion: before a line that costs something, eyes go to the side opposite the listener.
        if dur > 1.0 and start <= t_beat < start + min(AVERT, dur * 0.35) and emotion not in ("panico", "alarma"):
            return -math.copysign(20.0, other[0] or 1.0), 6.0
    return other


def _gaze_curves(char_id: str, beats: list[dict], beat_of: list[int], fps: int, total: int, off: frozenset,
                 dirs: dict, seed_id: str | None = None) -> tuple[list[tuple[float, float]], list[tuple[float, float]], list[int]]:
    """Per frame: eye gaze (yaw, pitch), head share (yaw, pitch) and frames where a big shift happens."""
    rng = random.Random(zlib.crc32(b"gaze" + (seed_id or char_id).encode()))
    jitter, next_jump = (0.0, 0.0), 0
    eye, head = None, (0.0, 0.0)
    a_eye = 1 - math.exp(-1.0 / (EYE_TAU * fps))
    a_head = 1 - math.exp(-1.0 / (HEAD_TAU * fps))
    eyes_out, head_out, shifts = [], [], []
    last_target = None
    for f in range(total):
        b = beats[beat_of[f]]
        t_beat = (f - b["start_frame"]) / fps
        _, _, actor = _role(b, char_id, off)
        # The listener keeps looking where it was for a beat: it reacts, it isn't cut.
        src = b
        if not actor and beat_of[f] > 0 and t_beat < LISTEN_DELAY:
            src = beats[beat_of[f] - 1]
        target = _gaze_target(src, char_id, off, dirs, (f - src["start_frame"]) / fps)
        if f >= next_jump:  # micro-saccades: tiny refixations every 0.5-1.5 s
            jitter = (rng.uniform(-3.0, 3.0), rng.uniform(-2.0, 2.0))
            next_jump = f + int(fps * rng.uniform(0.5, 1.5))
        if last_target is not None and math.dist(target, last_target) > GAZE_BLINK:
            shifts.append(f)
        last_target = target
        goal = (target[0] + jitter[0], target[1] + jitter[1])
        eye = goal if eye is None else (eye[0] + (goal[0] - eye[0]) * a_eye, eye[1] + (goal[1] - eye[1]) * a_eye)
        share = HEAD_SHARE_AWAY if src.get("away") and not src.get("gaze") else HEAD_SHARE
        want = (max(-HEAD_MAX[0], min(HEAD_MAX[0], target[0] * share[0])),
                max(-HEAD_MAX[1], min(HEAD_MAX[1], target[1] * share[1])))
        head = want if f == 0 else (head[0] + (want[0] - head[0]) * a_head, head[1] + (want[1] - head[1]) * a_head)
        eyes_out.append(eye)
        head_out.append(head)
    return eyes_out, head_out, shifts


def _direction(to_local, origin: Vector, world: Vector) -> tuple[float, float]:
    """(yaw, pitch) in degrees from origin (body-local) to a world point; the face looks down -Y."""
    v = to_local @ world - origin
    yaw = math.degrees(math.atan2(v.x, -v.y))
    pitch = math.degrees(math.atan2(v.z, math.hypot(v.x, v.y)))
    return yaw, pitch


def _envelope(episode_dir: str | None, beats: list[dict], char_id: str, fps: int, total: int, own: bool = True) -> list[float]:
    """Loudness per frame (0..1, per line) of this character's voice (own) or of everyone else's (what it hears)."""
    import wave
    from array import array
    from pathlib import Path

    env = [0.0] * total
    if not episode_dir:
        return env
    for b in beats:
        audio = b.get("audio")
        if not audio or (b["speaker"] != char_id if own else b["speaker"] in (char_id, None)):
            continue
        path = Path(episode_dir) / Path(audio["file"]).with_suffix(".wav")
        if not path.exists():
            continue
        with wave.open(str(path)) as w:
            if w.getsampwidth() != 2:
                continue
            sr, ch = w.getframerate(), w.getnchannels()
            samples = array("h", w.readframes(w.getnframes()))[::ch]
        hop = sr / fps
        rms = []
        for k in range(int(len(samples) / hop)):
            seg = samples[int(k * hop): int((k + 1) * hop)]
            rms.append(math.sqrt(sum(s * s for s in seg) / max(1, len(seg))))
        peak = sorted(rms)[int(len(rms) * 0.95)] if rms else 1.0
        start = b["start_frame"] + int(round(audio["offset"] * fps))
        for k, r in enumerate(rms):
            if 0 <= start + k < total:
                env[start + k] = min(1.0, r / max(peak, 1.0))
    return env


def _emphasis(env: list[float], fps: int, spacing: float = 0.35) -> list[float]:
    """Smooth accents on the stressed syllables (0..1), not the raw loudness.

    Following loudness frame by frame made heads vibrate (it rises and falls 6-8 times a second).
    Instead: find the clear peaks (at most one every `spacing` s) and give each a rounded ~0.3 s bump.
    """
    a_fast = 1 - math.exp(-1.0 / (0.04 * fps))
    a_slow = 1 - math.exp(-1.0 / (0.35 * fps))
    fast = slow = 0.0
    rise = []
    for v in env:
        fast += (v - fast) * a_fast
        slow += (v - slow) * a_slow
        rise.append(max(0.0, fast - slow))
    gap, half = int(spacing * fps), max(2, int(0.15 * fps))
    peaks, last = [], -gap
    for f in range(1, len(rise) - 1):
        if rise[f] > 0.12 and rise[f] >= rise[f - 1] and rise[f] >= rise[f + 1] and f - last >= gap:
            peaks.append((f, min(1.0, rise[f] / 0.35)))
            last = f
    out = [0.0] * len(env)
    for f, h in peaks:
        for d in range(-half, half + 1):
            if 0 <= f + d < len(out):
                out[f + d] = max(out[f + d], h * 0.5 * (1 + math.cos(math.pi * d / half)))
    return out


# Pose changes land like a body, not a slider: a damped spring that overshoots a little and settles,
# and the big moves wind up first (a small move the other way). Energy depends on the moment.
SPRING_TAU, SPRING_W = 3.0, 0.5  # frames, rad/frame: ~12 % overshoot at frame ~6
WIND_UP = {"recoil": 0.3, "lean_in": 0.25, "slump": 0.15, "facepalm": 0.25, "shrug": 0.2}
HEAR_LAG = 4  # frames between hearing a stressed word and the little nod


def _spring(fr: float, tau: float = SPRING_TAU, w: float = SPRING_W) -> float:
    if fr <= 0:
        return 0.0
    return 1 - math.exp(-fr / tau) * math.cos(w * fr)


# beat.ai_flourish: a cute beat as the AI lands its line (only rigs with a lid: the AIs).
FLOURISH = {"hop": 0.38, "giggle": 0.75}  # seconds
FLOURISH_LEAD = 0.3  # starts this long before the line ends, so the cut doesn't swallow it


def _flourish(beat: dict, char_id: str, t_beat: float) -> tuple[str | None, float]:
    """(kind, 0..1 progress) of the flourish at this moment, or (None, 0)."""
    kind = beat.get("ai_flourish")
    if not kind or beat["speaker"] != char_id:
        return None, 0.0
    audio = beat.get("audio") or {}
    at = audio.get("offset", 0.0) + audio.get("duration", 0.0) - FLOURISH_LEAD
    x = (t_beat - at) / FLOURISH[kind]
    return (kind, x) if 0.0 <= x <= 1.0 else (None, 0.0)


POWER_OFF = 1.6  # s: eyes close, light dies, the jar sags
POWER_ON = 1.0  # s: the light flickers back, eyes open


def _power(beats: list[dict], fps: int, total: int) -> list[float]:
    """Per frame: 1 = on, 0 = shut down (beat.ai_power)."""
    events = sorted((b["start_frame"] / fps + b.get("ai_power_at", 0.0), b["ai_power"]) for b in beats if b.get("ai_power"))
    out = []
    for f in range(total):
        t, level = f / fps, 1.0
        for at, kind in events:
            if t < at:
                break
            x = (t - at) / (POWER_OFF if kind == "off" else POWER_ON)
            if kind == "off":
                # A last flicker, then it fades out.
                level = 0.0 if x >= 1 else (1 - smoothstep(x)) * (0.6 if 0.12 < x < 0.2 else 1.0)
            else:
                level = 1.0 if x >= 1 else smoothstep(x) * (0.2 if 0.15 < x < 0.3 or 0.45 < x < 0.5 else 1.0)
        out.append(level)
    return out


TEAR_ROLL = 2.6  # s for the single tear to roll down the cheek


def _tears(char_id: str, root, beats: list[dict], fps: int, total: int) -> None:
    """beat.tears on the novato: "wet" shows glossy eyes; "tear" also rolls one drop down the cheek at tear_at."""
    tear = find(root, "tear")
    # Any human rig has the tear (the novato, the girl): only this character's beats count (silent beats: the reactor).
    mine = [b for b in beats if b.get("tears") and (b["speaker"] == char_id or (b["speaker"] is None and (b.get("reactor") or "novato") == char_id))]
    if tear is None or not mine:
        return
    frames = list(range(total))
    wet = [0.0] * total
    for b in mine:
        for f in range(b["start_frame"], min(total, b["end_frame"])):
            wet[f] = 1.0
    for name in ("eye_wet_L", "eye_wet_R", "eye_waterline_L", "eye_waterline_R"):
        obj = find(root, name)
        if obj:
            bake(obj, "hide_render", -1, frames, [1.0 - w for w in wet], interp="CONSTANT")
    start = tear.location.copy()
    path = [start, start + Vector((0.002, 0.003, -0.04)), start + Vector((-0.002, 0.008, -0.085))]
    loc, scale, hidden = [], [], []
    rolls = [b["start_frame"] / fps + b.get("tear_at", 0.8) for b in mine if b.get("tears") == "tear"]
    for f in frames:
        t = f / fps
        last = max((r for r in rolls if t >= r), default=None)
        x = -1.0 if last is None else (t - last) / TEAR_ROLL
        if x < 0 or x > 1:
            loc.append(start)
            scale.append(0.0)
            hidden.append(1.0)
            continue
        # Wells up (grows in place), then slides down slowly, thinning out at the end.
        grow = smoothstep(x / 0.25)
        k = smoothstep((x - 0.2) / 0.8) if x > 0.2 else 0.0
        p = path[0].lerp(path[1], min(1.0, k * 2)) if k < 0.5 else path[1].lerp(path[2], (k - 0.5) * 2)
        loc.append(p)
        scale.append(grow * (1.0 - 0.45 * smoothstep((x - 0.7) / 0.3)))
        hidden.append(0.0)
    for c in range(3):
        bake(tear, "location", c, frames, [v[c] for v in loc])
    rest = tuple(tear.scale)
    for c in range(3):
        bake(tear, "scale", c, frames, [rest[c] * s for s in scale])
    bake(tear, "hide_render", -1, frames, hidden, interp="CONSTANT")


# --- Objects with a face (rigs/thing.py) -------------------------------------------------------------------------
# Eyelids: a lid shell per eye (eyelid_L/R) closes over a still eyeball instead of squashing it. Openness 1 = the
# neutral look (a little lid shows), 0 = shut; above 1 the lid hides completely (alarm).
LID_REST = 0.86
# The lamp's light (lamp_bulb + its lights) acts too: brighter when proud or startled, dim when sad.
LAMP_LEVELS = {"neutral": 1.0, "orgulloso": 1.15, "confuso": 0.92, "alarma": 1.35, "juzgando": 0.85,
               "hundido": 0.32, "panico": 1.4, "aliviado": 1.1}
ACT_CHANNELS = ("rx", "ry", "rz", "x", "y", "z", "s")


def lid_angle(openness: float) -> float:
    """Rotation (rad, about the eye's X) of an upper-lid hemisphere whose edge leaves `openness` of the eye visible."""
    frac = max(0.0, min(1.0, openness * LID_REST))
    return -math.asin(2 * frac - 1)


def _act_pose(poses: dict, beat: dict, char_id: str, off: frozenset) -> dict:
    """Channel offsets of an acting part (a lamp's arm, a lid, laces) in this beat: its emotion's pose plus, for the
    actor, its action's pose."""
    emotion, action, actor = _role(beat, char_id, off)
    out = {c: 0.0 for c in ACT_CHANNELS}
    for key in ("base", emotion, action if actor else None):  # "base": always on (e.g. steam hidden at rest)
        for c, v in (poses.get(key) or {}).items():
            if c in out:
                out[c] += v
    return out


def _acting_parts(root, char_id: str, beats: list[dict], beat_of: list[int], fps: int, total: int, off: frozenset,
                  talking: list[bool]) -> None:
    """Bake every object that carries `act_poses` (a JSON dict set by its builder): emotion/action poses with a
    springy pop into alarm and a soft settle otherwise, plus a chatter while the character talks."""
    import json

    frames = list(range(total))
    for obj in [root, *root.children_recursive]:
        if "act_poses" not in obj.keys():
            continue
        poses = json.loads(obj["act_poses"])
        loc0, rot0, s0 = tuple(obj.location), tuple(obj.rotation_euler), tuple(obj.scale)
        talk = poses.get("talk") or {}
        vals = {c: [] for c in ACT_CHANNELS}
        for f in frames:
            i = beat_of[f]
            b = beats[i]
            cur = _act_pose(poses, b, char_id, off)
            prev = _act_pose(poses, beats[i - 1], char_id, off) if i > 0 else cur
            fr = f - b["start_frame"]
            emo, emo_prev = _role(b, char_id, off)[0], (_role(beats[i - 1], char_id, off)[0] if i > 0 else None)
            if emo in ("alarma", "panico") and emo_prev != emo:
                k = 1 - math.exp(-fr / 2.5) * math.cos(fr * 0.45)
            elif emo == "hundido":
                k = smoothstep(fr / 18)  # sadness sinks slowly
            else:
                k = smoothstep(fr / 9)
            t = f / fps
            chatter = abs(math.sin(t * 9.0)) if talking[f] else 0.0
            for c in ACT_CHANNELS:
                vals[c].append(prev[c] + (cur[c] - prev[c]) * k + talk.get(c, 0.0) * chatter)
        for n, c in enumerate(("rx", "ry", "rz")):
            if any(vals[c]):
                bake(obj, "rotation_euler", n, frames, [rot0[n] + rad(v) for v in vals[c]])
        for n, c in enumerate(("x", "y", "z")):
            if any(vals[c]):
                bake(obj, "location", n, frames, [loc0[n] + v for v in vals[c]])
        if any(vals["s"]):
            for n in range(3):
                bake(obj, "scale", n, frames, [s0[n] * (1 + v) for v in vals["s"]])


def _lamp(root, char_id: str, beats: list[dict], beat_of: list[int], fps: int, total: int, off: frozenset,
          power: list[float]) -> None:
    """A lamp's light follows its mood and its switch (beat.ai_power): bulb glow (object colour R) and light energy."""
    bulb = find(root, "lamp_bulb")
    if bulb is None:
        return
    frames = list(range(total))
    levels = []
    for f in frames:
        i = beat_of[f]
        b = beats[i]
        emo = _role(b, char_id, off)[0]
        cur = LAMP_LEVELS.get(emo, 1.0)
        prev = LAMP_LEVELS.get(_role(beats[i - 1], char_id, off)[0], 1.0) if i > 0 else cur
        fr = f - b["start_frame"]
        level = lerp(prev, cur, smoothstep(fr / (20 if emo == "hundido" else 8)))
        if emo in ("alarma", "panico") and fr in (2, 3, 7):
            level *= 0.55  # a startled flicker
        levels.append(level * power[f])
    bake(bulb, "color", 0, frames, levels)
    for obj in [root, *root.children_recursive]:
        if obj.type == "LIGHT" and obj.name.split(".")[0].startswith("lamp_"):
            base = obj.data.energy
            bake(obj.data, "energy", -1, frames, [base * v for v in levels])


def animate(char_id: str, root, timeline: dict, heads: dict | None = None, screen: Vector | None = None,
            seed_id: str | None = None) -> None:
    """heads: world head positions of everyone in the scene (gaze targets); screen: the laptop screen.

    seed_id: copies of the same character (blender/copies.py) blink and sway each on their own.
    """
    sid = seed_id or char_id
    fps, total = timeline["fps"], timeline["total_frames"]
    beats = timeline["beats"]
    off = frozenset(timeline.get("offscreen", []))
    body = find(root, "ctrl_body") or root
    head = find(root, "ctrl_head")
    eyes = [find(root, "eye_L"), find(root, "eye_R")]
    lids = [find(root, "eyelid_L"), find(root, "eyelid_R")]
    brows = [find(root, "brow_L"), find(root, "brow_R")]
    # Builders of rigid things (rigs/thing.py) damp the head and body moves: a lamp's base stays on the desk.
    head_gain = head.get("gain", 1.0) if head else 1.0
    body_gain = body.get("gain", 1.0)
    mouths = {m: find(root, m) for m in MOUTHS}

    rest = {
        "body_loc": tuple(body.location),
        "body_rot": tuple(body.rotation_euler),
        "body_scale": tuple(body.scale),
        "head_rot": tuple(head.rotation_euler) if head else None,
        "eye_scale": [tuple(e.scale) for e in eyes],
        "eye_loc": [tuple(e.location) if e else None for e in eyes],
        "brow_loc": [tuple(b.location) for b in brows],
        "brow_rot": [tuple(b.rotation_euler) for b in brows],
    }
    meta = character_meta(char_id)
    overrides = meta.get("emotion_overrides", {})
    if "emotion_defaults" in root.keys():  # a builder's own starting point (rigs/thing.py), under the character's
        import json

        base = json.loads(root["emotion_defaults"])
        overrides = {e: {**base.get(e, {}), **overrides.get(e, {})} for e in set(base) | set(overrides)}
    blinks = _blink_frames(sid, total, fps, meta.get("blink", "normal"))

    beat_of = []
    for i, b in enumerate(beats):
        beat_of += [i] * (b["end_frame"] - b["start_frame"])
    beat_of += [len(beats) - 1] * (total - len(beat_of))

    # Gaze: directions (in this body's frame) to every other head and to the laptop screen.
    dirs: dict = {}
    if heads and head:
        to_local = body.matrix_world.inverted()
        origin = to_local @ head.matrix_world.translation
        others = [c for c in heads if c != char_id and c not in off]
        for c in others:
            dirs[c] = _direction(to_local, origin, heads[c])
        if others:  # who to look at when nobody (else) is talking: the AI for the novato, the novato for the rest
            main = "novato" if "novato" in others else next((c for c in others if c != "novato"), others[0])
            dirs["_other"] = dirs[main]
        if screen is not None:
            dirs["_screen"] = _direction(to_local, origin, screen)
        for name, point in (timeline.get("_gaze_points") or {}).items():  # set points (e.g. her light)
            dirs[name] = _direction(to_local, origin, Vector(point))
    gaze_eye, gaze_head, shifts = _gaze_curves(char_id, beats, beat_of, fps, total, off, dirs, sid)
    curve = BLINKS.get(meta.get("blink", "normal"), BLINKS["normal"])[0]
    for s in shifts:  # a blink rides along with a big eye movement, unless one is already near
        if not any(g in blinks for g in range(s - 8, s + 8)):
            for j, v in enumerate(curve[:4]):
                blinks[s + j] = v
    # Camera cuts at a beat start: cut on the change, not into it. The face is already set on the first frame of the
    # new shot and no blink lands in it (a half-shut eye on a cut reads as a glitch).
    cuts = {b["start_frame"] for i, b in enumerate(beats) if i > 0
            and b["camera"] != (beats[i - 1].get("cut_camera") or beats[i - 1]["camera"])}
    for c in cuts:
        for g in range(c, c + CUT_CLEAN):
            if g in blinks:  # drop the whole blink, not just its frames inside the window
                a = z = g
                while a - 1 in blinks:
                    a -= 1
                while z + 1 in blinks:
                    z += 1
                for h in range(a, z + 1):
                    blinks.pop(h)
    ex, ez = EYE_RANGE.get(char_id, EYE_RANGE["default"])
    if eyes[0] is not None and "gaze_range" in eyes[0].keys():  # pupils in a big eyeball travel further
        ex, ez = eyes[0]["gaze_range"]
    env = _envelope(timeline.get("_episode_dir"), beats, char_id, fps, total)
    emph = _emphasis(env, fps)
    # What it hears: the listener nods along to the other's stressed words, a few frames late.
    heard = _emphasis(_envelope(timeline.get("_episode_dir"), beats, char_id, fps, total, own=False), fps, spacing=0.6)
    heard = [0.0] * HEAR_LAG + heard[:-HEAR_LAG]
    phase = (zlib.crc32(sid.encode()) % 628) / 100.0
    _tears(char_id, root, beats, fps, total)
    # Only the AI powers down; humans ignore beat.ai_power.
    power = _power(beats, fps, total) if find(root, "think_light") or find(root, "lamp_bulb") else [1.0] * total
    think = find(root, "think_light")
    think_glow = find(root, "think_glow")
    think_vals: list[float] = []
    # Small AIs only: the novato's arms are solved by rigs/arms.py.
    stub_arms = [find(root, "ctrl_arm_L"), find(root, "ctrl_arm_R")] if not find(root, "ctrl_forearm_L") else [None, None]
    arm_vals: dict[str, list[float]] = {k: [] for k in ("l0", "l1", "r0", "r1", "ls", "rs")}
    lid = find(root, "lid")
    lid_rest = tuple(lid.location) if lid else None
    lid_vals: dict[str, list[float]] = {k: [] for k in ("z", "rx", "ry")}
    frames = list(range(total))
    ch: dict[str, list[float]] = {}

    def put(key: str, value: float) -> None:
        ch.setdefault(key, []).append(value)

    # The AI types into its memory only while it stands at the laptop (staging.plan intervals).
    laptop_spans = timeline.get("ai_at_laptop") or []
    ticks = _write_ticks(beats, fps) if think else []
    ends = _session_ends(ticks)
    glow_extra: list[float] = []  # extra spill from the think light onto the desk while writing
    engaged_s = 0.0  # smoothed engagement (turn + lid ease in and out)
    visible_mouth: list[str] = []
    talking_at: list[bool] = []
    for f in frames:
        i = beat_of[f]
        b = beats[i]
        cur = _target(b, char_id, off, overrides)
        prev = _target(beats[i - 1], char_id, off, overrides) if i > 0 else cur
        t_beat = (f - b["start_frame"]) / fps
        t = f / fps
        _, action, actor = _role(b, char_id, off)
        fr = f - b["start_frame"]
        calm = _role(b, char_id, off)[0] in ("hundido",) or timeline.get("tone") == "agridulce"
        if actor and not calm:
            k = _spring(fr)
            wind = WIND_UP.get(action, 0.0)
            if wind and fr < 5:  # wind-up: a little the other way before the move
                k -= wind * math.sin(math.pi * fr / 5)
        elif actor:  # sadness doesn't bounce
            k = smoothstep(fr / (TRANSITION * 2))
        else:  # the listener takes in what it heard, then the face changes (a moment late, still alive)
            k = _spring(fr - LISTEN_DELAY * fps, tau=4.0, w=0.4) if not calm else smoothstep((fr - LISTEN_DELAY * fps) / (TRANSITION * 2))
        if b["start_frame"] in cuts and action == "idle":
            k = 1.0
        p = {key: lerp(prev[key], cur[key], k) for key in cur}
        fl_kind, fl_x = _flourish(b, char_id, t_beat) if lid else (None, 0.0)
        hop = 0.04 * math.sin(math.pi * fl_x) if fl_kind == "hop" else 0.0
        giggle = math.sin(math.pi * fl_x) if fl_kind == "giggle" else 0.0

        # Talking: active while this character's audio plays.
        talking, mouth = False, "mouth_rest"
        audio = b.get("audio")
        if audio and b["speaker"] == char_id and power[f] > 0.5:
            ta = t_beat - audio["offset"]
            if 0 <= ta <= audio["duration"]:
                talking = True
                for cue in audio["visemes"]:
                    if cue["start"] <= ta < cue["end"]:
                        mouth = cue["viseme"]
                        break
        if not talking and mouths.get("mouth_smile") and _role(b, char_id, off)[0] in SMILING and k > 0.5:
            mouth = "mouth_smile"
        visible_mouth.append(mouth)
        talking_at.append(talking)
        eng, flash, after = _writing(t, ticks)
        engaged_s += (eng - engaged_s) * (1 - math.exp(-1.0 / (0.25 * fps)))
        since = min((t - e for e in ends if t >= e), default=math.inf)
        landed = since - LID_LAND
        proud = smoothstep(landed / 0.2) * (1 - smoothstep((landed - PROUD) / 0.4)) if 0 <= landed else 0.0
        if stub_arms[0]:
            def pose_of(j: int) -> str:
                if any(a <= beats[j]["start_frame"] and beats[j]["end_frame"] <= z for a, z in laptop_spans):
                    return "type" if _typing_beat(beats[j]) else "keys"
                return _arm_pose(beats[j], char_id, off)

            a_cur = ARM_POSES[pose_of(i)]
            a_prev = ARM_POSES[pose_of(i - 1)] if i > 0 else a_cur
            ka = smoothstep((f - b["start_frame"]) / (4 if a_cur is ARM_POSES["alarm"] else 10))
            sway = 2.0 * math.sin(t * 1.7)
            (lf, lo), (rf, ro) = [tuple(lerp(pa, ca, ka)) for pa, ca in zip(a_prev, a_cur)]
            def stretch_of(j: int) -> tuple[float, float]:
                st = ARM_STRETCH.get(pose_of(j), 1.0) if j >= 0 else 1.0
                return st if isinstance(st, tuple) else (st, st)

            s_cur, s_prev = stretch_of(i), stretch_of(i - 1) if i > 0 else stretch_of(i)
            arm_vals["ls"].append(lerp(s_prev[0], s_cur[0], ka))
            arm_vals["rs"].append(lerp(s_prev[1], s_cur[1], ka))
            if a_cur is ARM_POSES["type"]:
                lf += 6.0 * math.sin(t * TYPE_RATE * 0.5)
                rf += 7.0 * math.sin(t * TYPE_RATE) + 3.0 * math.sin(t * TYPE_RATE * 0.37)
            # Writing: arms up a little, tapping the air in turns.
            lo += engaged_s * WRITE_ARMS
            ro += engaged_s * WRITE_ARMS
            lf += engaged_s * (-20 + 22 * math.sin(t * 15.0))
            rf += engaged_s * (-20 + 22 * math.sin(t * 15.0 + math.pi))
            arm_vals["l0"].append(rad(lf))
            arm_vals["l1"].append(rad(-(lo + sway)))
            arm_vals["r0"].append(rad(rf))
            arm_vals["r1"].append(rad(ro + sway))
        if lid:
            emo_cur = _role(b, char_id, off)[0]
            emo_prev = _role(beats[i - 1], char_id, off)[0] if i > 0 else emo_cur
            pc, pp = LID_POSES.get(emo_cur, LID_POSES["neutral"]), LID_POSES.get(emo_prev, LID_POSES["neutral"])
            fr = f - b["start_frame"]
            if emo_cur in ("alarma", "panico") and emo_prev != emo_cur:
                # pops up fast, overshoots and settles (damped spring)
                k_lid = 1 - math.exp(-fr / 2.5) * math.cos(fr * 0.45)
            else:
                k_lid = smoothstep(fr / 8)
            lz, lx, ly = (pp[n] + (pc[n] - pp[n]) * k_lid for n in range(3))
            if talking:  # barely there: big lid moves are kept for emotions, so they mean something
                lz += 0.0007 * abs(math.sin(t * 9.0))
            # After the last character the lid drops; a tiny bounce as it lands (the clink).
            bounce = 0.006 * math.sin(math.pi * landed / 0.18) if 0 <= landed < 0.18 else 0.0
            # Giggle: the lid chatters like a pot about to boil; hop: it lags the jump and lands late.
            lz += giggle * 0.006 * abs(math.sin(t * 42.0)) + (0.012 * math.sin(math.pi * min(1.0, fl_x * 1.3)) if fl_kind == "hop" else 0.0)
            lid_vals["z"].append(lid_rest[2] + lz + engaged_s * (WRITE_LID + LID_RATTLE * flash) + bounce)
            lid_vals["rx"].append(rad(lx))
            lid_vals["ry"].append(rad(ly))
        if think:
            lvl = _think_level(b, char_id, t, off)
            if i > 0:
                lvl = lerp(_think_level(beats[i - 1], char_id, t, off), lvl, smoothstep((f - b["start_frame"]) / 12))
            # The light's control channel tops out at 1 (= 7x emission): leave headroom for every flash.
            lvl = min(1.0, lvl + engaged_s * (0.08 + 0.42 * flash) + 0.3 * after) * power[f]
            think_vals.append(lvl)
            glow_extra.append((engaged_s * (0.6 + 2.4 * flash) + 0.5 * after) * power[f])

        # Talking follows the voice: the body lifts with loudness, the head dips on stressed syllables.
        bob = 0.0  # the body no longer rides the loudness (it read as vibrating); the head marks the words
        breathe = 0.008 * math.sin(t * 2.1)
        shrug = 0.05 * math.sin(math.pi * min(1.0, t_beat / 0.5)) if actor and action == "shrug" else 0.0
        jitter = 0.0  # no shiver for fear: on screen it read as glitching; the face and the voice carry it

        off_k = 1.0 - power[f]
        if body_gain == 1.0:
            put("bl1", rest["body_loc"][1] + p["body_y"])
            put("bl2", rest["body_loc"][2] + p["body_z"] + (bob + shrug + hop) * power[f] - 0.025 * off_k)
            put("br0", rest["body_rot"][0] + rad(p["body_x"]))
        else:
            put("bl1", rest["body_loc"][1] + p["body_y"] * body_gain)
            put("bl2", rest["body_loc"][2] + (p["body_z"] + (bob + shrug + hop) * power[f] - 0.025 * off_k) * body_gain)
            put("br0", rest["body_rot"][0] + rad(p["body_x"]) * body_gain)
        put("br2", rest["body_rot"][2] + rad(p["body_yaw"] + WRITE_TURN * engaged_s))
        # Squash on take-off and landing, stretch in the air (classic hop).
        squash = 0.0
        if fl_kind == "hop":
            squash = -0.08 * math.sin(math.pi * fl_x / 0.2) if fl_x < 0.2 else (0.06 * math.sin(math.pi * (fl_x - 0.2) / 0.6) if fl_x < 0.8 else -0.06 * math.sin(math.pi * (fl_x - 0.8) / 0.2))
        if body_gain == 1.0:
            put("bs2", rest["body_scale"][2] * p["body_sz"] * (1 + breathe + squash))
        else:
            put("bs2", rest["body_scale"][2] * (1 + (p["body_sz"] * (1 + breathe + squash) - 1) * body_gain))
        if head:
            emo_now = _role(b, char_id, off)[0]
            nod = 5.0 * emph[f] if talking else 0.0
            if not talking and emo_now not in ("hundido", "alarma", "panico") and power[f] > 0.5:
                nod += 3.0 * heard[f]  # active listening
            # Never perfectly still: a slow drift, different per character.
            drift_x = 0.7 * math.sin(t * 0.83 + phase) + 0.35 * math.sin(t * 2.1 + 2 * phase)
            drift_y = 0.6 * math.sin(t * 0.61 + 3 * phase)
            gh = gaze_head[f]
            if head_gain == 1.0:
                put("hr0", rest["head_rot"][0] + rad(max(-14.0, min(20.0, p["head_x"] + p["head_dx"])) + nod + drift_x
                                                     - gh[1] + 14.0 * off_k))
                put("hr1", rest["head_rot"][1] + rad(p["head_y"] + jitter + drift_y))
                put("hr2", rest["head_rot"][2] + rad(gh[0]))
            else:
                put("hr0", rest["head_rot"][0] + head_gain * rad(max(-14.0, min(20.0, p["head_x"] + p["head_dx"])) + nod
                                                                 + drift_x - gh[1] + 14.0 * off_k))
                put("hr1", rest["head_rot"][1] + head_gain * rad(p["head_y"] + jitter + drift_y))
                put("hr2", rest["head_rot"][2] + head_gain * rad(gh[0]))

        blink = blinks.get(f, 1.0)
        for n, (eye, rs) in enumerate(zip(eyes, rest["eye_scale"])):
            if eye:
                pop = 1 + (0.06 * emph[f] if talking else 0.0)  # eyes widen a touch on stressed words
                put(f"e{n}x", rs[0] * p["eye_s"] * pop)
                eye_z = p["eye_z"] * (1 - 0.88 * engaged_s)  # eyes shut, concentrating
                eye_z = lerp(eye_z, 0.55, proud)  # content squint once it's done
                eye_z = lerp(eye_z, 0.45, giggle)  # laughing inside: happy squint
                if lids[n] is not None:  # the lid closes over the eye; the eye itself only widens
                    put(f"e{n}z", rs[2] * p["eye_s"] * pop)
                    put(f"l{n}", lid_angle(eye_z * blink * lerp(0.0, 1.0, power[f])))
                else:
                    put(f"e{n}z", rs[2] * p["eye_s"] * eye_z * blink * pop * lerp(0.05, 1.0, power[f]))
                # Where the eyes point: what the head doesn't cover, the pupils do.
                gy = max(-EYE_MAX[0], min(EYE_MAX[0], gaze_eye[f][0] - gaze_head[f][0]))
                gp = max(-EYE_MAX[1], min(EYE_MAX[1], gaze_eye[f][1] - gaze_head[f][1]))
                rl = rest["eye_loc"][n]
                put(f"e{n}lx", rl[0] + ex * gy / EYE_MAX[0])
                put(f"e{n}lz", rl[2] + ez * gp / EYE_MAX[1])
        for n, (brow, rl, rr) in enumerate(zip(brows, rest["brow_loc"], rest["brow_rot"])):
            if brow:
                sign = 1 if n == 0 else -1  # brow_L sits at +x; mirror the tilt for brow_R
                bz = lerp(p["brow_z"], -0.006, engaged_s) + 0.01 * proud + (0.008 * emph[f] if talking else 0.0)
                if talking and (b.get("line") or "").rstrip("…. ").endswith("?") and ta > 0.55 * audio["duration"]:
                    bz += 0.012 * smoothstep((ta - 0.55 * audio["duration"]) / 0.15)  # questions end with brows up
                tilt = lerp(p["brow_tilt"], -9.0, engaged_s)  # furrowed: inner ends down
                put(f"b{n}z", rl[2] + bz + (p["brow_asym"] if n == 0 else 0.0))
                put(f"b{n}r", rr[1] + sign * rad(tilt))

    bake(body, "location", 1, frames, ch["bl1"])
    bake(body, "location", 2, frames, ch["bl2"])
    bake(body, "rotation_euler", 0, frames, ch["br0"])
    bake(body, "rotation_euler", 2, frames, ch["br2"])
    bake(body, "scale", 2, frames, ch["bs2"])
    if head:
        bake(head, "rotation_euler", 0, frames, ch["hr0"])
        bake(head, "rotation_euler", 1, frames, ch["hr1"])
        bake(head, "rotation_euler", 2, frames, ch["hr2"])
    for n, eye in enumerate(eyes):
        if eye:
            bake(eye, "scale", 0, frames, ch[f"e{n}x"])
            bake(eye, "scale", 2, frames, ch[f"e{n}z"])
            bake(eye, "location", 0, frames, ch[f"e{n}lx"])
            bake(eye, "location", 2, frames, ch[f"e{n}lz"])
    for n, lid_obj in enumerate(lids):
        if lid_obj is not None and eyes[n] is not None:
            bake(lid_obj, "rotation_euler", 0, frames, ch[f"l{n}"])
    for n, brow in enumerate(brows):
        if brow:
            bake(brow, "location", 2, frames, ch[f"b{n}z"])
            bake(brow, "rotation_euler", 1, frames, ch[f"b{n}r"])

    if stub_arms[0]:
        for arm, key in zip(stub_arms, ("l", "r")):
            if arm:
                bake(arm, "rotation_euler", 0, frames, arm_vals[f"{key}0"])
                bake(arm, "rotation_euler", 1, frames, arm_vals[f"{key}1"])
                if any(v != 1.0 for v in arm_vals[f"{key}s"]):
                    bake(arm, "scale", 2, frames, arm_vals[f"{key}s"])
    if lid:
        bake(lid, "location", 2, frames, lid_vals["z"])
        bake(lid, "rotation_euler", 0, frames, lid_vals["rx"])
        bake(lid, "rotation_euler", 1, frames, lid_vals["ry"])
    if think:
        bake(think, "color", 0, frames, think_vals)
        if think_glow:
            bake(think_glow.data, "energy", -1, frames, [v * 0.8 + e for v, e in zip(think_vals, glow_extra)])

    _acting_parts(root, char_id, beats, beat_of, fps, total, off, talking_at)
    _lamp(root, char_id, beats, beat_of, fps, total, off, power)

    # Mouth swaps: keys only where visibility changes.
    for name, obj in mouths.items():
        if obj is None:
            continue
        keys_f, keys_v, last = [], [], None
        for f, m in zip(frames, visible_mouth):
            hidden = 0.0 if m == name else 1.0
            if hidden != last:
                keys_f.append(f)
                keys_v.append(hidden)
                last = hidden
        bake(obj, "hide_render", -1, keys_f, keys_v, interp="CONSTANT")
