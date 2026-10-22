"""Single entry point: `reels <command>`."""

import json

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markup import escape

from reels import cast
from reels import doctor as doctor_mod
from reels import system
from reels.assets import ROOT

console = Console()

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """La fábrica: de un guion (script.json) a un reel animado en 3D."""
    system.setup_console()
    system.setup_path()
    load_dotenv(ROOT / ".env")


@app.command()
def doctor(
    skip_api: bool = typer.Option(False, "--skip-api", help="No comprobar las claves (sin internet)."),
    as_json: bool = typer.Option(False, "--json", help="Salida en JSON (para el instalador y la CI)."),
    render_test: bool = typer.Option(False, "--prueba-render", help="Mide cuánto tardaría tu computadora en renderizar un reel."),
) -> None:
    """¿Está todo instalado? Revisa cada pieza y, si falta algo, te da el comando exacto para tu sistema."""
    ok = doctor_mod.run(skip_api=skip_api, as_json=as_json)
    if render_test:
        if not ok:
            console.print("[yellow]Arregla primero lo que falta: la prueba de render necesita todo lo de arriba.[/]")
            raise typer.Exit(1)
        from reels import smoke

        console.print("\n[bold]Prueba de render[/] (unos fotogramas a calidad final; puede tardar un par de minutos)…")
        r = smoke.render_benchmark()
        console.print(f"  {r['seconds_per_frame']} s por fotograma → un reel de 30 s tardaría "
                      f"~{r['minutes_for_30s_reel']:.0f} min en tu computadora")
        console.print(f"[bold]  Recomendación:[/] {r['advice']}")
    if not ok:
        raise typer.Exit(1)


@app.command()
def humo(
    calidad: str = typer.Option("humo", help="humo (mínima, la más rápida) | draft | preview"),
    motor: str = typer.Option(None, help="cycles = sin GPU (máquinas virtuales, CI). Por defecto, EEVEE."),
    comprobar: bool = typer.Option(True, "--comprobar/--sin-comprobar", help="Re-escuchar el vídeo con whisper al final."),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir", help="Abrir el vídeo al terminar."),
) -> None:
    """Prueba de humo GRATIS: un vídeo de 7 s de punta a punta con una voz ya grabada (sin cuentas ni claves)."""
    from reels import smoke

    try:
        final = smoke.run(quality=calidad, engine=motor, check=comprobar)
    except Exception as e:  # noqa: BLE001  one plain message for a first-time user (details are in the logs)
        console.print(f"[red bold]✘ la prueba de humo ha fallado:[/] {escape(str(e))}")
        console.print("  Ejecuta `uv run reels doctor`: casi siempre es una pieza sin instalar.")
        raise typer.Exit(1)
    console.print(f"[green bold]✔ ¡La fábrica funciona![/] Tu primer vídeo: {final}")
    if abrir:
        system.open_path(final)


@app.command()
def personaje(
    nombre: str = typer.Argument(..., help="La carpeta del personaje: personajes/<nombre>/personaje.json"),
    celda: int = typer.Option(300, help="Tamaño de cada viñeta en píxeles (ancho)."),
    abrir: bool = typer.Option(True, "--abrir/--no-abrir", help="Abrir la hoja al terminar."),
) -> None:
    """Hoja de expresiones GRATIS de un personaje: sus 8 emociones, bocas, gestos y parpadeo, en una imagen."""
    from reels import personaje as sheet_mod

    try:
        dest = sheet_mod.sheet(nombre, celda)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red bold]✘ no he podido hacer la hoja:[/] {escape(str(e))}")
        raise typer.Exit(1)
    console.print(f"[green bold]✔ hoja de expresiones:[/] {dest}")
    console.print(f"[green bold]✔ fotograma:[/] {dest.parent / 'fotograma.png'}")
    console.print("  Orden: neutral, orgulloso, confuso, alarma, juzgando, hundido, pánico, aliviado · bocas M, E, A, O · "
                  "gestos · parpadeo")
    if abrir:
        system.open_path(dest)


@app.command()
def ejemplo(
    nombre: str = typer.Argument(None, help="lampara-de-las-tres | cafeteria-moka (sin nombre: la lista)"),
    calidad: str = typer.Option("draft", help="humo | draft | preview | final"),
    entero: bool = typer.Option(False, "--entero", help="El vídeo completo montado (si no, un fotograma por plano)."),
) -> None:
    """Abre un episodio de ejemplo que viene con la fábrica (voces ya grabadas: gratis) y lo renderiza."""
    from reels import ejemplos

    if not nombre:
        console.print("Ejemplos: " + ", ".join(ejemplos.available()))
        return
    try:
        result = ejemplos.run(nombre, calidad, stills=not entero)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red bold]✘ el ejemplo ha fallado:[/] {escape(str(e))}")
        raise typer.Exit(1)
    console.print(f"[green bold]✔ listo:[/] {result}")


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
def script(
    topic: str = typer.Argument(..., help='Tema, p. ej. "env publico".'),
    duration: float = typer.Option(20.0, help="Duración objetivo en segundos."),
    tone: str = typer.Option(None, help="comedia | agridulce | serie (por defecto lo elige el writer)."),
) -> str:
    """Genera episodes/<slug>/script.json a partir de un tema."""
    from reels import writer

    load_dotenv(ROOT / ".env")
    episode, usd = writer.write_script(topic, duration, tone)
    writer.save(episode, usd)
    console.print(f"[green]✔[/] episodes/{episode.slug}/script.json  ({len(episode.beats)} beats, ${usd:.3f})")
    for b in episode.beats:
        who = b.speaker.value if b.speaker else "—"
        text = b.line or (f"[{b.event.component}]" if b.event else f"(reacción muda de {b.reactor.value if b.reactor else cast.HUMAN})")
        tags = escape(" ".join(f"[{t.value}]" for t in b.delivery.tags)) if b.delivery else ""
        console.print(f"  {b.id:>2} [bold]{who:<8}[/] {text}  [dim]{tags} {b.emotion.value} · {b.action.value} · {b.camera.value}[/]")
    return episode.slug


def _load(slug: str):
    from reels.assets import episode_dir
    from reels.schema import Episode

    load_dotenv(ROOT / ".env")
    return Episode.model_validate_json((episode_dir(slug) / "script.json").read_text(encoding="utf-8"))


@app.command()
def voice(
    slug: str,
    only: str = typer.Option("", help="Regenera solo estos beats (ids separados por comas) y deja el resto del audio."),
    nonverbal: bool = typer.Option(False, "--nonverbal", help="Solo los sonidos sin palabras (risa, suspiro)."),
    spaces: bool = typer.Option(False, "--spaces", help="Solo reaplica la acústica (gratis, desde las copias secas)."),
    takes: int = typer.Option(0, "--takes", help="Saca 3 tomas sueltas de este beat para elegir de oído."),
    pick: str = typer.Option("", "--pick", help="Fija una toma elegida: 20=3 (beat=toma)."),
) -> None:
    """Genera (o reutiliza de la caché) las voces de cada beat."""
    from reels import voice as voice_mod

    if takes:
        page = voice_mod.voice_takes(_load(slug), takes)
        console.print(f"[green]✔[/] {page}")
        system.open_path(page)
    elif pick:
        beat, _, take = pick.partition("=")
        voice_mod.voice_pick(_load(slug), int(beat), int(take))
    elif spaces:
        voice_mod.apply_spaces(_load(slug))
    elif nonverbal:
        console.print(f"[green]✔[/] {voice_mod.voice_nonverbal(_load(slug))} créditos nuevos de ElevenLabs")
    elif only:
        voice_mod.voice_lines(_load(slug), [int(x) for x in only.split(",")])
    else:
        voice_mod.voice_episode(_load(slug))


@app.command("sfx-gen")
def sfx_gen(
    name: str = typer.Argument(..., help="Nombre del efecto (assets/sfx/<nombre>.wav)."),
    prompt: str = typer.Argument(..., help="Descripción del sonido, en inglés."),
    seconds: float = typer.Option(4.0, help="Duración en segundos."),
) -> None:
    """Genera un efecto de sonido con ElevenLabs (se cachea por descripción)."""
    from reels import voice as voice_mod

    load_dotenv(ROOT / ".env")
    console.print(f"[green]✔[/] {voice_mod.sound_effect(name, prompt, seconds)}")


@app.command("score")
def score_cmd(slug: str) -> None:
    """Episodio musical (episode.score): sintetiza la mezcla → audio/score.wav (gratis, segundos)."""
    from reels import score as score_mod

    episode = _load(slug)
    if not episode.score:
        raise typer.BadParameter(f"{slug} no tiene score")
    out = score_mod.render(episode)
    ev = score_mod.events(episode.score)
    console.print(f"[green]✔[/] {out.relative_to(ROOT)}: {len(ev['notes'])} notas, {episode.score.bars()} compases "
                  f"a {episode.score.bpm} BPM ({episode.score.bars() * 4 * 60 / episode.score.bpm:.1f} s)")


@app.command("music-gen")
def music_gen(
    name: str = typer.Argument(..., help="Nombre de la pista (assets/music/src/<nombre>.mp3)."),
    prompt: str = typer.Argument(..., help="Cómo es la música, en inglés (instrumentos, tempo, emoción, estructura)."),
    seconds: float = typer.Option(45.0, help="Duración en segundos (un poco más que el reel)."),
    mood: str = typer.Option("agridulce", help="agridulce | chill | tension | comedia | epica"),
    yes: bool = typer.Option(False, "--si", help="No preguntar (ya has dado el OK al gasto)."),
) -> None:
    """Compone una pista instrumental con Eleven Music. CUESTA (~900 créditos por minuto) y queda en tu catálogo."""
    from reels import music

    load_dotenv(ROOT / ".env")
    credits = round(seconds / 60 * music.MUSIC_CREDITS_PER_MIN)
    console.print(f"Eleven Music: {seconds:.0f} s ≈ {credits} créditos de ElevenLabs.")
    if not yes and not typer.confirm("¿La compongo?"):
        raise typer.Exit(1)
    entry = music.generate(prompt, seconds, mood, name)
    console.print(f"[green]✔[/] {entry['file']}  ({entry['mood']}, {entry['license']})")
    console.print(f'  Úsala en el guion: "music": {{"mood": "{entry["mood"]}", "track": "{entry["file"]}"}}')


@app.command("music-import")
def music_import(
    source: str,
    mood: str = typer.Option(..., help="agridulce | chill | tension | comedia"),
    starts: str = typer.Option(..., help="Segundos de inicio separados por comas, p. ej. 103.9,446.7"),
    length: float = typer.Option(75.0, help="Duración de cada clip en segundos."),
    license_note: str = typer.Option(..., "--license", help="Licencia verificada, o 'SIN VERIFICAR - no publicar'."),
) -> None:
    """Recorta clips de una pista larga y los añade a assets/music/music.json."""
    from pathlib import Path

    from reels import music

    for t in music.import_clips(Path(source), mood, [float(x) for x in starts.split(",")], length, license_note):
        console.print(f"[green]✔[/] {t['file']}  ({t['mood']}, {t['license']})")


@app.command()
def build(slug: str) -> None:
    """timeline + lip sync + pantallas Remotion + escena Blender (scene.blend)."""
    from reels import build as build_mod

    build_mod.build(_load(slug))


@app.command()
def render(
    slug: str,
    quality: str = typer.Option("final", help="humo | draft | preview | final | ultra (1.5x supersampled, 64 samples; nube)"),
    keyframes: bool = typer.Option(False, help="Solo un fotograma por beat (revisión rápida)."),
    cloud: bool = typer.Option(False, "--cloud", help="Renderiza en una GPU alquilada (Vast.ai) y la destruye al acabar."),
    max_price: float = typer.Option(0.6, help="--cloud: precio máximo en $/hora."),
    offer: int = typer.Option(0, help="--cloud: id de una oferta concreta de Vast."),
    fast: bool = typer.Option(False, "--fast", help="--cloud: solo GPUs rápidas (4090/5090/4080), para escenas pesadas."),
) -> None:
    """Renderiza la escena con Blender (reanudable) y monta renders/scene.mp4."""
    from reels import build as build_mod

    build_mod.rebuild_if_outdated(slug)  # a stale scene.blend would render (and upload) the old animation
    if cloud:
        from reels import cloud as cloud_mod

        load_dotenv(ROOT / ".env")
        # A laptop that falls asleep drops the SSH session while the rented GPU keeps billing: stay awake until the
        # machine is destroyed.
        # Closing the terminal or a SIGTERM must still run the `finally` that destroys the machine.
        with system.keep_awake("reels render --cloud"), system.exit_cleanly_on_terminate():
            try:
                console.print(f"[green]✔[/] {cloud_mod.render(slug, quality, max_price, offer or None, fast)}")
            except cloud_mod.CloudError as e:
                console.print(f"[red bold]✘ render en la nube:[/] {escape(str(e))}")
                raise typer.Exit(1)
        return
    console.print(f"[green]✔[/] {build_mod.render(slug, quality, keyframes)}")


@app.command("cloud-cleanup")
def cloud_cleanup(
    todas: bool = typer.Option(False, "--todas", help="También las que usa un render en marcha en esta computadora."),
) -> None:
    """Destruye las máquinas de render que se hayan quedado encendidas en Vast.ai sin que nadie las use."""
    from reels import cloud as cloud_mod

    load_dotenv(ROOT / ".env")
    try:
        with cloud_mod._client() as c:
            done, busy = cloud_mod.destroy_orphans(c, everything=todas)
    except Exception as e:  # noqa: BLE001  no key, no internet: say it plainly
        console.print(f"[red bold]✘ no he podido revisar Vast:[/] {escape(str(e))}")
        raise typer.Exit(1)
    if done:
        console.print(f"[green]✔[/] {len(done)} máquina(s) destruida(s): ya no cobran")
    else:
        console.print("[green]✔[/] No había ninguna máquina de la fábrica encendida sin usar.")
    if busy:
        console.print(f"  {len(busy)} máquina(s) en uso por un render en marcha en esta computadora: no las toco "
                      "(se destruyen solas al acabar; `--todas` para cortarlas ya).")


@app.command()
def preview(
    slug: str,
    beats: str = typer.Option(..., help="Rango de beats, p. ej. 2-4 (o un solo beat: 3)."),
    quality: str = typer.Option("preview", help="draft (rapidísimo) | preview"),
    open_video: bool = typer.Option(True, "--open/--no-open", help="Abrir el resultado al terminar."),
) -> None:
    """Renderiza y compone solo unos beats, con música y subtítulos, para iterar rápido."""
    from reels import build as build_mod

    first, _, last = beats.partition("-")
    result = build_mod.preview(slug, int(first), int(last or first), quality)
    console.print(f"[green]✔[/] {result}")
    if open_video:
        system.open_path(result)


@app.command()
def animatic(
    slug: str,
    audio_only: bool = typer.Option(False, "--audio-only", help="Solo voces + música + subtítulos sobre negro (sin Blender)."),
    open_video: bool = typer.Option(True, "--open/--no-open", help="Abrir el resultado al terminar."),
) -> None:
    """Revisión barata: mezcla real sobre un fotograma fijo por beat (o sobre negro con --audio-only)."""
    from reels import build as build_mod

    result = build_mod.animatic(slug, audio_only)
    console.print(f"[green]✔[/] {result}")
    if open_video:
        system.open_path(result)


@app.command()
def compose(slug: str) -> None:
    """Composición final con Remotion: vídeo + voces + subtítulos + SFX -> final.mp4."""
    from reels import build as build_mod

    console.print(f"[green]✔[/] {build_mod.compose(slug)}")


@app.command()
def cover(
    slug: str,
    beat: int = typer.Option(..., help="Beat del que sale la imagen (su fotograma central)."),
    title: str = typer.Option(None, help="Título (por defecto, el del episodio)."),
    mark: str = typer.Option(None, help="Marca pequeña bajo el título, p. ej. 1/3 (por defecto, la parte de la serie)."),
    at: float = typer.Option(0.5, help="Punto del beat (0 = inicio, 1 = final)."),
) -> None:
    """Portada para la cuadrícula del perfil: un fotograma a máxima calidad + título -> publicar/<slug>_portada.png."""
    from reels import build as build_mod

    console.print(f"[green]✔[/] {build_mod.cover(slug, beat, title, mark, at)}")


@app.command()
def check(slug: str) -> None:
    """Comprueba que final.mp4 dice cada frase mientras su plano está en pantalla."""
    from reels.check import check_sync

    if not check_sync(slug):
        raise typer.Exit(1)


@app.command()
def stats() -> None:
    """Métricas de Instagram de cada reel (las guarda en metrics/instagram.jsonl)."""
    from rich.table import Table

    from reels import instagram

    load_dotenv(ROOT / ".env")
    try:
        rows = instagram.snapshot()
    except instagram.InstagramError as e:
        console.print(f"[red]✘ {e}[/]")
        raise typer.Exit(1)
    table = Table(title=f"{len(rows)} reels")
    for col in ("episodio", "edad", "visitas", "visto medio", "% visto", "salta <3 s", "likes %", "compart.", "guard."):
        table.add_column(col, justify="left" if col == "episodio" else "right")
    for r in sorted(rows, key=lambda r: r["posted_at"], reverse=True):
        m = r["metrics"]
        views = m.get("views") or 0
        watch = (m.get("ig_reels_avg_watch_time") or 0) / 1000
        dur = r["duration_s"]
        skip = m.get("reels_skip_rate")
        age = r["age_h"]
        table.add_row(
            r["slug"] or "[dim]?[/]",
            f"{age / 24:.1f} d" if age >= 48 else f"{age:.0f} h",
            f"{views:,}".replace(",", "."),
            f"{watch:.1f} s" if watch else "-",
            f"{100 * watch / dur:.0f} %" if watch and dur else "-",
            f"{skip:.0f} %" if skip is not None else "-",
            f"{100 * (m.get('likes') or 0) / views:.1f} %" if views else "-",
            str(m.get("shares", "-")),
            str(m.get("saved", "-")),
        )
    console.print(table)
    hist = instagram.followers()
    if hist:
        line = f"Seguidores: {hist[-1]['followers']}"
        if len(hist) > 1 and hist[-2]["followers"] is not None:
            line += f" ({hist[-1]['followers'] - hist[-2]['followers']:+d} desde {hist[-2]['fetched_at'][:16].replace('T', ' ')})"
        console.print(line)
    console.print("[dim]Meta puede tardar hasta 48 h en consolidar los datos de un reel.[/]")


@app.command()
def comments() -> None:
    """Baja los comentarios de cada reel a metrics/comments.jsonl (local, no va a git)."""
    from reels import instagram

    load_dotenv(ROOT / ".env")
    try:
        new, total = instagram.comments()
    except instagram.InstagramError as e:
        console.print(f"[red]✘ {e}[/]")
        raise typer.Exit(1)
    console.print(f"[green]✔[/] {new} comentarios nuevos ({total} en total) → metrics/comments.jsonl")


@app.command()
def review(
    hecho: bool = typer.Option(False, "--hecho", help="Lista de todo lo ya hecho (lo que /ideas no debe repetir)."),
) -> None:
    """Tabla de cada reel publicado: métricas sobre alcance + duración, primera voz, tono y qué probaba."""
    from reels import review as review_mod

    print(review_mod.done_list() if hecho else review_mod.metrics_table())


@app.command()
def lint(slug: str) -> None:
    """Revisión gratis del guion (y del audio si ya existe) antes de gastar: sale con error si algo bloquea."""
    from reels.lint import lint as run_lint

    issues = run_lint(slug)
    for i in issues:
        color = "red" if i.level == "ERROR" else "yellow"
        console.print(f"[{color}]{i.level:<5}[/] [dim]{i.where:<9}[/] {escape(i.msg)}")
    errors = sum(i.level == "ERROR" for i in issues)
    if errors:
        console.print(f"[red bold]✘ {errors} errores: arréglalos antes del siguiente paso de pago[/]")
        raise typer.Exit(1)
    console.print(f"[green bold]✔ sin errores[/] ({len(issues)} avisos)")


@app.command()
def sheet(
    video: str = typer.Argument(..., help="Ruta a un vídeo, o un slug (usa su final.mp4)."),
    start: float = typer.Option(0.0, help="Segundo de inicio."),
    end: float = typer.Option(3.0, help="Segundo final."),
    fps: float = typer.Option(4.0, help="Fotogramas por segundo en la hoja."),
) -> None:
    """Hoja de fotogramas de un tramo (para juzgar movimiento y ritmo) + qué se dice en ese tramo."""
    from pathlib import Path

    from reels import sheet as sheet_mod
    from reels.assets import episode_dir

    slug = None if Path(video).exists() else video
    src = episode_dir(slug) / "final.mp4" if slug else Path(video)
    out = (episode_dir(slug) if slug else src.parent) / f"sheet_{start:g}-{end:g}.png"
    times = sheet_mod.sheet(src, start, end, fps, out)
    console.print(f"[green]✔[/] {out}  ({len(times)} fotogramas, de izquierda a derecha y de arriba abajo, "
                  f"{sheet_mod.COLS} por fila)")
    console.print("  tiempos: " + " ".join(f"{t:g}" for t in times))
    if slug:
        for line in sheet_mod.lines_between(slug, start, end):
            console.print("  " + escape(line))


@app.command()
def ref(video: str = typer.Argument(..., help="Un reel de referencia (.mp4) que hayas guardado tú.")) -> None:
    """Desmonta un reel de referencia en references/<nombre>/: planos, hoja a 1 fps y transcripción con tiempos."""
    from pathlib import Path

    from reels import sheet as sheet_mod

    console.print(f"[green]✔[/] {sheet_mod.reference(Path(video))}")


@app.command()
def calibrate() -> None:
    """Cuánto acierta cada crítico (espectadores, jurado) frente a los reels maduros: lo lee /calibrar."""
    from reels import calibrate as cal

    for line in cal.table() + [""] + cal.bias():
        console.print(escape(line))


@app.command()
def make(
    topic: str = typer.Argument(..., help='Tema, p. ej. "env publico".'),
    duration: float = typer.Option(20.0, help="Duración objetivo en segundos."),
    tone: str = typer.Option(None, help="comedia | agridulce | serie."),
    quality: str = typer.Option("final", help="preview | final"),
) -> None:
    """De tema a final.mp4 sin intervención: script → voice → build → render → compose."""
    import time

    from reels import build as build_mod
    from reels.assets import episode_dir

    t0 = time.time()
    console.rule("[bold]1/5 guion")
    slug = script(topic, duration, tone)
    episode = _load(slug)
    console.rule("[bold]2/5 voces")
    from reels import voice as voice_mod

    # Not voice(slug): called as a plain function, Typer's option defaults would be truthy OptionInfo objects.
    voice_mod.voice_episode(episode)
    console.rule("[bold]3/5 escena")
    build_mod.build(episode)
    console.rule("[bold]4/5 render")
    build_mod.render(slug, quality)
    console.rule("[bold]5/5 composición")
    final = build_mod.compose(slug)
    from reels.check import check_sync

    console.rule("[bold]comprobación")
    check_sync(slug)
    total = json.loads((episode_dir(slug) / "cost.json").read_text(encoding="utf-8"))["total_usd"]
    console.print(f"\n[green bold]✔ {final}[/]  ({(time.time() - t0) / 60:.1f} min, ${total:.3f})")


if __name__ == "__main__":
    app()
