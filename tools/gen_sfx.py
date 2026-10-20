"""Synthesise the template's placeholder sound effects with ffmpeg (no samples, no licences: CC0, made here).

    python tools/gen_sfx.py [ffmpeg]      -> plantilla/assets/sfx/*.wav  (48 kHz, stereo, 16 bit)

Why: the original project's effects have no documented origin (some were generated with ElevenLabs on another
account), so they cannot be redistributed. These are simple, honest stand-ins with the same names, lengths and
loudness, so every piece of the pipeline works; a student can replace any of them with `reels sfx-gen` or with a
sound they have the rights to. Deterministic: the same command always produces the same files.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "plantilla" / "assets" / "sfx"
FF = sys.argv[1] if len(sys.argv) > 1 else "ffmpeg"

NOISE = "(2*random(0)-1)"  # white noise in aevalsrc (seeded: deterministic)

# name: (seconds, aevalsrc expression of t, extra filter chain, target mean volume dB)
# Target loudness copied from the originals so the mix in remotion/src/compose/Final.tsx stays balanced.
SOUNDS: dict[str, tuple[float, str, str, float]] = {
    "ding": (0.7, "sin(2*PI*1320*t)*exp(-6*t)+0.35*sin(2*PI*2640*t)*exp(-9*t)", "", -20.4),
    "ding_alarm": (0.75, "if(lt(t,0.33),sin(2*PI*880*t),sin(2*PI*1175*t))*exp(-4*mod(t,0.375))", "", -19.0),
    "whoosh": (0.45, f"{NOISE}*sin(PI*t/0.45)^2", "bandpass=f=1800:w=1.5", -25.0),
    "error": (0.35, "0.6*sgn(sin(2*PI*196*t))*if(lt(mod(t,0.17),0.13),1,0)", "lowpass=f=2500", -17.3),
    "click": (0.48, f"if(lt(t,0.004),{NOISE},0)+0.6*sin(2*PI*2400*t)*exp(-600*t)", "", -34.3),
    "toc": (0.6, "sin(2*PI*620*t)*exp(-28*t)+0.4*sin(2*PI*1460*t)*exp(-45*t)", "", -33.6),
    "tick": (0.06, "sin(2*PI*4200*t)*exp(-120*t)", "", -24.3),
    "typing": (4.0, f"{NOISE}*if(lt(mod(t*(1+0.25*sin(7*t)),0.14),0.007),1,0)", "bandpass=f=3000:w=1.2", -30.1),
    "typing_tiny": (4.0, f"{NOISE}*if(lt(mod(t*(1+0.2*sin(5*t)),0.19),0.005),1,0)*if(lt(t,1.6),1,0)",
                    "bandpass=f=3500:w=1.2", -43.9),
    "amb_night": (30.0, f"{NOISE}", "lowpass=f=220,lowpass=f=220", -23.5),
    "amb_luces": (11.37, f"0.3*{NOISE}+0.5*sin(2*PI*220*t)*(0.6+0.4*sin(2*PI*0.2*t))+0.4*sin(2*PI*330*t)*(0.6+0.4*sin(2*PI*0.13*t))",
                  "lowpass=f=900", -29.8),
    "amb_ruinas": (26.0, f"{NOISE}*(0.6+0.4*sin(2*PI*0.11*t))", "bandpass=f=500:w=1.8,lowpass=f=1200", -12.0),
    "boom": (2.0, f"(sin(2*PI*48*t)+0.6*{NOISE})*exp(-2.6*t)", "lowpass=f=300", -12.0),
    "cadena": (3.48, f"{NOISE}*min(1,t*4)*exp(-0.5*t)*(0.8+0.2*sin(2*PI*6*t))", "bandpass=f=900:w=2", -12.8),
    "grifo": (3.0, f"{NOISE}*min(1,t*8)*min(1,(3-t)*4)", "bandpass=f=4000:w=1.5", -17.3),
    "glitch": (1.0, "sgn(sin(2*PI*(110+880*floor(mod(t*23,4)))*t))*if(lt(mod(t,0.12),0.07),1,0)", "lowpass=f=6000", -17.5),
    "portal_rumble": (4.48, f"(0.7*sin(2*PI*(40+12*t)*t)+0.5*{NOISE})*min(1,t/2.5)", "lowpass=f=400", -20.2),
    "riser": (2.48, f"(0.5*sin(2*PI*(200+380*t)*t)+0.5*{NOISE})*(t/2.48)^2", "highpass=f=150", -11.9),
    "sky_burst": (3.0, f"{NOISE}*exp(-2.2*t)+0.3*sin(2*PI*1760*t)*exp(-1.5*t)", "highpass=f=400", -25.0),
    "tension": (3.0, "(sin(2*PI*55*t)+sin(2*PI*58.3*t)+0.4*sin(2*PI*110*t))*min(1,t/2)", "lowpass=f=500", -47.1),
    "tunnel_whoosh": (2.0, f"{NOISE}*sin(PI*t/2)^2*(0.7+0.3*sin(2*PI*9*t))", "bandpass=f=1200:w=2", -20.3),
    # Impulse responses for the voice acoustics (afir normalises them: only their decay shape matters).
    "ir_room": (0.6, f"if(lt(t,0.0001),1,{NOISE}*exp(-11*t))", "lowpass=f=6000", -24.0),
    "ir_bano": (0.75, f"if(lt(t,0.0001),1,{NOISE}*exp(-7*t))", "highpass=f=300", -17.9),
    "ir_hall": (4.0, f"if(lt(t,0.0001),1,{NOISE}*exp(-1.7*t))", "lowpass=f=5000", -26.3),
    "ir_ruins": (2.4, f"if(lt(t,0.0001),1,{NOISE}*exp(-2.9*t))", "lowpass=f=3500", -25.5),
}


def mean_volume(path: Path) -> float:
    out = subprocess.run([FF, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", out).group(1))


def make(name: str, seconds: float, expr: str, chain: str, target: float) -> Path:
    dest = OUT / f"{name}.wav"
    raw = OUT / f"{name}.raw.wav"
    graph = f"aevalsrc=exprs='{expr}|{expr}':s=48000:d={seconds}" + (f",{chain}" if chain else "")
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", graph, "-c:a", "pcm_s16le", str(raw)], check=True)
    gain = target - mean_volume(raw)
    # Gain to the original loudness, then a limiter so nothing clips.
    subprocess.run([FF, "-y", "-v", "error", "-i", str(raw), "-af", f"volume={gain:.2f}dB,alimiter=limit=0.95:level=false",
                    "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", "-fflags", "+bitexact", "-flags:a", "+bitexact",
                    str(dest)], check=True)
    raw.unlink()
    return dest


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in SOUNDS.items():
        print(f"{name:14s} {mean_volume(make(name, *spec)):6.1f} dB (objetivo {spec[3]})")
