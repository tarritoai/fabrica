#!/bin/bash
# Visual regression of the smoke episode: renders its keyframes (EEVEE, preview) with the current code and compares
# them pixel by pixel with tools/regresion/humo/ (the reference, reviewed by eye on 2026-10-20: the neutral room at
# night, prota and taza). Usage: tools/regresion_humo.sh   (from the repo root; needs Blender, ffmpeg and uv)
# After an intended visual change: look at the new frames, then copy them over the reference in the same commit.
set -e
cd "$(dirname "$0")/../plantilla"
uv run python -c "
from reels import smoke, build as b
from reels.schema import Episode
out = smoke.prepare()
b.build(Episode.model_validate_json((out / 'script.json').read_text(encoding='utf-8')))
b.render('humo', 'preview', keyframes=True)"
cd ..
uv run --project plantilla python tools/visual_diff.py tools/regresion/humo plantilla/episodes/humo/renders/keyframes_preview
