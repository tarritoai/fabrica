"""Join every episode with its latest Instagram snapshot: the table /revision and /ideas read.

Plain markdown on purpose: it is read by Claude Code (skills, subagents) as much as by the user.
Ratios are over reach (accounts), not views, so replays do not inflate them.
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from reels.assets import EPISODES, ROOT, published
from reels.instagram import SNAPSHOTS
from reels.schema import Episode

MADRID = ZoneInfo("Europe/Madrid")
PREDICTIONS = ROOT / "metrics/predicciones.jsonl"  # written by /episodio before publishing: are the critics right?
SETTLED_H = 48  # Meta needs up to 48 h to consolidate a reel's numbers


def latest_snapshots() -> dict[str, dict]:
    """Newest snapshot per slug (unmatched posts are keyed by media id)."""
    latest: dict[str, dict] = {}
    if not SNAPSHOTS.exists():
        return latest
    for line in SNAPSHOTS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        key = row["slug"] or f"?{row['media_id']}"
        if key not in latest or row["fetched_at"] > latest[key]["fetched_at"]:
            latest[key] = row
    return latest


def predictions() -> dict[str, dict]:
    """Latest prediction per slug: {slug, fecha, espectadores: {nombre: {nota, comparte}}, jurado, salta_3s, compart_pct}."""
    out: dict[str, dict] = {}
    if PREDICTIONS.exists():
        for line in PREDICTIONS.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            out[row["slug"]] = row
    return out


def _episodes() -> dict[str, Episode]:
    eps = {}
    for p in sorted(EPISODES.glob("*/script.json")):
        if p.parent.name.startswith("_"):
            continue
        try:
            eps[p.parent.name] = Episode.model_validate_json(p.read_text(encoding="utf-8"))
        except ValueError:
            continue  # an old script that no longer validates: it still shows up in the done list by name
    return eps


def _timing(slug: str) -> tuple[float | None, float | None]:
    """(duration, seconds until the first voice) from the 2D timeline, when the voices exist."""
    p = EPISODES / slug / "timeline.json"
    if not p.exists():
        return None, None
    tl = json.loads(p.read_text(encoding="utf-8"))
    first = tl["beats"][0]["start"] if tl.get("beats") else None
    return tl["frames"] / tl["fps"], first


def _pct(n, d) -> str:
    return f"{100 * n / d:.1f}" if n is not None and d else "-"


def metrics_table() -> str:
    eps = _episodes()
    preds = predictions()
    rows = []
    for key, s in sorted(latest_snapshots().items(), key=lambda kv: kv[1]["posted_at"]):
        m = s["metrics"]
        slug = s["slug"]
        ep = eps.get(slug) if slug else None
        dur, first = _timing(slug) if slug else (None, None)
        dur = s.get("duration_s") or dur
        reach = m.get("reach")
        watch = (m.get("ig_reels_avg_watch_time") or 0) / 1000
        posted = datetime.fromisoformat(s["posted_at"]).astimezone(MADRID)
        age = s["age_h"]
        rows.append([
            slug or f"? ({s['media_id']})",
            posted.strftime("%a %d %H:%M"),
            f"{age:.0f} h" + ("" if age >= SETTLED_H else " *"),
            f"{dur:.0f}" if dur else "-",
            f"{first:.1f}" if first is not None else "-",
            f"{m.get('views', 0):,}".replace(",", "."),
            f"{reach:,}".replace(",", ".") if reach else "-",
            f"{m['reels_skip_rate']:.0f}" if m.get("reels_skip_rate") is not None else "-",
            f"{watch:.1f}" if watch else "-",
            f"{100 * watch / dur:.0f}" if watch and dur else "-",
            _pct(m.get("shares"), reach),
            _pct(m.get("saved"), reach),
            _pct(m.get("comments"), reach),
            _pct(m.get("likes"), reach),
            ep.tone if ep else "-",
            ",".join(ep.tests) if ep and ep.tests else "-",
            _predicted(preds.get(slug)),
        ])
    head = ["episodio", "publicado (Madrid)", "edad", "dur s", "1ª voz s", "visitas", "alcance", "salta <3s %",
            "visto s", "% visto", "compart. %", "guard. %", "coment. %", "likes %", "tono", "tests",
            "predicho (nota esp. · compart. % · salta %)"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    lines.append("\n`*` = menos de 48 h: datos provisionales. Porcentajes sobre alcance (cuentas), no sobre visitas.")
    return "\n".join(lines)


def _predicted(p: dict | None) -> str:
    if not p:
        return "-"
    notes = [v.get("nota") for v in p.get("espectadores", {}).values() if v.get("nota") is not None]
    nota = f"{sum(notes) / len(notes):.1f}" if notes else "-"
    return f"{nota} · {p.get('compart_pct', '-')} · {p.get('salta_3s', '-')}"


def done_list() -> str:
    """Every episode ever made, with its premise and how it did: what /ideas must not repeat."""
    eps = _episodes()
    snaps = latest_snapshots()
    lines = ["| episodio | tono | premisa | estado | compart. % |", "|---|---|---|---|---|"]
    for p in sorted(EPISODES.iterdir()):
        slug = p.name
        if slug.startswith("_") or not (p / "script.json").exists():
            continue
        ep = eps.get(slug)
        s = snaps.get(slug)
        if s:
            state = "publicado"
        elif published(slug, ".mp4").exists():
            state = "terminado"
        else:
            state = "sin terminar"
        share = _pct(s["metrics"].get("shares"), s["metrics"].get("reach")) if s else "-"
        premise = (ep.premise if ep else "(guion antiguo)").replace("|", "/").replace("\n", " ")
        lines.append(f"| {slug} | {ep.tone if ep else '-'} | {premise} | {state} | {share} |")
    return "\n".join(lines)
