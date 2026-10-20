"""Estimate the ElevenLabs credits an episode's voices will cost, BEFORE spending anything.

Usage (from the project root):
    uv run python .claude/skills/episodio/estimar_voz.py <slug> [--tomas 7,12] [--solo 3,5]

--tomas: beats that will also get 3 solo takes to choose by ear (reels voice --takes).
--solo:  only these beats will be regenerated (reels voice --only): estimate just them.
It is an upper bound: anything already in .cache/voice/ is reused for free.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from reels.schema import Episode  # noqa: E402
from reels.voice import TAKES, tts_text  # noqa: E402

RETOUCH = 0.30  # keep a 30 % margin for re-doing a few lines
# Measured on the course account (oct. 2026, eleven_v4): an episode of 524 characters x 3 dialogue takes cost 759
# credits, ~0.5 per character. "Como mucho" keeps 1 credit per character (the plan's nominal rate) as the ceiling.
TYPICAL = 0.5


def ids(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x.strip()] if text else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--tomas", default="", help="beats con 3 tomas sueltas, p. ej. 7,12")
    ap.add_argument("--solo", default="", help="solo estos beats (reels voice --only)")
    a = ap.parse_args()

    path = ROOT / "episodes" / a.slug / "script.json"
    if not path.exists():
        print(f"No existe {path.relative_to(ROOT)}: escribe antes el guion.")
        return 1
    ep = Episode.model_validate_json(path.read_text(encoding="utf-8"))
    spoken = [b for b in ep.beats if b.line]
    only = set(ids(a.solo))
    chars = {b.id: len(tts_text(b)) for b in spoken}

    if only:
        base = sum(c for i, c in chars.items() if i in only)
        how = f"rehacer {len(only)} frases sueltas"
    else:
        base = TAKES * sum(chars.values()) + sum(chars.values())  # 3 full dialogue takes + re-slicing lines that fail
        how = f"episodio entero ({len(spoken)} frases, {TAKES} tomas del diálogo completo)"
    takes = sum(3 * chars.get(i, 0) for i in ids(a.tomas))
    total = base + takes
    margin = round(total * (1 + RETOUCH))

    print(f"Voz de «{ep.title}» ({a.slug}): {how}")
    print(f"  caracteres por pasada: {sum(chars.values())}")
    print(f"  créditos, lo normal con v4: ~{round(total * TYPICAL)}")
    print(f"  créditos, como mucho: ~{total}" + (f" (incluye {takes} de tomas sueltas)" if takes else ""))
    print(f"  con margen de retoques (+30 %): ~{margin}")
    print("  Lo que ya esté en la caché (.cache/voice/) no se cobra. Créditos que te quedan: uv run reels doctor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
