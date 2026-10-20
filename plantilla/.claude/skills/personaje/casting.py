"""Casting de voz por la API de ElevenLabs: buscar en la biblioteca pública, probar las 6 frases, saldo.

    uv run python .claude/skills/personaje/casting.py saldo
    uv run python .claude/skills/personaje/casting.py buscar --genero male --acento "latin american" [--edad middle_aged] [--texto calida]
    uv run python .claude/skills/personaje/casting.py estimar <personaje> <n_voces>
    uv run python .claude/skills/personaje/casting.py probar <personaje> <voice_id> [<voice_id> ...]
    uv run python .claude/skills/personaje/casting.py medir <personaje>

`buscar` es gratis (y guarda las candidatas en personajes/<id>/casting/candidatas.json al probar). `probar` CUESTA:
añade cada voz a "My Voices" (gratis) y dice las 6 frases de personajes/<id>/casting.md (sección "## Frases", una
por línea "1. ...") con el modelo v4; deja los mp3 en personajes/<id>/casting/<voz>/ y uno seguido (todas.mp3)
para escucharlas de un tirón. Lo ya generado no se vuelve a cobrar. `medir` (gratis) saca tono, ritmo y si se
entiende cada frase (whisper), para comparar candidatas con números además de con el oído.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_v4"
CREDITS_PER_CHAR = 0.45  # v4, medido en la cuenta del curso (oct. 2026); `saldo` antes y después da la cifra real


def hazlo_en_la_web(motivo: str) -> str:
    """Spanish message for the student when the API route to the Voice Library is closed."""
    return (f"{motivo}\n\nNo pasa nada: haz el casting en la web de ElevenLabs, que es gratis.\n"
            "  1. Entra en elevenlabs.io → Voices → Voice Library y escucha voces (filtra por idioma, acento y edad).\n"
            "  2. Elige la que te guste y pulsa «Add to My Voices». Copia su voice_id (menú de la voz → Copy voice ID).\n"
            "  3. Vuelve aquí y dile a Claude: «guarda esta voz para <personaje>: <voice_id>». La fábrica la apunta en\n"
            "     personajes/<id>/personaje.json (voice.voice_id y voice.name) y ya está lista para narrar.")


def _key() -> str:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit(hazlo_en_la_web("Aún no hay clave de ElevenLabs en .env (ELEVENLABS_API_KEY)."))
    return key


def _plan_sin_biblioteca(r) -> bool:
    """401/402/403 from ElevenLabs: key without permission or a plan that cannot use library voices through the API."""
    if r.status_code not in (401, 402, 403):
        return False
    return True


def _h() -> dict:
    return {"xi-api-key": _key()}


def saldo() -> tuple[int, int]:
    r = httpx.get(f"{API}/user/subscription", headers=_h(), timeout=30)
    r.raise_for_status()
    d = r.json()
    return d["character_count"], d["character_limit"]


def frases(char_id: str) -> list[tuple[str, str]]:
    md = (ROOT / "personajes" / char_id / "casting.md").read_text(encoding="utf-8")
    block = md.split("## Frases", 1)[1] if "## Frases" in md else md
    out = []
    for line in block.splitlines():
        m = re.match(r"^\s*\d+\.\s*(?:\*\*(.+?)\*\*\s*[:·—-]\s*)?(.+)$", line)
        if m:
            out.append(((m.group(1) or f"f{len(out) + 1}").strip().lower(), m.group(2).strip().strip("«»\"")))
        elif out and line.startswith("## "):
            break
    if len(out) < 6:
        sys.exit(f"personajes/{char_id}/casting.md: necesito 6 frases en '## Frases' (encontradas {len(out)}).")
    return out[:6]


def cmd_buscar(a) -> None:
    params = {"page_size": a.n, "language": "es"}
    for k, v in (("gender", a.genero), ("accent", a.acento), ("age", a.edad), ("search", a.texto), ("use_cases", a.uso)):
        if v:
            params[k] = v
    r = httpx.get(f"{API}/shared-voices", params=params, headers=_h(), timeout=30)
    if _plan_sin_biblioteca(r):
        sys.exit(hazlo_en_la_web("Tu cuenta de ElevenLabs no deja buscar voces de la biblioteca desde fuera de la web "
                                 f"(HTTP {r.status_code}: suele pasar con el plan gratis o con una clave sin permisos)."))
    r.raise_for_status()
    voices = r.json()["voices"]
    cache = ROOT / ".cache" / "casting-busqueda.json"
    cache.parent.mkdir(exist_ok=True)
    old = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    for v in voices:
        old[v["voice_id"]] = {k: v.get(k) for k in ("name", "accent", "locale", "gender", "age", "descriptive", "use_case",
                                                   "public_owner_id", "preview_url", "description", "cloned_by_count")}
        print(f"{v['voice_id']}  {v['name'][:44]:44}  {v.get('accent') or '':16} {v.get('locale') or '':6} {v.get('gender'):6} "
              f"{v.get('age') or '':12} {v.get('descriptive') or '':14} {v.get('use_case') or '':24} usada por {v.get('cloned_by_count')}")
    cache.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(voices)} voces (gratis). Escucha la muestra de cada una en la web o con `preview_url` de {cache.relative_to(ROOT)}.")


def cmd_estimar(a) -> None:
    chars = sum(len(t) for _, t in frases(a.personaje))
    total = chars * a.voces
    print(f"{a.voces} voces × 6 frases = {total} caracteres ≈ {total * CREDITS_PER_CHAR:.0f} créditos (v4, ~{CREDITS_PER_CHAR}/carácter)")


def _add(voice_id: str, meta: dict) -> None:
    mine = httpx.get(f"{API}/voices/{voice_id}", headers=_h(), timeout=30)
    if mine.status_code == 200:
        return
    owner = meta.get("public_owner_id")
    if not owner:
        sys.exit(f"{voice_id}: no sé de quién es; búscala antes con `buscar` (o añádela a My Voices en la web).")
    r = httpx.post(f"{API}/voices/add/{owner}/{voice_id}", headers=_h(), json={"new_name": meta.get("name", voice_id)[:40]}, timeout=30)
    if _plan_sin_biblioteca(r):
        sys.exit(hazlo_en_la_web(f"Tu plan de ElevenLabs no deja añadir voces de la biblioteca desde fuera de la web (HTTP {r.status_code})."))
    if r.status_code not in (200, 201):
        sys.exit(f"No he podido añadir {voice_id} a My Voices: HTTP {r.status_code} {r.text[:200]}")


def cmd_probar(a) -> None:
    from reels import system

    lines = frases(a.personaje)
    cache = ROOT / ".cache" / "casting-busqueda.json"
    found = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    out_root = ROOT / "personajes" / a.personaje / "casting"
    before, limit = saldo()
    print(f"saldo antes: {limit - before} créditos libres ({before} usados de {limit})")
    chosen = {}
    for vid in a.voces:
        meta = found.get(vid, {"name": vid})
        _add(vid, meta)
        slug = re.sub(r"[^a-z0-9]+", "-", meta.get("name", vid).split(" - ")[0].lower()).strip("-") or vid
        folder = out_root / slug
        folder.mkdir(parents=True, exist_ok=True)
        parts = []
        for n, (reg, text) in enumerate(lines, 1):
            mp3 = folder / f"{n}-{reg}.mp3"
            if not mp3.exists():
                r = httpx.post(f"{API}/text-to-speech/{vid}", params={"output_format": "mp3_44100_128"}, headers=_h(), timeout=120,
                               json={"text": text, "model_id": MODEL, "language_code": "es", "seed": 1,
                                     "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}})
                if r.status_code != 200:
                    sys.exit(f"ElevenLabs HTTP {r.status_code}: {r.text[:300]}")
                mp3.write_bytes(r.content)
            parts.append(mp3)
        lst = folder / "lista.txt"
        lst.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
        subprocess.run([system.ffmpeg(), "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-af", "apad=pad_dur=0.6",
                        str(folder / "todas.mp3")], check=False)
        chosen[vid] = {**meta, "carpeta": str(folder.relative_to(ROOT))}
        print(f"✔ {meta.get('name', vid)} → {folder.relative_to(ROOT)}/ (6 frases + todas.mp3)")
    (out_root / "candidatas.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=1), encoding="utf-8")
    after, _ = saldo()
    print(f"saldo después: {limit - after} créditos libres · este casting ha gastado {after - before} créditos")


def cmd_medir(a) -> None:
    from reels import system, voice

    out_root = ROOT / "personajes" / a.personaje / "casting"
    expected = dict(frases(a.personaje))
    for folder in sorted(p for p in out_root.iterdir() if p.is_dir()):
        rows = []
        for mp3 in sorted(folder.glob("[0-9]-*.mp3")):
            reg = mp3.stem.split("-", 1)[1]
            text = expected.get(reg, "")
            f0 = subprocess.run([system.ffmpeg(), "-v", "error", "-i", str(mp3), "-af", "aresample=16000", "-f", "f32le", "-ac", "1", "-"],
                                capture_output=True).stdout
            import numpy as np

            x = np.frombuffer(f0, np.float32)
            pitch = _median_pitch(x, 16000)
            dur = len(x) / 16000
            words = len(text.split())
            sc = voice.score_take(mp3, text) if text else {"heard": "", "similarity": 0}
            heard, ok = sc["heard"], sc["similarity"]
            rows.append(f"  {reg:10} {dur:4.1f} s · {words / dur * 60 if dur else 0:5.0f} pal/min · tono {pitch:5.0f} Hz · "
                        f"se entiende {ok:.2f} · oye «{heard[:50]}»")
        print(folder.name)
        print("\n".join(rows))


def _median_pitch(x, sr: int) -> float:
    """Median F0 by autocorrelation over voiced 40 ms frames (60–400 Hz)."""
    import numpy as np

    n = int(0.04 * sr)
    f0s = []
    for i in range(0, len(x) - n, n // 2):
        fr = x[i:i + n] - x[i:i + n].mean()
        if np.sqrt((fr ** 2).mean()) < 0.02:
            continue
        ac = np.correlate(fr, fr, "full")[n - 1:]
        lo, hi = sr // 400, sr // 60
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.3 * ac[0]:
            f0s.append(sr / k)
    return float(np.median(f0s)) if f0s else 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("saldo")
    b = sub.add_parser("buscar")
    b.add_argument("--genero", choices=["male", "female", "neutral"])
    b.add_argument("--acento", help='p. ej. "latin american", "mexican", "colombian", "argentine", "peninsular"')
    b.add_argument("--edad", choices=["young", "middle_aged", "old"])
    b.add_argument("--texto", help="palabras de la ficha: calida, seca, grave...")
    b.add_argument("--uso", help="conversational, narrative_story, characters_animation...")
    b.add_argument("-n", type=int, default=15)
    e = sub.add_parser("estimar")
    e.add_argument("personaje")
    e.add_argument("voces", type=int)
    p = sub.add_parser("probar")
    p.add_argument("personaje")
    p.add_argument("voces", nargs="+")
    m = sub.add_parser("medir")
    m.add_argument("personaje")
    a = ap.parse_args()
    if a.cmd == "saldo":
        used, limit = saldo()
        print(f"{limit - used} créditos libres ({used} usados de {limit})")
    else:
        {"buscar": cmd_buscar, "estimar": cmd_estimar, "probar": cmd_probar, "medir": cmd_medir}[a.cmd](a)


if __name__ == "__main__":
    main()
