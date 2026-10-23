"""`reels lint <slug>`: the free review of a 2D script before anything costs money.

ERROR blocks the next paid step (the voice); AVISO is worth a look. It checks what a person would only notice after
paying: an event hanging from a word the line does not say, an actor that is not in the shot, a piece or a background
that does not exist, a sound or a track that is not there, lines too long for the phone, a reel too long or too short.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from reels.assets import ASSETS, PERSONAJES, REMOTION, SFX, episode_dir
from reels.schema import Episode, Event
from reels.timeline import norm

SAFE_X = (120, 960)
SAFE_Y = (300, 1560)
CHARS_PER_SECOND = 15.0  # «¿Y si…?» narrators after tightening


@dataclass
class Issue:
    level: str  # ERROR | AVISO
    where: str
    msg: str


def known_pieces(slug: str) -> set[str]:
    """Names exported (capitalised) by the generic pieces, your characters and this episode's pieces."""
    src = REMOTION / "src"
    folders = [src / "piezas", src / "personajes"]
    for s in (slug, slug.removesuffix("-b")):
        folders.append(src / "episodios" / s)
    names: set[str] = set()
    for folder in folders:
        for f in folder.glob("*.ts*"):
            text = f.read_text(encoding="utf-8", errors="replace")
            names |= set(re.findall(r"export\s+(?:const|function)\s+([A-Z]\w*)", text))
            for group in re.findall(r"export\s*\{([^}]*)\}", text):
                names |= {n.split(" as ")[-1].strip() for n in group.split(",") if n.strip()[:1].isupper()}
    return names


def palettes() -> set[str]:
    style = REMOTION / "src" / "kit" / "style.ts"
    return set(re.findall(r'nombre:\s*"(\w+)"', style.read_text(encoding="utf-8"))) if style.exists() else {"alfar"}


def _anchor_ok(at: str, line: str) -> bool:
    if at in ("inicio", "fin"):
        return True
    word, _, nth = at.partition("#")
    n = int(nth) if nth else 1
    return sum(1 for w in line.split() if norm(w) == norm(word)) >= n


def lint(slug: str, voice: bool = True) -> list[Issue]:
    out: list[Issue] = []
    path = episode_dir(slug) / "script.json"
    if not path.exists():
        return [Issue("ERROR", "guion", f"no existe {path.relative_to(episode_dir(slug).parent.parent)}")]
    raw = path.read_text(encoding="utf-8")
    try:
        ep = Episode.model_validate_json(raw)
    except ValidationError as e:
        for err in e.errors():
            where = ".".join(str(x) for x in err["loc"])
            out.append(Issue("ERROR", "guion", f"{where}: {err['msg']}"))
        return out
    if ep.slug != slug:
        out.append(Issue("ERROR", "guion", f"«slug» dice «{ep.slug}» pero la carpeta es «{slug}»: las voces irían a otro sitio"))
    pieces = known_pieces(slug)
    if ep.palette not in palettes():
        out.append(Issue("ERROR", "estilo", f"no existe la paleta «{ep.palette}» (hay: {', '.join(sorted(palettes()))})"))
    for key, v in ep.voices.items():
        if isinstance(v, str):
            pj = PERSONAJES / v / "personaje.json"
            if not pj.exists():
                out.append(Issue("ERROR", "voces", f"«{key}» apunta al personaje «{v}», que no existe (personajes/{v}/personaje.json)"))
            elif not (json.loads(pj.read_text(encoding="utf-8")).get("voice") or {}).get("voice_id"):
                out.append(Issue("ERROR", "voces", f"el personaje «{v}» todavía no tiene voz: /personaje {v}"))
    if ep.music and not (ASSETS / "music" / ep.music.track).exists():
        out.append(Issue("ERROR", "música", f"no existe assets/music/{ep.music.track}"))

    def check_shot(shot, where: str) -> set[str]:
        if shot.scene not in pieces:
            out.append(Issue("ERROR", where, f"no existe el fondo «{shot.scene}» (mira docs/piezas.md)"))
        for a in shot.actors:
            if a.piece not in pieces:
                out.append(Issue("ERROR", where, f"no existe la pieza «{a.piece}» (actor «{a.id}»): o se dibuja (dibujante) o se usa otra"))
            if a.voice and a.voice not in ep.voices:
                out.append(Issue("ERROR", where, f"el actor «{a.id}» tiene la voz «{a.voice}», que no está en «voices»"))
        return {a.id for a in shot.actors}

    def check_event(ev: Event, actors: set[str], where: str, line: str | None) -> None:
        if line is not None and not _anchor_ok(ev.at, line):
            out.append(Issue("ERROR", where, f"el evento «{ev.type}» cuelga de «{ev.at}», que la frase no dice"))
        if ev.actor and ev.actor not in actors:
            out.append(Issue("ERROR", where, f"el evento «{ev.type}» mueve a «{ev.actor}», que no está en este plano"))
        if ev.type == "reveal" and ev.piece and ev.piece not in pieces:
            out.append(Issue("ERROR", where, f"no existe la pieza «{ev.piece}» del revelado"))
        if ev.type == "sfx" and ev.sound and not (SFX / f"{ev.sound}.wav").exists():
            out.append(Issue("ERROR", where, f"no existe el efecto assets/sfx/{ev.sound}.wav"))
        if ev.type in ("stamp", "label") and ev.x is not None and ev.y is not None:
            if not (SAFE_X[0] <= ev.x <= SAFE_X[1] and SAFE_Y[0] <= ev.y <= SAFE_Y[1]):
                out.append(Issue("AVISO", where, f"«{ev.text}» queda fuera de la zona segura del teléfono ({ev.x:.0f}, {ev.y:.0f})"))
        if ev.until and ev.until not in ("plano", "beat", "final") and line is not None and not _anchor_ok(ev.until, line):
            out.append(Issue("ERROR", where, f"«until» = «{ev.until}» no es una palabra de la frase"))

    actors: set[str] = set()
    total_chars = 0
    for b in ep.beats:
        where = f"beat {b.id}"
        if b.shot:
            actors = check_shot(b.shot, where)
        for ev in b.events:
            check_event(ev, actors, where, b.line)
        for h in b.highlight:
            if not any(norm(w) == norm(h) for w in b.line.split()):
                out.append(Issue("AVISO", where, f"«{h}» está en highlight pero la frase no lo dice"))
        if b.bubble and b.bubble.actor and b.bubble.actor not in actors:
            out.append(Issue("ERROR", where, f"el bocadillo apunta a «{b.bubble.actor}», que no está en el plano"))
        longest = max((len(s.split()) for s in re.split(r"[.!?…]+", b.line) if s.strip()), default=0)
        if longest > 14:
            out.append(Issue("AVISO", where, f"una frase de {longest} palabras: en este formato van cortas (≤ 12)"))
        if re.search(r"\d", b.line):
            out.append(Issue("AVISO", where, "lleva cifras: la voz las dirá con letras y el rótulo las enseñará con cifras (comprueba que suena bien)"))
        total_chars += len(b.line)
    if ep.ending.shot:
        actors = check_shot(ep.ending.shot, "remate")
    for ev in ep.ending.events:
        check_event(ev, actors, "remate", None)
    if ep.counter and not any(ev.type == "count" for b in ep.beats for ev in b.events):
        out.append(Issue("AVISO", "contador", "hay contador pero ningún evento «count» lo mueve"))
    if not ep.post.strip():
        out.append(Issue("AVISO", "post", "falta el texto del post (una frase que abre la historia + una petición sobre quien lo ve)"))
    if ep.beats[0].shot and not ep.beats[0].shot.actors and not ep.title_card:
        out.append(Issue("AVISO", "beat 1", "el fotograma 0 no tiene ni actores ni cartel: ¿qué para el scroll?"))

    est = total_chars / CHARS_PER_SECOND / max(1.0, ep.pace.tempo / 1.1) + ep.ending.seconds
    voice_json = episode_dir(slug) / "voice.json"
    if voice and voice_json.exists():
        data = json.loads(voice_json.read_text(encoding="utf-8"))
        said = {w["beat"] for t in data.get("takes", []) for w in t.get("words", [])}
        lost = [b.id for b in ep.beats if b.id not in said]
        if lost:
            out.append(Issue("ERROR", "voz", f"los beats {lost} no tienen voz (¿cambiaste el guion?): `reels voice {slug}` (lo que no cambió sale de la caché)"))
        for t in data.get("takes", []):
            if t.get("similarity") is not None and t["similarity"] < 0.6:
                out.append(Issue("AVISO", "voz", f"la toma {t['take']} (beats {t['beats']}) no dice bien su texto ({t['similarity']:.2f}): escúchala"))
        est = sum(t["duration"] for t in data.get("takes", [])) + ep.ending.seconds
    real = voice and voice_json.exists()
    out.append(Issue("INFO", "duración", f"{'dura' if real else 'unos'} {est:.1f} s ({'con las voces de verdad' if real else 'estimado por el texto'})"))
    if ep.music and real:
        track = ASSETS / "music" / ep.music.track
        secs = _track_seconds(track)
        if secs and secs < est and not ep.music.loop:
            out.append(Issue("AVISO", "música", f"la pista dura {secs:.0f} s y el reel {est:.0f} s: el final quedaría sin música (pon \"loop\": true o compón una más larga)"))
    if slug == "humo":
        return out
    if est > 45:
        out.append(Issue("AVISO", "duración", f"{est:.0f} s: este formato funciona entre 20 y 45 s (quita una frase o un peldaño)"))
    elif est < 20:
        out.append(Issue("AVISO", "duración", f"{est:.0f} s: corto para contar una escalera de tres (este formato va de 20 a 45 s)"))
    return out


def _track_seconds(path: Path) -> float | None:
    import subprocess

    from reels import system

    if not path.exists():
        return None
    try:
        r = subprocess.run([system.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        return float(r.stdout.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
