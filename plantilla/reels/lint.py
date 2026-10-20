"""Free, deterministic checks on an episode before spending money (voices, renders).

Every rule here comes from a real mistake or from a real account's data (craft rules to start with; tune them
with your own data in docs/lo-que-funciona.md).
ERROR blocks the next paid step; AVISO is shown at the next gate with its reason.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from reels.assets import episode_dir, published
from reels.schema import Episode

TARGET_S = (25.0, 40.0)  # watch time sits at 21-32 s whatever the length; 60 s reels lose half before the end
MAX_FIRST_SPEECH_S = 0.5  # reels with a voice on frame 0 lose 31-33 % in <3 s; a silent opener lost 48 %
MAX_FIRST_SPEECH_S_SCREEN = 2.5  # ...unless frame 0 is a screen that reads on its own
WORDS_PER_S = 2.6  # Spanish at our pace, used only before the voices exist
SHOT_AVG_S = 1.8  # H12: reels cutting every 1.6-1.8 s were watched at 66-68 %; 2.9-3.2 s, at 38-45 %
SHOT_MAX_S = 4.0
MIN_WORDS_PER_S = 2.0

# Fine in Spain, rude or odd in Mexico/Colombia/Argentina (>50 % of the audience).
LATAM = {
    r"\bcog(?:e|er|es|en|emos|í|ió|iste|ieron|ido|iendo|erlo|erla|elo|ela)\b|\bcoj(?:o|a|as|an)\b": "coger (agarrar, tomar, lo contrataron)",
    r"\bpill(?:a|ar|as|an|o|é|ó|aste|aron|ado|ada)\b": "pillar (agarrar, descubrir, enterarse)",
    r"\bconcha\b": "concha",
    r"\bchaqueta\b": "chaqueta (chamarra, sudadera)",
    r"\bpija\b": "pija (en Argentina es vulgar)",
    r"\bpolla\b": "polla",
    r"\bbicho\b": "bicho",
    r"\bcajeta\b": "cajeta",
    r"\bcorr(?:erse|erme|erte|o|e)\b": "correrse",
    r"\bpaja\b": "paja",
    r"\bgilipollas\b": "gilipollas (no se entiende fuera de España)",
    r"\bhostia\b": "hostia",
}

# Sounds written, translated or formal: people do not talk like this.
WRITTEN = {
    r"\ba diario\b": "«todos los días»",
    r"\bhonestamente\b": "«la verdad»",
    r"\bseguramente\b": "«seguro», «fijo»",
    r"\bun honor\b": "calco del inglés: «me lo he pasado muy bien contigo»",
    r"\bsin embargo\b": "«pero»",
    r"\bpor lo tanto\b": "«así que»",
    r"\ben efecto\b": "«ya», «claro»",
    r"\bno obstante\b": "«pero»",
    r"\btiene sentido\b": "calco de «makes sense»: «cuadra», «normal»",
    r"\bdefinitivamente\b": "calco de «definitely»: «sin duda», «claro»",
    r"\baplicar a\b": "calco: «presentarse a», «echar el CV»",
}
# Simple future ("te quedarás") is written Spanish; spoken is "te vas a quedar".
FUTURE = re.compile(r"\b\w{2,}(?:ré|rás|rá|réis|rán)\b", re.IGNORECASE)
NOT_FUTURE = {"atrás", "detrás", "jamás", "quizá", "será"}  # "será" stays: "será posible" is spoken

BRANDS = re.compile(r"\b(instagram|netflix|whatsapp|google|gmail|facebook|tiktok|spotify|amazon|apple|iphone|"
                    r"microsoft|github|slack|discord|twitter|youtube|openai|anthropic|visa|mastercard)\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
LAPTOP_SCREENS = {"MemorySave", "DateGlitch", "SystemNotice"}  # their font has no emoji glyphs


@dataclass
class Issue:
    level: str  # ERROR | AVISO
    where: str
    msg: str


def lint(slug: str) -> list[Issue]:
    out = episode_dir(slug)
    ep = Episode.model_validate_json((out / "script.json").read_text(encoding="utf-8"))
    issues: list[Issue] = []
    add = lambda level, where, msg: issues.append(Issue(level, where, msg))  # noqa: E731

    # --- Opening: a voice on frame 0, readable on a phone.
    first = ep.beats[0]
    if not first.line and not first.event:
        add("ERROR", f"beat {first.id}", "ni voz ni pantalla legible en el fotograma 0 (un reel que abrió así perdió al 48 % en <3 s)")
    elif not first.line:
        add("AVISO", f"beat {first.id}", "abre con pantalla muda: tiene que entenderse sin sonido en 1 s")
    elif first.delivery and first.delivery.pause_before > 0:
        add("ERROR", f"beat {first.id}", f"pause_before {first.delivery.pause_before} s en la primera frase")
    if first.camera.value in {"establishing", "wide_space", "wide_epic", "mundo_wide"}:
        add("AVISO", f"beat {first.id}", f"abre con plano general ({first.camera.value}): en el móvil no se lee nada")

    # --- Lines: natural, short, safe across the Spanish-speaking world.
    pauses = 0
    for b in ep.beats:
        if text := b.line:
            where = f"beat {b.id}"
            low = text.lower()
            n = len(text.split())
            if n > 8:
                add("AVISO", where, f"{n} palabras: «{text}»")
            for pat, why in LATAM.items():
                if re.search(pat, low):
                    add("ERROR", where, f"doble sentido en LatAm: {why} — «{text}»")
            for pat, why in WRITTEN.items():
                if re.search(pat, low):
                    add("AVISO", where, f"suena escrito, mejor {why} — «{text}»")
            for m in FUTURE.finditer(low):
                if m.group(0) not in NOT_FUTURE:
                    add("AVISO", where, f"futuro de libro «{m.group(0)}»: en hablado, «vas a …» — «{text}»")
            if re.search(r"\d", text) and not (b.delivery and b.delivery.spoken):
                add("AVISO", where, f"cifras en la frase: escríbelas como se dicen o usa delivery.spoken — «{text}»")
            d = b.delivery
            if d and d.max_gap:
                add("AVISO", where, "max_gap recorta la toma después de generarla: mejor comas en spoken (v4 para en cada punto)")
            if d and d.spoken and d.pace != "normal" and not re.search(r"rush|fast|quick|brisk|slow", d.spoken, re.I):
                add("AVISO", where, f"pace «{d.pace}» no llega a la voz con spoken: escríbelo dentro ([rushed] / [slowly])")
        if b.delivery and b.delivery.pause_before >= 0.6:
            pauses += 1
    if pauses > 3:
        add("AVISO", "guion", f"{pauses} pausas largas: si todo lleva pausa, ninguna pesa (guía 12)")

    # --- Screens: invented brands, no emojis on laptop fonts.
    for b in ep.beats:
        if not b.event:
            continue
        props = json.dumps(b.event.props.model_dump(), ensure_ascii=False)
        for m in set(BRANDS.findall(props)):
            add("AVISO", f"beat {b.id}", f"marca real en pantalla ({m}): usa una inventada")
        if b.event.component in LAPTOP_SCREENS and EMOJI.search(props):
            add("ERROR", f"beat {b.id}", f"emoji en {b.event.component}: la fuente del portátil lo pinta como un cuadrado")

    # --- Length: measured once the voices exist, estimated before.
    timeline = out / "timeline.json"
    if timeline.exists():
        tl = json.loads(timeline.read_text(encoding="utf-8"))
        dur = tl["duration"]
        spoken = [b for b in tl["beats"] if b["line"]]
        if spoken:
            t0 = spoken[0]["start_frame"] / tl["fps"] + _leading_silence(out, spoken[0]["id"])
            if first.event and t0 <= MAX_FIRST_SPEECH_S_SCREEN:
                pass  # a readable screen carries the opening (modelo-retirado: voice at 1.9 s, 34 % skip)
            elif first.event:
                add("ERROR", "audio", f"la primera voz entra en el segundo {t0:.1f}: ni una pantalla aguanta tanto "
                    "(un arranque mudo de 5,5 s perdió al 48 % en <3 s)")
            elif t0 > MAX_FIRST_SPEECH_S:
                add("ERROR", "audio", f"la primera voz entra en el segundo {t0:.1f}: tiene que sonar en el fotograma 0")
        label = "medido"
        _pace(tl, out, add)
    else:
        words = sum(len(b.line.split()) for b in ep.beats if b.line)
        silent = sum(1 for b in ep.beats if not b.line)
        dur = words / WORDS_PER_S + sum(b.hold for b in ep.beats) + silent * 1.2 + sum(
            b.delivery.pause_before for b in ep.beats if b.delivery)
        label = "estimado"
    if dur > TARGET_S[1] + 5:
        add("ERROR", "duración", f"{dur:.0f} s ({label}): por encima de ~45 s se pierde a la mitad antes del final")
    elif dur > TARGET_S[1]:
        add("AVISO", "duración", f"{dur:.0f} s ({label}): el objetivo es {TARGET_S[0]:.0f}–{TARGET_S[1]:.0f} s")

    # --- Cast: every speaker needs a voice before `reels voice` (new characters start without one).
    from reels import cast as cast_mod
    from reels.assets import character

    for c in sorted({b.speaker.value for b in ep.beats if b.speaker is not None}):
        if not (character(c).get("voice") or {}).get("voice_id"):
            who = cast_mod.player(c)
            add("AVISO", "reparto", f"«{who}» no tiene voz todavía: pon un voice_id de ElevenLabs en su personaje.json "
                                    "antes de `reels voice` (las voces ya grabadas, como en los ejemplos, no la necesitan)")

    # --- Learning: every reel tests something.
    if not ep.tests:
        add("AVISO", "guion", "sin `tests`: ¿qué hipótesis de docs/hipotesis.md prueba este reel?")

    # --- Post text, once it exists.
    post = published(slug, ".txt")
    if post.exists():
        text = post.read_text(encoding="utf-8")
        body = text.split("Música:")[0]
        if "?" not in body and "envía" not in body.lower():
            add("AVISO", "post", "el texto no pide nada (una pregunta sobre el espectador o «envíaselo a…»)")
        if ep.music and "Música:" not in text:
            add("ERROR", "post", "falta el crédito de la música")
    return issues


def _pace(tl: dict, out, add) -> None:
    """H12: a new shot every ~1.5 s, none held >4 s, voice at >=2 words/s (cutting every 1.6-1.8 s: 66-68 % watched)."""
    fps = tl["fps"]
    shots: list[list] = []  # [camera, seconds, first beat id]
    for b in tl["beats"]:
        secs = (b["end_frame"] - b["start_frame"]) / fps
        parts = [(b["camera"], secs)]
        if b.get("cut_camera") and b.get("cut_at") is not None:
            parts = [(b["camera"], b["cut_at"]), (b["cut_camera"], secs - b["cut_at"])]
        for camera, s in parts:
            if shots and shots[-1][0] == camera:
                shots[-1][1] += s
            else:
                shots.append([camera, s, b["id"]])
    avg = tl["duration"] / len(shots)
    if avg > SHOT_AVG_S:
        add("AVISO", "ritmo", f"un plano cada {avg:.1f} s de media: el objetivo es ~{SHOT_AVG_S:.1f} s")
    for camera, secs, beat in shots:
        if secs > SHOT_MAX_S:
            add("AVISO", f"beat {beat}", f"plano de {secs:.1f} s seguidos ({camera}): córtalo o que pase algo dentro")
    words = sum(len(json.loads(p.read_text(encoding="utf-8")).get("words", []))
                for b in tl["beats"] if b["line"] and (p := out / "audio" / f"beat_{b['id']:02d}.json").exists())
    if words and words / tl["duration"] < MIN_WORDS_PER_S:
        add("AVISO", "ritmo", f"{words / tl['duration']:.1f} palabras/s: por debajo de {MIN_WORDS_PER_S} el vídeo se siente lento")


def _leading_silence(out, beat_id: int) -> float:
    """Seconds before the first word of a beat, from its whisper word timings when we have them."""
    words = out / "audio" / f"beat_{beat_id:02d}.json"
    if not words.exists():
        return 0.0
    data = json.loads(words.read_text(encoding="utf-8"))
    first = next((w for w in data.get("words", []) if w.get("start") is not None), None)
    return float(first["start"]) if first else 0.0
