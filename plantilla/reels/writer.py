"""Script generation with Claude: topic -> validated Episode (script.json)."""

from __future__ import annotations

import json
import os
import re

import anthropic
from pydantic import ValidationError
from rich.console import Console

from reels import cost
from reels.assets import ROOT, character, episode_dir
from reels import cast
from reels.schema import OFFSCREEN, Action, Camera, Character, Emotion, Episode, Sfx

# Optional "hands-free" writer (pay-per-use API). The factory normally writes scripts inside Claude Code.
MODEL = os.environ.get("REELS_SCRIPT_MODEL", "claude-opus-5-5")
MAX_ATTEMPTS = 3
SECONDS_PER_BEAT = 2.2

console = Console()


def _system_prompt() -> str:
    guide = (ROOT / "style/guide.md").read_text(encoding="utf-8")
    bible = (ROOT / "style/characters.md").read_text(encoding="utf-8")
    lessons_path = ROOT / "style/lessons.md"
    lessons = lessons_path.read_text(encoding="utf-8") if lessons_path.exists() else ""
    patterns = (ROOT / "references/patterns.md").read_text(encoding="utf-8")
    # Single source of truth shared with humans and new chats: what every field does and what works.
    pieces = (ROOT / "docs/piezas.md").read_text(encoding="utf-8")
    works = (ROOT / "docs/lo-que-funciona.md").read_text(encoding="utf-8")

    per_char = "\n".join(
        f"- {c.value}: acciones permitidas = {', '.join(character(c.value)['actions'])}" for c in Character
    )
    brand = json.loads((ROOT / "assets/brand/brand.json").read_text(encoding="utf-8"))
    handle = brand.get("handle") or "la cuenta"
    topic = brand.get("tema") or "historias cortas con humor y emoción"
    return f"""Eres guionista de reels verticales en español para @{handle.lstrip('@')}: {topic}.
Serie animada en 3D low-poly. Cada beat es un plano con una frase.

{works}

(La guía de estilo de abajo nació para comedia: si choca con «Lo que funciona», manda «Lo que funciona».)

{guide}

{bible}

{lessons}

## Patrones de reels de referencia (contexto obligatorio: extrae patrones, nunca copies guiones)
{patterns}

## Estructura por tono (`tone`)
- comedia: gancho → escalada → remate con dato o escalada visible → frase seca → reacción muda.
- agridulce: arranque cómico → la IA muestra algo humano (celos, apego, miedo a ser sustituida) → confesión vulnerable → resolución tierna del humano → chiste final pequeño que rompe la tensión → reacción muda. Beats más largos y más silencios.
- serie: como comedia, pero acaba en cliffhanger y rellena `series` (name, part).

## Dirección de voz (`delivery`): la voz es la mitad de la actuación
- Cada beat con frase lleva `delivery`: `tags` (0–2 audio tags compatibles), `pace`, `pause_before` (segundos de silencio antes de la frase, se respeta en el montaje) e `intensity`.
- Escribe con puntuación de actor: "…" para un parón ("…Oh."), "—" para cortar ("No, no es— vale."), frases a medias.
- Muletillas naturales de España ("a ver", "bueno", "o sea", "vale") con moderación.
- Tags: susurro + curioso sí; susurro + emocionado no. No abuses: muchas frases van sin tags.
- Las voces se generan como una conversación entera, así que el ritmo natural ya sale del audio: usa `hold` corto (0–0.3) en las frases y reserva los silencios largos para `pause_before` y los beats mudos.

## Beats mudos
- Un beat con `speaker` y `line` null y sin `event` es una reacción muda: la cara de `reactor` procesando lo que ha pasado. `hold` entre 1 y 2 s.
- El episodio SIEMPRE termina con un beat mudo de reacción (normalmente primer plano del novato procesando).

## Lo que existe en los assets (enums cerrados; no uses otros valores)
- emotion / listener_emotion: {', '.join(e.value for e in Emotion)}
- action: {', '.join(a.value for a in Action)}
{per_char}
- camera: {', '.join(c.value for c in Camera)}
- sfx: {', '.join(s.value for s in Sfx)}.

## Catálogo de piezas (qué hace cada campo, cuándo usarlo y sus trampas)
{pieces}

## Formato
- `hold`: segundos de silencio tras la frase (0.1 en frases normales; más en beats mudos y antes de lo que pesa).
- No escribas duraciones: se calculan desde el audio.
- `slug`: kebab-case ascii corto.
"""


def _extra_checks(ep: Episode) -> list[str]:
    errors = []
    for b in ep.beats:
        if b.speaker is not None:
            allowed = character(b.speaker.value)["actions"]
            if b.action.value not in allowed:
                errors.append(f"beat {b.id}: {b.speaker.value} no soporta la acción {b.action.value} (permitidas: {allowed})")
        if b.speaker in OFFSCREEN and b.camera not in (Camera.phone_closeup, Camera.closeup_novato):
            errors.append(f"beat {b.id}: {b.speaker.value} está fuera de cámara; usa phone_closeup o closeup_novato")
        if b.camera == Camera.closeup_ai and not any(cast.kind_of(cast.player(c.value)) == "cosa" for c in ep.characters):
            errors.append(f"beat {b.id}: closeup_ai sin IA en el reparto")
    return errors


def write_script(topic: str, duration: float = 20.0, tone: str | None = None) -> tuple[Episode, float]:
    """Return a validated episode and its cost in USD."""
    n_lo = max(5, int(duration / SECONDS_PER_BEAT) - 1)
    n_hi = n_lo + 3
    tone_line = f"Tono: {tone}.\n" if tone else "Elige el tono que mejor le vaya al tema.\n"
    user = (
        f"Tema: {topic}\n{tone_line}\n"
        f"Duración objetivo: unos {duration:.0f} segundos, entre {n_lo} y {n_hi} beats. "
        "Escribe el guion completo."
    )
    # The full Episode schema is too large for a structured-output grammar, so the schema
    # goes in the prompt and Pydantic validates; errors are fed back on retry.
    schema = json.dumps(Episode.model_json_schema(), ensure_ascii=False)
    system = (
        _system_prompt()
        + "\n## Salida\nResponde SOLO con un objeto JSON válido (sin texto alrededor ni ```) que cumpla este JSON Schema:\n"
        + schema
    )
    client = anthropic.Anthropic()
    feedback = ""
    usd = 0.0
    errors: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        console.print(f"[dim]writer: intento {attempt}…[/]")
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=32000,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=system,
            messages=[{"role": "user", "content": user + feedback}],
        ) as stream:
            response = stream.get_final_message()
        usd += cost.claude_usd(MODEL, response.usage.input_tokens, response.usage.output_tokens)
        if response.stop_reason == "refusal":
            raise RuntimeError(f"Claude rechazó el guion: {response.stop_details}")
        text = "".join(b.text for b in response.content if b.type == "text")
        match = re.search(r"\{.*\}", text, re.S)
        try:
            episode = Episode.model_validate_json(match.group(0) if match else text)
        except ValidationError as e:
            errors = [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]
        else:
            errors = _extra_checks(episode)
            if not errors:
                return episode, usd
        feedback = "\n\nEl intento anterior no valía por estos errores, corrígelos:\n- " + "\n- ".join(errors[:20])
        console.print(f"[yellow]writer: {len(errors)} error(es), reintento[/]")
    raise RuntimeError(f"el guion no pasó la validación tras {MAX_ATTEMPTS} intentos: {errors}")


def save(episode: Episode, usd: float) -> None:
    out = episode_dir(episode.slug)
    out.mkdir(parents=True, exist_ok=True)
    (out / "script.json").write_text(
        json.dumps(episode.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    , encoding="utf-8")
    cost.log(out, "script", usd, model=MODEL)
