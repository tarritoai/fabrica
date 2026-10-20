"""Musical episodes (episode.score): the score -> note events (the animation's timing) and the mix (the audio).

Both come from the same notes, so every sound lands on its frame by construction. Everything is synthesised here
(no samples, no licences): the jars are struck ceramic (modal synthesis), the rest a small electronic kit, mixed
with sidechain on the kick, a dotted-eighth echo on the jars and the room's impulse response.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np

from reels.assets import ROOT, episode_dir, style
from reels.schema import STEPS_PER_BAR, Episode, Score
from reels import system

SR = 48000
NOTE = re.compile(r"^([A-G])(#|b)?(-?\d)$")
PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
DRUMS = {"bombo", "caja", "hats"}
VELOCITY = {"x": 0.8, "X": 1.0, "o": 0.45, "O": 0.8}


def midi(name: str) -> int:
    m = NOTE.match(name)
    if not m:
        raise ValueError(f"not a note: {name!r}")
    letter, acc, octave = m.groups()
    return 12 * (int(octave) + 1) + PITCH[letter] + {"#": 1, "b": -1, None: 0}[acc]


def pitch_class(name: str) -> int:
    return midi(name + "4") % 12


def step_seconds(score: Score) -> float:
    return 60 / score.bpm / 4


def notes(score: Score) -> list[dict]:
    """Every note of the score: track, start step, length in steps, pitches (empty for drums), velocity, open hat."""
    out, at = [], 0
    for sec in score.sections:
        steps = sec.bars * STEPS_PER_BAR
        for track, pattern in sec.tracks.items():
            tokens = pattern.replace("|", " ").split()
            if not tokens:
                continue
            if len(tokens) > steps:
                raise ValueError(f"section {sec.name}, {track.value}: {len(tokens)} steps in a {steps}-step section")
            last = None
            for i in range(steps):
                tok = tokens[i % len(tokens)]
                if tok == "-":
                    if last is not None:
                        last["len"] += 1
                    continue
                last = None
                if tok == ".":
                    continue
                if track.value in DRUMS:
                    if tok not in VELOCITY:
                        raise ValueError(f"section {sec.name}, {track.value}: drum token {tok!r} (use x X o O .)")
                    last = {"track": track.value, "step": at + i, "len": 1, "pitches": [], "vel": VELOCITY[tok], "open": tok == "O"}
                else:
                    accent = tok.endswith("!")
                    last = {"track": track.value, "step": at + i, "len": 1, "pitches": [midi(p) for p in tok.rstrip("!").split("+")],
                            "vel": 1.0 if accent else 0.85, "accent": accent, "wobble": sec.wobble, "bar0": at}
                out.append(last)
        at += steps
    return sorted(out, key=lambda n: (n["step"], n["track"]))


def events(score: Score, start_frame: int = 0) -> dict:
    """The score in frames, for Blender: sections (palette, energy…) and every note (tarro notes know their jar)."""
    fps = style()["fps"]
    step = round(step_seconds(score) * fps)
    jars = [pitch_class(j) for j in score.jars]
    sections, at = [], start_frame
    for sec in score.sections:
        length = sec.bars * STEPS_PER_BAR * step
        sections.append({"name": sec.name, "start_frame": at, "end_frame": at + length, "palette": sec.palette, "wobble": sec.wobble,
                         "energy": sec.energy, "impact": sec.impact, "blackout_tail": sec.blackout_tail * step})
        at += length
    out = []
    for n in notes(score):
        e = {"track": n["track"], "frame": start_frame + n["step"] * step, "frames": n["len"] * step, "vel": n["vel"],
             "pitches": n["pitches"], "open": n.get("open", False), "accent": n.get("accent", False)}
        if n["track"] != "tarro":
            out.append(e)
            continue
        for m in n["pitches"]:  # a chord on the jars: every jar in it plays
            if m % 12 not in jars:
                raise ValueError(f"tarro note {m} has no jar (score.jars: {score.jars})")
            out.append({**e, "pitches": [m], "jar": jars.index(m % 12)})
    return {"bpm": score.bpm, "step_frames": step, "bar_frames": step * STEPS_PER_BAR, "jars": len(jars),
            "sections": sections, "notes": out}


# --- synthesis -------------------------------------------------------------------------------------------------

def _hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _t(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SR)) / SR


def _onepole(x: np.ndarray, cutoff: float, high: bool = False) -> np.ndarray:
    """Cheap 6 dB/oct filter (a recursive loop in numpy is slow, so via the frequency domain on short buffers)."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    h = 1 / (1 + 1j * f / cutoff)
    spec *= (1 - h) if high else h
    return np.fft.irfft(spec, len(x))


def tarro(m: int, vel: float, rng: np.random.Generator) -> np.ndarray:
    """A struck glazed clay jar: inharmonic partials that die fast (higher ones faster) and a little tap."""
    t = _t(1.6)
    f0 = _hz(m)
    out = np.zeros_like(t)
    for ratio, amp, decay in ((1.0, 1.0, 0.55), (2.32, 0.42, 0.22), (4.25, 0.2, 0.09), (6.63, 0.1, 0.05), (1.003, 0.35, 0.7)):
        if f0 * ratio > SR / 2.2:
            continue
        out += amp * np.exp(-t / decay) * np.sin(2 * np.pi * f0 * ratio * t + rng.uniform(0, 6.28))
    tap = rng.standard_normal(int(0.012 * SR)) * np.exp(-np.arange(int(0.012 * SR)) / (0.002 * SR))
    out[: len(tap)] += 0.25 * _onepole(tap, 3500)
    attack = np.minimum(1, t / 0.0015)
    return vel * out * attack * 0.5


def bajo(m: int, length: float, vel: float, wobble_hz: float = 0.0, phase: float = 0.0) -> np.ndarray:
    """A sub sine under a growling pair of detuned saws. With wobble the growl opens and shuts in time (the LFO is
    locked to the bar, so every wobble lands on the grid); the sub always stays, the harmonics carry it on a phone."""
    t = _t(length + 0.12)
    env = np.minimum(1, t / 0.004) * np.where(t < length, 1.0, np.exp(-(t - length) / 0.04))
    f = _hz(m)
    sub = np.sin(2 * np.pi * f * t)
    saw = sum(2 * ((f * k * t + o) % 1.0) - 1 for k, o in ((1.0, 0.0), (1.007, 0.31), (0.995, 0.67))) / 3
    dark, bright = _onepole(_onepole(saw, 180), 260), _onepole(saw, 2400)
    if wobble_hz:
        lfo = 0.5 - 0.5 * np.cos(2 * np.pi * (wobble_hz * t + phase))
    else:
        lfo = 0.25 + 0.55 * np.exp(-t / 0.09)  # a plain note still barks on its attack
    growl = np.tanh(3.0 * (dark * (1 - lfo) + bright * lfo))
    return vel * env * (0.62 * np.tanh(1.8 * sub) + 0.38 * growl)


def pad(ms: list[int], length: float, vel: float, rng: np.random.Generator) -> np.ndarray:
    """Soft detuned saws, low-passed: the warm bed under the jars."""
    t = _t(length + 0.8)
    out = np.zeros_like(t)
    for m in ms:
        for cents in (-9, 0, 8):
            f = _hz(m) * 2 ** (cents / 1200)
            ph = (f * t + rng.uniform()) % 1.0
            out += 2 * ph - 1
    out = _onepole(_onepole(_onepole(out, 900), 1400), 160, high=True)  # no mud under the bass
    env = np.minimum(1, t / 0.35) * np.where(t < length, 1.0, np.exp(-(t - length) / 0.3))
    return vel * 0.05 * out * env / max(1, len(ms)) * 3


def bombo(vel: float) -> np.ndarray:
    """An 808-ish kick: a pitch drop into a sub tail, a click on top, driven hard."""
    t = _t(0.6)
    freq = 44 + 140 * np.exp(-t / 0.03)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.26)
    click = np.exp(-t / 0.0015) * 0.5
    return vel * 1.0 * np.tanh(2.4 * (body + click))


def caja(vel: float, rng: np.random.Generator) -> np.ndarray:
    """A clap: three quick bursts of band-passed noise, a tail and a little body."""
    t = _t(0.35)
    noise = _onepole(_onepole(rng.standard_normal(len(t)), 900, high=True), 3800)
    env = np.zeros_like(t)
    for k, d in enumerate((0.0, 0.011, 0.022)):
        env += (t >= d) * np.exp(-np.maximum(0, t - d) / (0.008 if k < 2 else 0.11))
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.4
    return vel * 0.55 * (noise * env / np.abs(noise).max() + body)


def hats(vel: float, open_: bool, rng: np.random.Generator) -> np.ndarray:
    t = _t(0.3 if open_ else 0.08)
    noise = _onepole(rng.standard_normal(len(t)), 7000, high=True)
    return vel * 0.22 * noise / np.abs(noise).max() * np.exp(-t / (0.09 if open_ else 0.018))


def riser(seconds: float, rng: np.random.Generator) -> np.ndarray:
    t = _t(seconds)
    k = t / seconds
    noise = rng.standard_normal(len(t))
    # Brighter as it climbs: blend a dark and a bright copy.
    x = (1 - k) * _onepole(noise, 600) + k * _onepole(noise, 6000, high=True) * 0.6
    return 0.18 * x / np.abs(x).max() * k ** 2.2


def impact(rng: np.random.Generator) -> np.ndarray:
    t = _t(2.2)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t / 0.08)) / SR) * np.exp(-t / 0.7)
    air = _onepole(rng.standard_normal(len(t)), 2500, high=True) * np.exp(-t / 0.5) * 0.15
    return 0.8 * np.tanh(1.5 * boom) + air


def _add(bus: np.ndarray, sig: np.ndarray, at: float, pan: float = 0.0) -> None:
    """Mix a mono signal into a stereo bus at `at` seconds (equal-power pan, -1 left … 1 right)."""
    i = int(round(at * SR))
    if i >= bus.shape[1]:
        return
    sig = sig[: bus.shape[1] - i]
    a = (pan + 1) * np.pi / 4
    bus[0, i: i + len(sig)] += np.cos(a) * sig
    bus[1, i: i + len(sig)] += np.sin(a) * sig


def _convolve(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = x.shape[1] + ir.shape[1] - 1
    size = 1 << (n - 1).bit_length()
    out = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:, : x.shape[1]]
    return out


def _read_wav(path: Path) -> np.ndarray:
    raw = subprocess.run([system.ffmpeg(), "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).T.astype(np.float64)


def render(episode: Episode, lead_in: float = 0.0) -> Path:
    """The whole mix -> episodes/<slug>/audio/score.wav. lead_in: seconds of silence before the first note."""
    score = episode.score
    rng = np.random.default_rng(7)
    step = step_seconds(score)
    total = lead_in + score.bars() * STEPS_PER_BAR * step + 2.5  # room for the last tails
    n = int(total * SR)
    buses = {k: np.zeros((2, n)) for k in ("tarro", "bajo", "pad", "drums", "fx")}
    jars = [pitch_class(j) for j in score.jars]
    kicks = []
    for note in notes(score):
        at = lead_in + note["step"] * step
        length = note["len"] * step
        tr = note["track"]
        if tr == "tarro":
            for m in note["pitches"]:
                jar = jars.index(m % 12) if m % 12 in jars else 0
                pan = -0.55 + 1.1 * jar / max(1, len(jars) - 1)  # the jars spread across the room, left to right
                _add(buses["tarro"], tarro(m, note["vel"], rng), at, pan)
        elif tr == "bajo":
            wob = note["wobble"] / (STEPS_PER_BAR * step) if note["wobble"] else 0.0
            phase = ((note["step"] - note["bar0"]) % STEPS_PER_BAR) / STEPS_PER_BAR * note["wobble"]
            _add(buses["bajo"], bajo(note["pitches"][0], length, note["vel"], wob, phase), at)
        elif tr == "pad":
            _add(buses["pad"], pad(note["pitches"], length, note["vel"], rng), at)
        elif tr == "bombo":
            _add(buses["drums"], bombo(note["vel"]), at)
            kicks.append(at)
        elif tr == "caja":
            _add(buses["drums"], caja(note["vel"], rng), at, 0.05)
        elif tr == "hats":
            _add(buses["drums"], hats(note["vel"], note["open"], rng), at, 0.25)
    at = lead_in
    for sec in score.sections:
        length = sec.bars * STEPS_PER_BAR * step
        if sec.impact:
            _add(buses["fx"], impact(rng), at)
        if sec.riser:
            _add(buses["fx"], riser(length, rng), at)
        at += length

    # Sidechain: the bed ducks on every kick and breathes back (the "pumping" that makes it sound produced).
    duck = np.ones(n)
    t = _t(0.3)
    curve = 1 - 0.75 * np.exp(-t / 0.08)
    for k in kicks:
        i = int(k * SR)
        seg = duck[i: i + len(curve)]
        np.minimum(seg, curve[: len(seg)], out=seg)
    for bus in ("bajo", "pad"):
        buses[bus] *= duck

    # The jars ring out: a dotted-eighth ping-pong echo, darker on every repeat.
    echo = np.zeros((2, n))
    d = int(3 * step * SR)
    src = buses["tarro"].mean(axis=0)
    for k in range(1, 5):
        rep = _onepole(src, 4200 / k) * 0.32 ** k
        side = k % 2
        echo[side, k * d:] += rep[: n - k * d]
    # The room: the same impulse response the voices use, on the jars, the pad and the clap.
    ir = _read_wav(ROOT / "assets/sfx/ir_hall.wav")
    ir /= np.abs(ir).sum(axis=1, keepdims=True).max() / 6
    send = buses["tarro"] * 0.6 + buses["pad"] * 0.5 + buses["drums"] * 0.12 + echo * 0.4
    verb = _convolve(send, ir) * duck * 0.35

    mix = (buses["tarro"] * 1.25 + echo * 0.5 + buses["bajo"] * 0.85 + buses["pad"] * 0.45 + buses["drums"] * 0.9
           + buses["fx"] * 0.8 + verb)
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # gentle glue on the peaks
    mix *= 0.89 / max(1e-9, np.abs(mix).max())  # -1 dBFS; compose sets the final loudness
    out = episode_dir(episode.slug) / "audio" / "score.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(mix.T, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run([system.ffmpeg(), "-y", "-v", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-", str(out)], input=pcm, check=True)
    return out
