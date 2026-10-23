"""An Instagram carousel (1080×1350 images) from a reel: the frame 0, the end of each shot (what its events left on
screen) and the ending, cropped to 4:5 between the tags and the captions. Free; it never touches the key frames of
`reels stills` (it renders its own)."""

from __future__ import annotations

import shutil
from pathlib import Path

from reels import render, system
from reels.assets import published


def pick(tl: dict, n: int) -> list[int]:
    """Frame 0, then the last moment of each shot (spread evenly if there are more shots than slides)."""
    ends = [max(s["from"], s["to"] - 4) for s in tl["shots"][1:]]
    if len(ends) > n - 1:
        step = len(ends) / (n - 1)
        ends = [ends[min(len(ends) - 1, round(i * step + step - 1))] for i in range(n - 1)]
    return sorted({0, *ends})[:n]


def make(slug: str, n: int = 6, frames: list[int] | None = None) -> Path:
    tl = render.timeline(slug)
    picks = frames or pick(tl, n)
    _, images = render.stills(slug, picks, folder_name="carrusel")
    folder = published(slug, "_x").parent / "carrusel"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for i, img in enumerate(images, start=1):
        # 1080×1920 → 1080×1350: keep the part between the tags and the captions (y 150…1500)
        system.run_tool([system.ffmpeg(), "-y", "-loglevel", "error", "-i", str(img), "-vf", "crop=1080:1350:0:150",
                         "-q:v", "2", str(folder / f"{i:02d}.jpg")], "ffmpeg (carrusel)")
    return folder
