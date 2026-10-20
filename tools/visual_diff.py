"""Visual regression: compare two folders of rendered frames (same file names) pixel by pixel.

    uv run --project plantilla python tools/visual_diff.py <before_dir> <after_dir> [--tolerance 0.5]

Prints, per frame, the mean absolute difference (0-255 scale) and the share of pixels that changed by more than
8 levels; exits 1 if any frame's mean difference is above the tolerance. Frames are decoded with ffmpeg (no PIL).
Used before/after refactors of the cast and rigs (fabrica-p1-generalidad): the smoke episode must render the same.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


def ffmpeg() -> str:
    return shutil.which("ffmpeg") or str(Path.home() / ".local/opt/ffmpeg-9/bin/ffmpeg")


def load(path: Path) -> np.ndarray:
    probe = subprocess.run([ffmpeg(), "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True, check=True)
    info = subprocess.run([ffmpeg(), "-i", str(path)], capture_output=True, text=True).stderr
    import re

    w, h = map(int, re.search(r", (\d{2,5})x(\d{2,5})", info).groups())
    return np.frombuffer(probe.stdout, np.uint8).reshape(h, w, 3).astype(np.int16)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    ap.add_argument("--tolerance", type=float, default=0.5, help="max mean abs difference per frame (0-255)")
    args = ap.parse_args()
    rows, worst = [], 0.0
    for a in sorted(args.before.glob("*.png")):
        b = args.after / a.name
        if not b.exists():
            rows.append({"frame": a.name, "missing": True})
            worst = float("inf")
            continue
        x, y = load(a), load(b)
        if x.shape != y.shape:
            rows.append({"frame": a.name, "shape": [x.shape, y.shape]})
            worst = float("inf")
            continue
        d = np.abs(x - y)
        mean, changed = float(d.mean()), float((d.max(axis=2) > 8).mean())
        worst = max(worst, mean)
        rows.append({"frame": a.name, "mean_abs": round(mean, 4), "changed_px": round(changed, 5), "max": int(d.max())})
    for r in rows:
        print(json.dumps(r))
    ok = worst <= args.tolerance
    print(f"{'OK' if ok else 'DIFFERENT'}: worst mean abs diff {worst:.4f} (tolerance {args.tolerance})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
