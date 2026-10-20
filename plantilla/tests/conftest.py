import json
import shutil
from pathlib import Path

import pytest

from reels import cast

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _fresh_cast_cache():
    cast.aliases.cache_clear()
    yield
    cast.aliases.cache_clear()


@pytest.fixture
def humo_script() -> dict:
    return json.loads((ROOT / "assets" / "humo" / "script.json").read_text(encoding="utf-8"))


@pytest.fixture
def episode_in_tmp(tmp_path, monkeypatch):
    """Point episodes/ at a temporary folder and return a function that writes episodes/<slug>/script.json."""
    import reels.assets as assets

    monkeypatch.setattr(assets, "EPISODES", tmp_path)

    def write(slug: str, data: dict, audio_from: Path | None = None) -> Path:
        d = tmp_path / slug
        d.mkdir()
        (d / "script.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        if audio_from:
            shutil.copytree(audio_from, d / "audio")
        return d

    return write
