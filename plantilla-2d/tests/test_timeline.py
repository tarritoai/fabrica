"""Words → frames: shots cut just before their first word, events land on their word, the ending and the overlays."""

import copy

import pytest

from conftest import fake_voice
from reels import timeline
from reels.schema import Episode


@pytest.fixture
def built(episodes_tmp, example_script):
    episodes_tmp("quijote-gafas", example_script, fake_voice(example_script))
    ep = Episode.model_validate(example_script)
    return ep, timeline.build(ep)


def test_frames_and_shots(built):
    ep, tl = built
    assert tl["fps"] == 30 and tl["width"] == 1080 and tl["height"] == 1920
    assert tl["shots"][0]["from"] == 0
    starts = {b["id"]: b["from"] for b in tl["beats"]}
    opening = [b.id for b in ep.beats if b.shot is not None]
    for shot, bid in zip(tl["shots"], opening):
        assert shot["from"] == 0 or starts[bid] - 3 <= shot["from"] <= starts[bid]
    for a, b in zip(tl["shots"], tl["shots"][1:]):
        assert a["to"] == b["from"] > a["from"]
    assert tl["shots"][-1]["to"] == tl["frames"]
    assert len(tl["shots"]) == len(opening) + 1  # + the ending's shot


def test_events_land_on_their_word(built):
    _, tl = built
    words = [w for w in tl["words"] if w["beat"] == 2]
    molino = next(w for w in words if timeline.norm(w["text"]) == "molino")
    stamp = next(e for e in tl["events"] if e["type"] == "stamp" and e["text"] == "MOLINO")
    assert stamp["frame"] == round((molino["start"] + 0.15) * 30)
    assert stamp["until"] == tl["shots"][stamp["shot"]]["to"] - 1  # a stamp lasts until its shot ends
    count = [e["value"] for e in tl["events"] if e["type"] == "count"]
    assert count == [1, 2, 3]


def test_takes_are_laid_with_gaps(built):
    ep, tl = built
    voices = tl["audio"]["voices"]
    assert [v["file"] for v in voices] == ["audio/toma_01.wav", "audio/toma_02.wav", "audio/toma_03.wav"]
    narr_end = max(w["end"] for w in tl["words"] if w["voice"] == "narrador")
    sancho_start = min(w["start"] for w in tl["words"] if w["voice"] == "sancho")
    assert sancho_start == pytest.approx(narr_end + ep.pace.gap, abs=0.002)


def test_overlays_and_ending(built):
    ep, tl = built
    assert tl["title_card"]["from"] == 0  # the question is on screen in frame 0
    assert tl["counter"]["label"] == "LOCURAS EVITADAS"
    q = next(e for e in tl["events"] if e["type"] == "question")
    assert q["frame"] == tl["ending_from"] + round(ep.ending.question_delay * 30)
    assert tl["frames"] == round((max(w["end"] for w in tl["words"]) + ep.ending.seconds) * 30)
    sounds = {s["file"] for s in tl["audio"]["sfx"]}
    assert {"sfx/sello.wav", "sfx/ding.wav", "sfx/papel.wav", "sfx/destello.wav", "sfx/pop.wav"} <= sounds


def test_bad_anchor_says_which_word(episodes_tmp, example_script):
    bad = copy.deepcopy(example_script)
    bad["beats"][1]["events"][0]["at"] = "dragón"
    episodes_tmp("quijote-gafas", bad, fake_voice(bad))
    with pytest.raises(timeline.TimelineError, match="dragón"):
        timeline.build(Episode.model_validate(bad))


def test_nth_occurrence_anchor():
    words = [{"text": t, "start": i * 1.0, "end": i + 0.5} for i, t in enumerate("y es un molino y es otro molino".split())]
    assert timeline.resolve_anchor("molino#2", words, 1) == 7.0
    assert timeline.resolve_anchor("inicio", words, 1) == 0.0
    assert timeline.resolve_anchor("fin", words, 1) == 7.5


def test_missing_voice_is_explained(episodes_tmp, example_script):
    episodes_tmp("quijote-gafas", example_script)
    with pytest.raises(timeline.TimelineError, match="reels voice"):
        timeline.build(Episode.model_validate(example_script))


def test_free_sketch_without_voices(episodes_tmp, example_script):
    """`reels stills --sin-voz`: a timeline from the text alone, to look at the frames before paying."""
    episodes_tmp("quijote-gafas", example_script)  # no voice.json
    tl = timeline.build(Episode.model_validate(example_script), estimated=True)
    assert tl["estimated"] and tl["audio"]["voices"] == [] and tl["frames"] > 30 * 10
    assert [e["value"] for e in tl["events"] if e["type"] == "count"] == [1, 2, 3]


def test_a_cut_never_lands_before_the_previous_line_ends(built):
    _, tl = built
    for prev, b in zip(tl["beats"], tl["beats"][1:]):
        for s in tl["shots"]:
            if s["from"] and prev["from"] <= s["from"] <= b["from"]:
                assert s["from"] > prev["to"] or s["from"] >= b["from"] - 3


def test_carousel_picks_the_end_of_each_shot(built):
    from reels.carousel import pick

    _, tl = built
    frames = pick(tl, 6)
    assert frames[0] == 0 and len(frames) <= 6 and frames == sorted(frames)
    assert all(any(s["from"] <= f < s["to"] for s in tl["shots"]) for f in frames)
