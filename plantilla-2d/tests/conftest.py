import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "assets" / "ejemplos" / "quijote-gafas"
HUMO = ROOT / "assets" / "humo"


@pytest.fixture
def example_script() -> dict:
    return json.loads((EXAMPLE / "script.json").read_text(encoding="utf-8"))


@pytest.fixture
def episodes_tmp(tmp_path, monkeypatch):
    """Point episodes/ at a temporary folder; returns a function that writes episodes/<slug>/script.json."""
    import reels.assets as assets
    import reels.lint as lint
    import reels.timeline as timeline

    monkeypatch.setattr(assets, "EPISODES", tmp_path)
    monkeypatch.setattr(lint, "episode_dir", lambda slug: tmp_path / slug)
    monkeypatch.setattr(timeline, "episode_dir", lambda slug: tmp_path / slug)

    def write(slug: str, data: dict, voice: dict | None = None) -> Path:
        d = tmp_path / slug
        d.mkdir(exist_ok=True)
        (d / "script.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        if voice is not None:
            (d / "voice.json").write_text(json.dumps(voice, ensure_ascii=False), encoding="utf-8")
        return d

    return write


def fake_voice(script: dict, seconds_per_word: float = 0.3) -> dict:
    """A voice.json as `reels voice` would write it, with one take per run of the same voice (no audio needed)."""
    takes, cur, t = [], None, 0.0
    for b in script["beats"]:
        if cur is None or cur["voice"] != b["voice"]:
            cur = {"take": len(takes) + 1, "file": f"audio/toma_{len(takes) + 1:02d}.wav", "voice": b["voice"], "beats": [],
                   "words": [], "duration": 0.0, "mean_db": -19.0, "similarity": 1.0}
            takes.append(cur)
            t = 0.05
        cur["beats"].append(b["id"])
        for w in b["line"].split():
            cur["words"].append({"text": w, "start": round(t, 3), "end": round(t + seconds_per_word * 0.8, 3), "beat": b["id"]})
            t += seconds_per_word
        cur["duration"] = round(t + 0.1, 3)
    return {"model": "eleven_v4", "takes": takes, "credits": 0}


@pytest.fixture
def copy_example(tmp_path):
    def make(slug: str = "quijote-gafas") -> Path:
        d = tmp_path / slug
        shutil.copytree(EXAMPLE, d)
        return d
    return make
