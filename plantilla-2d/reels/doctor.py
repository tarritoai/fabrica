"""`reels doctor` (2D factory): is this computer ready? One line per piece, and for each problem the exact fix for THIS
system. The 2D factory needs no Blender, no Rhubarb and no graphics card: Node + Remotion, ffmpeg, whisper and a key.

Written for people who have never used a terminal: plain Spanish, one command to copy per problem.
Nothing here costs money: the API checks only read account data (free endpoints).
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass

import httpx
from dotenv import dotenv_values
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from reels import system
from reels.assets import ROOT

OK, WARN, FAIL = "ok", "aviso", "falta"
ICONS = {OK: "[green]✔[/]", WARN: "[yellow]![/]", FAIL: "[red]✘[/]"}

NODE_MIN = (20, 0)
PYTHON_MIN = (3, 12)
FFMPEG_MIN = (6, 0)
WHISPER_URL = "https://github.com/ggml-org/whisper.cpp/releases"


@dataclass
class Check:
    name: str
    status: str
    detail: str
    fix: str = ""  # what to do, with the exact command for this OS


def _os() -> str:
    return system.current_os()


def hint(**per_os: str) -> str:
    """Pick the instruction for this OS (keys: mac, windows, linux, any)."""
    return per_os.get(_os()) or per_os.get("any", "")


def _brew_or(cmd: str) -> str:
    """On a Mac, Homebrew is the install method: if it is missing, say so first."""
    if system.find_tool("brew"):
        return cmd
    return f"primero instala Homebrew (mira la línea «Homebrew»), y luego: {cmd}"


def _run(cmd: list[str], timeout: float = 30) -> str:
    return system.run_text(cmd, timeout=timeout).strip()


def _shown(version: tuple[int, ...] | None) -> str:
    return ".".join(map(str, version)) if version else "?"


def _probe(name: str, path: str | None, args: list[str], minimum: tuple[int, ...] | None, fix: str) -> tuple[Check, str]:
    """Run `path args` and compare its version. Returns the check and the raw output."""
    if not path:
        return Check(name, FAIL, "no está instalado (o no lo encuentro)", fix), ""
    try:
        out = _run([path, *args])
    except (OSError, subprocess.TimeoutExpired) as e:
        extra = ""
        if _os() == "mac" and "bad cpu type" in str(e).lower():
            extra = " (necesita Rosetta: softwareupdate --install-rosetta --agree-to-license)"
        return Check(name, FAIL, f"está pero no arranca: {e}{extra}", fix), ""
    version = system.version_tuple(out)
    if minimum and (version is None or version < minimum):
        return Check(name, FAIL, f"versión {_shown(version)}, hace falta {_shown(minimum)} o más", fix), out
    return Check(name, OK, f"{_shown(version)}  ({path})"), out


# --- system ------------------------------------------------------------------------------------------------------


def check_python() -> Check:
    v = sys.version_info[:3]
    if v >= PYTHON_MIN:
        return Check("Python", OK, _shown(v))
    return Check("Python", FAIL, f"{_shown(v)}: hace falta 3.12", "uv python install 3.12  y luego  uv sync")


def check_brew() -> Check | None:
    if _os() != "mac":
        return None  # Homebrew is only an install method, and only on a Mac
    path = system.find_tool("brew")
    if path:
        return Check("Homebrew", OK, f"para instalar lo demás ({path})")
    return Check("Homebrew", WARN, "no está: es la forma fácil de instalar lo demás en un Mac",
                 '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                 "  (al acabar, copia y ejecuta las líneas de «Next steps» que te enseña)")


def check_uv() -> Check:
    fix = hint(windows='powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
               any="curl -LsSf https://astral.sh/uv/install.sh | sh")
    return _probe("uv", system.find_tool("uv"), ["--version"], None, fix + "  (y abre una terminal nueva)")[0]


def check_git() -> Check:
    fix = hint(mac="xcode-select --install", windows="winget install --id Git.Git -e",
               linux="opcional (sirve para copias de seguridad y actualizar): si tienes la contraseña de administrador, "
                     "sudo apt install git")
    check = _probe("git", system.find_tool("git"), ["--version"], None, fix)[0]
    if check.status == FAIL and _os() == "linux":
        check.status = WARN
    return check


def check_node() -> Check:
    fix = hint(mac=_brew_or("brew install node@24") + "  (y añade al PATH la línea que te enseña brew)",
               windows="winget install OpenJS.NodeJS.LTS  (y abre una terminal nueva)",
               linux="curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash  y luego  nvm install --lts")
    return _probe("Node.js", system.find_tool("node", "NODE_BIN"), ["--version"], NODE_MIN, fix)[0]


def check_remotion_deps() -> Check:
    cli = ROOT / "remotion" / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    if cli.exists():
        return Check("Remotion (el dibujo y el montaje)", OK, "piezas instaladas en remotion/node_modules")
    return Check("Remotion (el dibujo y el montaje)", FAIL, "faltan sus piezas (no se ha hecho npm ci)",
                 f'cd "{ROOT / "remotion"}"  y luego  npm ci')


def ffmpeg_fix() -> str:
    return hint(mac=_brew_or("brew install ffmpeg"),
                windows="winget install Gyan.FFmpeg  (y abre una terminal nueva)",
                # No sudo: the distro's ffmpeg is often too old (Ubuntu 22.04: 4.4, 24.04: 6.1); a static build in
                # ~/.local/opt is found automatically (reels/system.py tool_dirs).
                linux="mkdir -p ~/.local/opt && curl -L https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
                      "ffmpeg-master-latest-linux64-gpl.tar.xz | tar -xJ -C ~/.local/opt")


def check_ffmpeg() -> list[Check]:
    fix = ffmpeg_fix()
    path = system.find_tool("ffmpeg", "FFMPEG_BIN")
    if not path:
        return [Check("ffmpeg", FAIL, "no está instalado (o no lo encuentro)", fix)]
    try:
        version = system.ffmpeg_version(path)
        encoders = _run([path, "-hide_banner", "-encoders"])
        filters = _run([path, "-hide_banner", "-filters"])
    except (OSError, subprocess.TimeoutExpired) as e:
        return [Check("ffmpeg", FAIL, f"está pero no arranca: {e}", fix)]
    checks = []
    if version and version < FFMPEG_MIN:
        checks.append(Check("ffmpeg", FAIL, f"versión {_shown(version)}: es vieja, hace falta la 6 o más", fix))
    elif "libx264" not in encoders:
        checks.append(Check("ffmpeg", FAIL, f"{_shown(version)} sin libx264 (no puede hacer MP4)", fix))
    else:
        tempo = "acelera la voz con rubberband" if " rubberband " in filters else "acelera la voz con atempo (sin rubberband: suena un poco menos natural)"
        checks.append(Check("ffmpeg", OK, f"{_shown(version)}, {tempo}  ({path})"))
    probe = system.find_tool("ffprobe", "FFPROBE_BIN")
    checks.append(Check("ffprobe", OK, probe) if probe else Check("ffprobe", FAIL, "no está (viene con ffmpeg)", fix))
    return checks




def check_whisper() -> list[Check]:
    fix = hint(mac=_brew_or("brew install whisper-cpp"),
               windows=f"baja whisper-bin-x64.zip de {WHISPER_URL} (la versión «bNNNN» más nueva) y descomprímelo en "
                       f"{ROOT / 'tools' / 'whisper'}",
               linux=f"baja whisper-bin-ubuntu-x64.tar.gz de {WHISPER_URL} (la versión «bNNNN» más nueva) y "
                     f"descomprímelo en {ROOT / 'tools' / 'whisper'}")
    checks = []
    path = system.find_whisper()
    if path:
        try:
            _run([path, "--help"])
            checks.append(Check("whisper.cpp (oído)", OK, path))
        except (OSError, subprocess.TimeoutExpired) as e:
            checks.append(Check("whisper.cpp (oído)", FAIL, f"está pero no arranca: {e}", fix))
    else:
        checks.append(Check("whisper.cpp (oído)", FAIL, "no está instalado (o no lo encuentro)", fix))
    model = system.whisper_model()
    if model.exists() and model.stat().st_size > 100e6:
        checks.append(Check("modelo de whisper", OK, f"{model.name} ({model.stat().st_size / 1e6:.0f} MB)"))
    else:
        shown = model.relative_to(ROOT) if model.is_relative_to(ROOT) else model
        checks.append(Check("modelo de whisper", FAIL, f"falta {shown} (unos 470 MB)", "uv run reels descargar-modelo"))
    return checks














def check_project_path() -> Check:
    text = str(ROOT)
    synced = [s for s in ("OneDrive", "Mobile Documents", "iCloud", "Dropbox", "Google Drive") if s.lower() in text.lower()]
    better = r"C:\nave-2d" if _os() == "windows" else "~/nave-2d"
    if synced:
        return Check("carpeta del proyecto", WARN, f"{text} está dentro de {synced[0]}: sincroniza miles de archivos "
                     "temporales del render y puede bloquearlos a medias", f"mueve la carpeta fuera, por ejemplo a {better}")
    if _os() == "windows" and (" " in text or not text.isascii()):
        # The pipeline itself handles it (pathlib, argument lists, UTF-8); some third-party tools are the risk.
        return Check("carpeta del proyecto", WARN, f"{text} tiene espacios o tildes: la fábrica lo soporta, pero si "
                     "una herramienta externa falla, este es el primer sospechoso", f"si algo falla, muévela a {better}")
    return Check("carpeta del proyecto", OK, text)


def check_fonts() -> Check:
    fonts = ROOT / "remotion" / "src" / "fonts"
    n = len(list(fonts.glob("*.woff2"))) if fonts.is_dir() else 0
    if n >= 6:
        return Check("tipografías (incluidas)", OK, f"{n} archivos en remotion/src/fonts")
    return Check("tipografías (incluidas)", FAIL, "faltan las tipografías de la fábrica",
                 "vuelve a copiar la plantilla (/fabrica:actualizar) o /fabrica:nave")


# --- secrets -----------------------------------------------------------------------------------------------------


def _mask(key: str) -> str:
    return f"{key[:4]}…{key[-4:]}" if len(key) > 12 else "…"


def check_env_ignored() -> Check:
    if not (ROOT / ".env").exists():
        return Check(".env (tus claves)", WARN, "todavía no existe", hint(windows="copy .env.example .env",
                                                                          any="cp .env.example .env"))
    if not (ROOT / ".git").exists():
        return Check(".env (tus claves)", OK, "existe (la carpeta aún no es un repositorio git)")
    result = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT, capture_output=True)
    if result.returncode == 0:
        return Check(".env (tus claves)", OK, "existe y git no lo sube nunca")
    return Check(".env (tus claves)", FAIL, "git NO lo está ignorando: podrías publicar tus claves",
                 "añade una línea .env al archivo .gitignore")


def check_anthropic(shell_env: dict[str, str], file_env: dict[str, str | None]) -> Check:
    """Claude Code bills the API (pay per use) instead of the subscription when ANTHROPIC_API_KEY is set."""
    if shell_env.get("ANTHROPIC_API_KEY", "").strip():
        return Check("ANTHROPIC_API_KEY", WARN,
                     "está puesta en tu sistema: Claude Code la usará y te cobrará por uso en vez de usar tu suscripción",
                     hint(windows='quítala: [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "User") '
                                  "y abre una terminal nueva",
                          any="quítala de tu ~/.zshrc o ~/.bashrc (la línea export ANTHROPIC_API_KEY=...) y abre una terminal nueva"))
    if (file_env.get("ANTHROPIC_API_KEY") or "").strip():
        return Check("ANTHROPIC_API_KEY", WARN, "está en .env: solo la usa `reels script` (cobra por uso); la fábrica no la necesita",
                     "si no usas `reels script`, borra su valor en .env")
    return Check("ANTHROPIC_API_KEY", OK, "no está (bien: Claude Code usa tu suscripción)")


def check_elevenlabs(client: httpx.Client) -> Check:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        return Check("ELEVENLABS_API_KEY", WARN, "vacía: hará falta para generar voces",
                     "pégala en .env (elevenlabs.io → Developers → API keys)")
    try:
        r = client.get("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": key})
    except httpx.HTTPError as e:
        return Check("ELEVENLABS_API_KEY", FAIL, f"sin conexión: {e}", "revisa tu conexión a internet")
    if r.status_code == 200:
        sub = r.json()
        used, limit = sub.get("character_count", 0), sub.get("character_limit", 0)
        status = WARN if limit and used / limit > 0.8 else OK
        return Check("ELEVENLABS_API_KEY", status, f"{_mask(key)}  plan {sub.get('tier', '?')}: te quedan {max(0, limit - used):,} "
                     f"créditos de {limit:,} este mes",
                     "te queda menos del 20 % de créditos este mes" if status == WARN else "")
    if r.status_code in (401, 403) and "permission" in r.text.lower():
        r2 = client.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key})
        if r2.status_code == 200:
            return Check("ELEVENLABS_API_KEY", WARN, f"{_mask(key)}  válida, pero sin permiso user_read",
                         "activa el permiso user_read de la clave para ver cuántos créditos te quedan")
    return Check("ELEVENLABS_API_KEY", FAIL, f"{_mask(key)}  no funciona (HTTP {r.status_code})", "copia otra vez la clave en .env")








# --- report ------------------------------------------------------------------------------------------------------


def collect(skip_api: bool = False) -> list[tuple[str, list[Check]]]:
    shell_env = dict(os.environ)  # before .env is loaded: what Claude Code itself would see
    file_env = dotenv_values(ROOT / ".env") if (ROOT / ".env").exists() else {}
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    system.setup_path()
    base = [check_python(), check_brew(), check_uv(), check_git(), check_node(), check_remotion_deps(), *check_ffmpeg(),
            *check_whisper(), check_fonts(), check_project_path()]
    secrets = [check_env_ignored(), check_anthropic(shell_env, file_env)]
    if not skip_api:
        with httpx.Client(timeout=15) as client:
            secrets += [check_elevenlabs(client)]
    secrets = [c for c in secrets if c]
    return [("Programas", [c for c in base if c]), ("Claves", secrets)]


def run(skip_api: bool = False, as_json: bool = False) -> bool:
    sections = collect(skip_api)
    checks = [c for _, cs in sections for c in cs]
    failed = [c for c in checks if c.status == FAIL]
    if as_json:
        print(json.dumps({"os": _os(), "ok": not failed, "checks": [asdict(c) for c in checks]}, ensure_ascii=False, indent=1))
        return not failed
    console = Console()
    names = {"mac": "Mac", "windows": "Windows", "linux": "Linux"}
    console.print(f"[bold]Revisión de la fábrica 2D[/] · {names[_os()]} ({platform.machine()}) · {ROOT}")
    table = Table(show_header=False, box=None, padding=(0, 1))
    for title, cs in sections:
        table.add_row("", f"[bold]{title}[/]", "")
        for c in cs:
            detail = escape(c.detail) + (f"\n[cyan]→ {escape(c.fix)}[/]" if c.fix and c.status != OK else "")
            table.add_row(ICONS[c.status], escape(c.name), detail)
    console.print(table)
    if failed:
        console.print(f"\n[red bold]✘ {len(failed)} cosa(s) por arreglar:[/] {', '.join(c.name for c in failed)}. "
                      "Copia el comando de la flecha →, ejecútalo y vuelve a lanzar `uv run reels doctor`.")
    else:
        console.print("\n[green bold]✔ Todo listo.[/] Siguiente paso: `uv run reels humo` (un reel de prueba, gratis).")
    return not failed
