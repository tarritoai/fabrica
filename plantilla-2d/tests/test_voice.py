"""Voices: one take per run of the same voice, numbers spelled for the voice but shown as written, [tags] are not
words, and the examples that ship with the factory are entirely in their own cache (they cost nothing)."""

import json

import pytest

from conftest import EXAMPLE, HUMO
from reels import voice
from reels.schema import Episode


def _ep(folder):
    return Episode.model_validate_json((folder / "script.json").read_text(encoding="utf-8"))


def test_runs_of_the_same_voice_are_one_take():
    takes = voice.takes(_ep(EXAMPLE))
    assert [(t.voice, [b.id for b in t.beats]) for t in takes] == [
        ("narrador", [1, 2, 3, 4, 5]), ("sancho", [6]), ("quijote", [7])]
    assert takes[1].previous == takes[0].text and takes[2].previous == takes[1].text


@pytest.mark.parametrize("folder", [EXAMPLE, HUMO], ids=["quijote-gafas", "humo"])
def test_shipped_examples_are_fully_cached(folder):
    """Every take of the example and of the smoke test has its paid audio in assets/<…>/voz/: free for the student."""
    ep = _ep(folder)
    shipped = {p.stem for p in (folder / "voz").glob("*.mp3")}
    for t in voice.takes(ep):
        v = voice.voice_of(ep, t.voice)
        key = voice.cache_key(v.voice_id, voice.payload(t, v))
        assert key in shipped, f"toma {t.index} sin caché"
        meta = json.loads((folder / "voz" / f"{key}.json").read_text(encoding="utf-8"))
        assert meta["alignment"]["characters"] and meta["payload"]["text"] == t.text


def test_spell_numbers():
    assert voice.spell_numbers("Locuras: 3.") == "Locuras: tres."
    assert voice.spell_numbers("1.200 páginas") == "mil doscientas páginas"
    assert voice.spell_numbers("21 veces") == "veintiuna veces"
    assert voice.spell(1600) == "mil seiscientos"


def test_line_words_keep_digits_and_skip_tags():
    from reels.schema import Beat

    beat = Beat(id=4, voice="narrador", line="Páginas: 1.200. Ahora, 3.", tags=["rushed"])
    take = voice.Take(1, "narrador", [beat], 1000, None)
    assert take.text == "[rushed] Páginas: mil doscientas. Ahora, tres."
    chars = list(take.text)
    al = {"characters": chars, "character_start_times_seconds": [i * 0.05 for i in range(len(chars))],
          "character_end_times_seconds": [i * 0.05 + 0.04 for i in range(len(chars))]}
    spoken = voice.words_from_alignment(al)
    assert [w["text"] for w in spoken] == ["Páginas:", "mil", "doscientas.", "Ahora,", "tres."]
    words = voice.line_words(take, spoken)
    assert [w["text"] for w in words] == ["Páginas:", "1.200.", "Ahora,", "3."]
    assert words[1]["start"] == spoken[1]["start"] and words[1]["end"] == spoken[2]["end"]


def test_estimate_counts_only_what_is_not_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, "CACHE", tmp_path)
    ep = _ep(HUMO)
    est = voice.estimate(ep)
    assert est["characters_new"] == sum(len(t.text) for t in voice.takes(ep)) and est["characters_cached"] == 0
    for f in (HUMO / "voz").iterdir():
        (tmp_path / f.name).write_bytes(f.read_bytes())
    assert voice.estimate(ep)["characters_new"] == 0


def test_spending_is_refused_when_not_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr(voice, "CACHE", tmp_path)
    monkeypatch.setattr(voice, "episode_dir", lambda slug: tmp_path / slug)
    with pytest.raises(voice.SpendError):
        voice.voice_episode(_ep(HUMO), allow_spend=False)


def test_a_performance_is_its_own_take():
    ep = _ep(EXAMPLE)
    data = ep.model_dump(by_alias=True)
    data["beats"][2]["performance"] = "actuaciones/beat_03.mp3"
    takes = voice.takes(Episode.model_validate(data))
    assert [[b.id for b in t.beats] for t in takes][:3] == [[1, 2], [3], [4, 5]]


def test_the_hook_is_its_own_take_and_a_b_hook_pays_only_the_hook():
    from reels.schema import Episode as Ep

    data = json.loads((EXAMPLE / "script.json").read_text(encoding="utf-8"))
    data["pace"]["hook_alone"] = True
    a = voice.takes(Ep.model_validate(data))
    assert [[b.id for b in t.beats] for t in a][:2] == [[1], [2, 3, 4, 5]]
    assert a[1].previous is None  # the narrator going on does not «answer» its own hook
    data["beats"][0]["line"] = "¿Y si Don Quijote viera perfectamente?"
    b = voice.takes(Ep.model_validate(data))
    changed = [i for i, (x, y) in enumerate(zip(a, b)) if voice.payload(x, voice.voice_of(Ep.model_validate(data), x.voice)) !=
               voice.payload(y, voice.voice_of(Ep.model_validate(data), y.voice))]
    assert changed == [0]


def test_signature_changes_with_the_rhythm_only_when_it_should():
    ep = _ep(EXAMPLE)
    data = ep.model_dump(by_alias=True)
    data["pace"]["tempo"] = 1.2
    assert voice.signature(Episode.model_validate(data)) != voice.signature(ep)
    assert voice.signature(_ep(EXAMPLE)) == voice.signature(ep)
