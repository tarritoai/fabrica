"""Per-episode cost log (episodes/<slug>/cost.json)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# USD per million tokens (input, output).
CLAUDE_PRICES = {"claude-opus-5-5": (4.0, 20.0)}
# ElevenLabs Starter: ~5 USD / 40k credits; multilingual_v2 = 1 credit per character.
ELEVENLABS_USD_PER_CREDIT = 5.0 / 40_000


def log(episode_dir: Path, stage: str, usd: float, **details) -> None:
    path = episode_dir / "cost.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"entries": [], "total_usd": 0.0}
    data["entries"].append(
        {"stage": stage, "usd": round(usd, 5), "at": datetime.now(timezone.utc).isoformat(), **details}
    )
    data["total_usd"] = round(sum(e["usd"] for e in data["entries"]), 5)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def claude_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = CLAUDE_PRICES.get(model, (4.0, 20.0))  # unknown model: estimate with the default prices
    return (input_tokens * pin + output_tokens * pout) / 1e6
