"""Single entry point of the 2D factory: `uv run reels <command>` (the same names as the 3D one where they mean the same)."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markup import escape

from reels import system
from reels.assets import ROOT, episode_dir

console = Console()
app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """La fábrica 2D: de un guion (script.json) a un reel «¿Y si…?» dibujado por código."""
    system.setup_console()
    system.setup_path()
    load_dotenv(ROOT / ".env")


def _load(slug: str):
    from reels.schema import Episode

    path = episode_dir(slug) / "script.json"
    if not path.exists():
        console.print(f"[red bold]✘ no existe episodes/{slug}/script.json[/]")
        raise typer.Exit(1)
    return Episode.model_validate_json(path.read_text(encoding="utf-8"))


def _fail(what: str, e: Exception) -> None:
    console.print(f"[red bold]✘ {what}:[/] {escape(str(e))}")
    raise typer.Exit(1)


# --- revision and first steps ---------------------------------------------------------------------------------------


@app.command()
def doctor(
    skip_api: bool = typer.Option(False, "--skip-api", help="No comprobar las claves (sin internet)."),
    as_json: bool = typer.Option(False, "--json", help="Salida en JSON (para el instalador y la CI)."),
) -> None:
    """¿Está todo instalado? Revisa cada pieza y, si falta algo, te dice cómo arreglarlo en tu sistema."""
    from reels import doctor as doctor_mod

    if not doctor_mod.run(skip_api=skip_api, as_json=as_json):
        raise typer.Exit(1)


@app.command()
def humo(
    comprobar: bool = typer.Option(True, "--comprobar/--sin-comprobar", help="Re-escuchar el vídeo con whisper al final."),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir", help="Abrir el vídeo al terminar."),
) -> None:
    """Prueba de humo GRATIS: un reel de unos 6 s de punta a punta, con una voz ya grabada (sin cuentas ni claves)."""
    from reels import ejemplos

    try:
        final = ejemplos.run("humo", ROOT / "assets" / "humo", check=comprobar, listen=comprobar)
    except Exception as e:  # noqa: BLE001  one plain message for a first-time user (details in the logs)
        console.print(f"[red bold]✘ la prueba de humo ha fallado:[/] {escape(str(e))}")
        console.print("  Ejecuta `uv run reels doctor`: casi siempre es una pieza sin instalar.")
        raise typer.Exit(1)
    console.print(f"[green bold]✔ ¡La fábrica 2D funciona![/] Tu primer vídeo: {final}")
    if abrir:
        system.open_path(final)


@app.command()
def ejemplo(
    nombre: str = typer.Argument(None, help="quijote-gafas (sin nombre: la lista)"),
    fotogramas: bool = typer.Option(False, "--fotogramas", help="Solo los fotogramas clave (más rápido), sin vídeo."),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir"),
) -> None:
    """Hace un episodio de ejemplo que viene con la fábrica, con sus voces ya grabadas: GRATIS."""
    from reels import ejemplos

    if not nombre:
        console.print("Ejemplos: " + ", ".join(ejemplos.available()))
        return
    try:
        result = ejemplos.run(nombre, video=not fotogramas)
    except Exception as e:  # noqa: BLE001
        _fail("el ejemplo ha fallado", e)
    console.print(f"[green bold]✔ listo:[/] {result}")
    if abrir:
        system.open_path(result)


@app.command("descargar-modelo")
def descargar_modelo() -> None:
    """Descarga el modelo de whisper (el «oído» de la fábrica, ~470 MB) a models/."""
    dest = system.whisper_model()
    if dest.exists() and dest.stat().st_size > 100e6:
        console.print(f"[green]✔[/] ya está: {dest}")
        return
    system.download(system.WHISPER_MODEL_URL, dest)
    console.print(f"[green]✔[/] {dest}")


@app.command()
def lint(slug: str) -> None:
    """Revisión gratis del guion (y de la voz si ya existe) antes de gastar: sale con error si algo bloquea."""
    from reels.lint import lint as run_lint

    issues = run_lint(slug)
    for i in issues:
        color = "red" if i.level == "ERROR" else "yellow" if i.level == "AVISO" else "cyan"
        console.print(f"[{color}]{i.level:<5}[/] [dim]{i.where:<9}[/] {escape(i.msg)}")
    errors = sum(i.level == "ERROR" for i in issues)
    if errors:
        console.print(f"[red bold]✘ {errors} errores: arréglalos antes del siguiente paso[/]")
        raise typer.Exit(1)
    console.print(f"[green bold]✔ sin errores[/] ({sum(i.level == 'AVISO' for i in issues)} avisos)")


# --- voice (costs) ----------------------------------------------------------------------------------------------------


@app.command()
def voice(
    slug: str,
    estimar: bool = typer.Option(False, "--estimar", help="Solo cuánto costaría (no gasta nada)."),
    sin_oido: bool = typer.Option(False, "--sin-oido", help="No re-escuchar las tomas con whisper."),
) -> None:
    """Voces del episodio con ElevenLabs (lo que ya está en la caché no se vuelve a pagar). CUESTA créditos."""
    from reels import voice as voice_mod

    ep = _load(slug)
    try:
        est = voice_mod.estimate(ep)
    except Exception as e:  # noqa: BLE001
        _fail("no puedo preparar las voces", e)
    if estimar:
        console.print(json.dumps(est, ensure_ascii=False))
        console.print(f"Nuevas: {est['characters_new']} caracteres → como mucho {est['credits_max']} créditos "
                      f"(lo normal, ~{est['credits_likely']}). En caché (gratis): {est['characters_cached']} caracteres.")
        return
    try:
        result = voice_mod.voice_episode(ep, listen=not sin_oido)
    except Exception as e:  # noqa: BLE001
        _fail("las voces han fallado", e)
    console.print(f"[green bold]✔ voces listas[/]: {result['credits']} créditos nuevos de ElevenLabs")


# --- drawing (free, local) --------------------------------------------------------------------------------------------


@app.command()
def build(slug: str) -> None:
    """Tiempos del reel (cada evento en su palabra) → episodes/<slug>/timeline.json. Gratis."""
    from reels import timeline
    from reels.voice import ensure_voice

    try:
        ep = _load(slug)
        ensure_voice(ep)
        tl = timeline.save(ep)
    except Exception as e:  # noqa: BLE001
        _fail("no he podido montar los tiempos", e)
    console.print(f"[green]✔[/] {tl['frames'] / tl['fps']:.1f} s · {len(tl['shots'])} planos · {len(tl['events'])} eventos")


@app.command()
def stills(
    slug: str,
    frames: str = typer.Option("", "--frames", help="Fotogramas concretos, p. ej. 0,45,120 (por defecto, los clave)."),
    sin_voz: bool = typer.Option(False, "--sin-voz", help="Boceto ANTES de pagar las voces: tiempos estimados por el texto."),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir"),
) -> None:
    """Fotogramas clave (uno por plano y por beat) y una hoja con todos: para revisar el dibujo antes del vídeo. Gratis."""
    from reels import render, timeline
    from reels.voice import ensure_voice

    try:
        ep = _load(slug)
        if sin_voz:
            timeline.save(ep, estimated=True)
        else:
            ensure_voice(ep)
            timeline.save(ep)
        sheet, imgs = render.stills(slug, [int(x) for x in frames.split(",")] if frames else None)
    except Exception as e:  # noqa: BLE001
        _fail("los fotogramas han fallado", e)
    console.print(f"[green]✔[/] {len(imgs)} fotogramas en {sheet.parent} · hoja: {sheet}")
    if abrir:
        system.open_path(sheet)


@app.command()
def render(
    slug: str,
    borrador: bool = typer.Option(False, "--borrador", help="A media resolución (más rápido): borrador.mp4."),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir"),
) -> None:
    """El reel entero con voces, música y efectos → episodes/<slug>/final.mp4 (a -14 LUFS). Gratis, en tu computadora."""
    from reels import render as render_mod
    from reels import timeline
    from reels.voice import ensure_voice

    try:
        ep = _load(slug)
        ensure_voice(ep)
        timeline.save(ep)
        final = render_mod.render_video(slug, draft=borrador)
    except Exception as e:  # noqa: BLE001
        _fail("el vídeo ha fallado", e)
    console.print(f"[green bold]✔[/] {final}")
    if abrir:
        system.open_path(final)


@app.command()
def check(slug: str, video: str = typer.Option("final.mp4", help="final.mp4 o borrador.mp4")) -> None:
    """Comprueba con whisper que cada frase suena en su momento del vídeo."""
    from reels.check import check_sync

    try:
        ok = check_sync(slug, video)
    except Exception as e:  # noqa: BLE001
        _fail("la comprobación no ha podido hacerse", e)
    if not ok:
        raise typer.Exit(1)


@app.command()
def sheet(
    video: str = typer.Argument(..., help="Un vídeo, o un slug (usa su final.mp4)."),
    start: float = typer.Option(0.0, help="Segundo de inicio."),
    end: float = typer.Option(3.0, help="Segundo final."),
    fps: float = typer.Option(6.0, help="Fotogramas por segundo en la hoja."),
) -> None:
    """Hoja de fotogramas de un tramo del vídeo (para juzgar movimiento y ritmo)."""
    from reels import render as render_mod

    src = Path(video) if Path(video).exists() else episode_dir(video) / "final.mp4"
    dest = src.parent / f"hoja_{start:g}-{end:g}.jpg"
    try:
        render_mod.video_sheet(src, start, end, fps, dest)
    except Exception as e:  # noqa: BLE001
        _fail("la hoja ha fallado", e)
    console.print(f"[green]✔[/] {dest}  (de izquierda a derecha y de arriba abajo)")


@app.command()
def cover(
    slug: str,
    beat: int = typer.Option(None, help="Beat del que sale la portada (su último fotograma)."),
    segundo: float = typer.Option(None, help="O un segundo exacto del reel."),
) -> None:
    """Portada para la cuadrícula del perfil → publicar/<slug>/<slug>_portada.png."""
    from reels import render as render_mod
    from reels.assets import published

    tl = json.loads((episode_dir(slug) / "timeline.json").read_text(encoding="utf-8"))
    if segundo is not None:
        frame = int(segundo * tl["fps"])
    elif beat is not None:
        frame = next(b["to"] - 2 for b in tl["beats"] if b["id"] == beat)
    else:
        frame = tl["beats"][0]["to"] - 2
    dest = published(slug, "_portada.png")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        render_mod.cover(slug, frame, dest)
    except Exception as e:  # noqa: BLE001
        _fail("la portada ha fallado", e)
    console.print(f"[green]✔[/] {dest}")


@app.command()
def carousel(
    slug: str,
    n: int = typer.Option(6, help="Cuántas imágenes (de 2 a 10)."),
    frames: str = typer.Option("", "--frames", help="O los fotogramas exactos, p. ej. 0,80,200 (mira la hoja de stills)."),
) -> None:
    """Un carrusel de Instagram (imágenes 1080×1350) sacado del reel → publicar/<slug>/carrusel/. Gratis."""
    from reels import carousel as carousel_mod

    try:
        folder = carousel_mod.make(slug, max(2, min(10, n)), [int(x) for x in frames.split(",")] if frames else None)
    except Exception as e:  # noqa: BLE001
        _fail("el carrusel ha fallado", e)
    console.print(f"[green]✔[/] {folder}")
    system.open_path(folder)


@app.command()
def personaje(
    nombre: str = typer.Argument(..., help="Un personaje tuyo (personajes/<id>/) o una pieza (Persona, Cosa, Quijote…)."),
    episodio: str = typer.Option(None, help="Si la pieza es de un episodio: su slug."),
    escala: float = typer.Option(None, help="Tamaño en la hoja (por defecto 0.62; más pequeño para piezas muy altas)."),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir"),
) -> None:
    """Hoja del personaje GRATIS: sus expresiones y poses (o una miniatura, si es un fondo) en una imagen."""
    from reels import characters

    try:
        dest = characters.sheet(nombre, episodio, escala)
    except Exception as e:  # noqa: BLE001
        _fail("no he podido hacer la hoja", e)
    console.print(f"[green bold]✔ hoja:[/] {dest}")
    if abrir:
        system.open_path(dest)


@app.command()
def piezas(episodio: str = typer.Argument(None, help="Slug del episodio cuyas piezas compruebas (opcional).")) -> None:
    """Comprueba el código de las piezas (TypeScript) sin dibujar nada: errores con su archivo y su línea. Gratis."""
    from reels import render as render_mod

    try:
        out = render_mod.typecheck()
    except Exception as e:  # noqa: BLE001
        _fail("no he podido comprobar las piezas", e)
    if out:
        console.print(escape(out))
        console.print("[red bold]✘ hay errores en el código de las piezas[/]")
        raise typer.Exit(1)
    console.print("[green bold]✔ el código de las piezas está bien[/]" + (f" (incluidas las de {episodio})" if episodio else ""))


# --- ElevenLabs beyond the voice (they cost) ----------------------------------------------------------------------------


@app.command("voice-design")
def voice_design(
    descripcion: str = typer.Argument(..., help="Cómo es la voz, con palabras («narrador joven de España, rápido, con chispa»)."),
    texto: str = typer.Option(None, help="Lo que dicen las muestras (por defecto, una frase de «¿Y si…?»)."),
) -> None:
    """Diseña una voz nueva desde una descripción: 3 muestras para escuchar (CUESTA unos 120 créditos)."""
    from reels import voices

    try:
        page = voices.design(descripcion, texto)
    except Exception as e:  # noqa: BLE001
        _fail("el diseño de voz ha fallado", e)
    console.print(f"[green]✔[/] escucha las 3 muestras: {page}")
    system.open_path(page)


@app.command("voice-save")
def voice_save(
    muestra: int = typer.Argument(..., help="La muestra elegida (1, 2 o 3) del último diseño."),
    nombre: str = typer.Option(..., help="Nombre de la voz en tu cuenta («Narrador de la casa»)."),
    personaje_id: str = typer.Option("narrador", "--personaje", help="Personaje que la usará (personajes/<id>/)."),
) -> None:
    """Guarda la muestra elegida como voz de tu cuenta y la pone en personajes/<id>/personaje.json (gratis)."""
    from reels import voices

    try:
        path = voices.save_design(muestra, nombre, personaje_id)
    except Exception as e:  # noqa: BLE001
        _fail("no he podido guardar la voz", e)
    console.print(f"[green]✔[/] voz guardada en tu cuenta y en {path}")


@app.command("voice-search")
def voice_search(
    consulta: str = typer.Argument("narrador", help="Qué buscas («narrador», «abuelo», «niña»…)."),
    acento: str = typer.Option("", help="peninsular, mexicano, argentino… (vacío: cualquiera)."),
) -> None:
    """Busca voces en español en la biblioteca pública de ElevenLabs (gratis)."""
    from reels import voices

    try:
        for v in voices.search(consulta, acento):
            console.print(f"  {v['voice_id']}  {escape(v['name'])}  [dim]{escape(v.get('accent') or '')} · {escape(v.get('descriptive') or '')}[/]")
    except Exception as e:  # noqa: BLE001
        _fail("la búsqueda ha fallado", e)


@app.command("voice-use")
def voice_use(
    voice_id: str = typer.Argument(..., help="El voice_id de una voz de la biblioteca (de `reels voice-search`)."),
    personaje_id: str = typer.Option("narrador", "--personaje", help="Personaje que la usará (personajes/<id>/)."),
) -> None:
    """Añade una voz de la biblioteca a tus voces (gratis) y se la da a un personaje."""
    from reels import voices

    try:
        path = voices.use_library(voice_id, personaje_id)
    except Exception as e:  # noqa: BLE001
        _fail("no he podido usar esa voz", e)
    console.print(f"[green]✔[/] {path}")


@app.command("voice-try")
def voice_try(
    personaje_id: str = typer.Argument(..., help="personajes/<id>/ con su voz."),
    frase: str = typer.Option("¿Y si los gatos pudieran votar? Ganaría la siesta. Por mayoría absoluta.", help="Frase de prueba."),
) -> None:
    """Dice una frase de prueba con la voz de un personaje (CUESTA unos pocos créditos)."""
    from reels import voices

    try:
        mp3 = voices.try_voice(personaje_id, frase)
    except Exception as e:  # noqa: BLE001
        _fail("la prueba de voz ha fallado", e)
    console.print(f"[green]✔[/] {mp3}")
    system.open_path(mp3)


@app.command("voice-act")
def voice_act(
    slug: str,
    beat: int = typer.Argument(..., help="El beat cuya frase grabas tú."),
    grabacion: str = typer.Argument(..., help="Tu grabación (mp3, wav, m4a) diciendo la frase con el ritmo que quieres."),
) -> None:
    """«Actúalo tú»: tu grabación sale con la voz del personaje de ese beat (ElevenLabs, cambia voz). CUESTA."""
    from reels import voices

    try:
        out = voices.act(slug, beat, Path(grabacion))
    except Exception as e:  # noqa: BLE001
        _fail("el cambio de voz ha fallado", e)
    console.print(f"[green]✔[/] {out}")


@app.command("sfx-gen")
def sfx_gen(
    name: str = typer.Argument(..., help="Nombre del efecto (assets/sfx/<nombre>.wav)."),
    prompt: str = typer.Argument(..., help="Descripción del sonido, en inglés."),
    seconds: float = typer.Option(1.0, help="Duración en segundos."),
) -> None:
    """Genera un efecto de sonido con ElevenLabs (unos 10 créditos; se guarda en caché por descripción)."""
    from reels import sound

    try:
        console.print(f"[green]✔[/] {sound.sound_effect(name, prompt, seconds)}")
    except Exception as e:  # noqa: BLE001
        _fail("el efecto ha fallado", e)


@app.command("music-gen")
def music_gen(
    name: str = typer.Argument(..., help="Nombre de la pista (assets/music/clips/<nombre>.mp3)."),
    prompt: str = typer.Argument(..., help="Cómo es la música, en inglés (instrumentos, tempo, emoción, final)."),
    seconds: float = typer.Option(30.0, help="Duración en segundos (un poco más que el reel)."),
    mood: str = typer.Option("comedia", help="comedia | tension | epica | ternura"),
    yes: bool = typer.Option(False, "--si", help="No preguntar (ya has dado el OK al gasto)."),
) -> None:
    """Compone una pista instrumental con Eleven Music. CUESTA (~820 créditos por minuto) y queda en tu catálogo."""
    from reels import sound

    credits = round(seconds / 60 * sound.MUSIC_CREDITS_PER_MIN)
    console.print(f"Eleven Music: {seconds:.0f} s ≈ {credits} créditos de ElevenLabs.")
    if not yes and not typer.confirm("¿La compongo?"):
        raise typer.Exit(1)
    try:
        entry = sound.compose(name, prompt, seconds, mood)
    except Exception as e:  # noqa: BLE001
        _fail("la música ha fallado", e)
    console.print(f"[green]✔[/] assets/music/{entry['file']}  ({entry['license']})")
    console.print(f'  En el guion: "music": {{"track": "{entry["file"]}", "volume": 0.18}}')


@app.command("music-import")
def music_import(
    source: str = typer.Argument(..., help="La pista (mp3/wav) con licencia que has descargado tú."),
    name: str = typer.Option(..., help="Nombre corto."),
    license_note: str = typer.Option(..., "--license", help="Licencia verificada (enlace), o 'SIN VERIFICAR - no publicar'."),
    mood: str = typer.Option("comedia"),
) -> None:
    """Añade una pista con licencia a tu catálogo (assets/music/music.json)."""
    from reels import sound

    try:
        entry = sound.import_track(Path(source), name, license_note, mood)
    except Exception as e:  # noqa: BLE001
        _fail("no he podido importarla", e)
    console.print(f"[green]✔[/] assets/music/{entry['file']}")


# --- numbers and references (the same as the 3D factory) ---------------------------------------------------------------


@app.command()
def ref(video: str = typer.Argument(..., help="Un reel de referencia (.mp4) que hayas guardado tú.")) -> None:
    """Desmonta un reel de referencia en references/<nombre>/: planos, hoja a 1 fps y transcripción."""
    from reels import refs

    console.print(f"[green]✔[/] {refs.reference(Path(video))}")


@app.command()
def stats() -> None:
    """Métricas de Instagram de cada reel por la API (opcional, con IG_ACCESS_TOKEN) → metrics/instagram.jsonl."""
    from reels import instagram

    try:
        rows = instagram.snapshot()
    except instagram.InstagramError as e:
        _fail("Instagram", e)
    console.print(f"[green]✔[/] {len(rows)} reels guardados en metrics/instagram.jsonl (mira `uv run reels review`)")


@app.command()
def comments() -> None:
    """Baja los comentarios de cada reel a metrics/comments.jsonl (local, no va a git)."""
    from reels import instagram

    try:
        new, total = instagram.comments()
    except instagram.InstagramError as e:
        _fail("Instagram", e)
    console.print(f"[green]✔[/] {new} comentarios nuevos ({total} en total) → metrics/comments.jsonl")


@app.command()
def review(hecho: bool = typer.Option(False, "--hecho", help="Lista de lo ya hecho (lo que /ideas no debe repetir).")) -> None:
    """Tabla de cada reel publicado con sus números (de /numeros)."""
    from reels import review as review_mod

    print(review_mod.done_list() if hecho else review_mod.metrics_table())


@app.command()
def calibrate() -> None:
    """Cuánto acierta cada crítico (espectadores, jurado) frente a los reels maduros: lo lee /calibrar."""
    from reels import calibrate as cal

    for line in cal.table() + [""] + cal.bias():
        console.print(escape(line))


if __name__ == "__main__":
    app()
