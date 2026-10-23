"""Operating-system glue: where the tools live, how to call them and how to open files (Mac, Windows, Linux).

Every stage asks this module instead of hard-coding a path or a Mac-only command, so the same code runs on a
Mac (Apple Silicon), on native Windows 10/11 and on Linux.

Tool lookup order, for every external program:
1. an explicit variable in .env (BLENDER_BIN, RHUBARB_BIN, WHISPER_BIN, FFMPEG_BIN...), relative to the project;
2. the PATH (after adding the project's own tools/ folders to it, see `setup_path`);
3. the usual install places of that operating system (Blender only).
"""

from __future__ import annotations

import os
import re
import shutil
import hashlib
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from reels.assets import ROOT

TOOLS = ROOT / "tools"
DEFAULT_WHISPER_MODEL = "models/ggml-small.bin"
WHISPER_MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
FFMPEG_MIN = (7, 0)  # afir's irnorm option (voice acoustics) exists since ffmpeg 7.0; Ubuntu 24.04 ships 6.1
DEVNULL = os.devnull  # "/dev/null" on Mac/Linux, "nul" on Windows


def current_os() -> str:
    """'mac', 'windows' or 'linux'."""
    if sys.platform == "darwin":
        return "mac"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def exe(name: str) -> str:
    """File name of an executable on this OS (adds .exe on Windows)."""
    return f"{name}.exe" if current_os() == "windows" and not name.lower().endswith(".exe") else name


def project_path(value: str | os.PathLike) -> Path:
    """A path from .env or the CLI: `~` expanded, relative paths taken from the project root (not the cwd)."""
    p = Path(value).expanduser()
    return p if p.is_absolute() else ROOT / p


# --- PATH -------------------------------------------------------------------------------------------------------


def tool_dirs() -> list[Path]:
    """Folders where the installer may drop portable tools (tools/bin, tools/<tool>/, tools/<tool>/bin)."""
    dirs: list[Path] = [TOOLS / "bin"]
    if TOOLS.is_dir():
        for sub in sorted(TOOLS.iterdir()):
            if sub.is_dir() and sub.name != "bin":
                dirs += [sub, sub / "bin"]
    if current_os() == "mac":
        # Homebrew on Apple Silicon / Intel: present even when the shell profile was not reloaded yet.
        dirs += [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
        # node@24 is keg-only (not linked into bin/): found even if the user skipped brew's PATH step.
        dirs += sorted(Path("/opt/homebrew/opt").glob("node@*/bin"), reverse=True)
    if current_os() == "windows" and (local_app := os.environ.get("LOCALAPPDATA")):
        # winget's command links: present before a new terminal picks up the updated PATH.
        dirs.append(Path(local_app) / "Microsoft" / "WinGet" / "Links")
    if current_os() == "linux":
        # No-sudo installs: ~/.local/bin and portable builds unpacked in ~/.local/opt/<tool>[/bin].
        local = Path.home() / ".local"
        dirs.append(local / "bin")
        opt = local / "opt"
        if opt.is_dir():
            for sub in sorted(opt.iterdir()):
                if sub.is_dir():
                    dirs += [sub / "bin", sub]
    return [d for d in dirs if d.is_dir()]


def setup_path() -> None:
    """Put the project's own tools first in PATH (idempotent). Child processes inherit it."""
    current = os.environ.get("PATH", "").split(os.pathsep)
    extra = [str(d) for d in tool_dirs() if str(d) not in current]
    if extra:
        os.environ["PATH"] = os.pathsep.join([*extra, *current])


def find_tool(names: str | list[str], env_var: str | None = None) -> str | None:
    """Full path of a program, or None. `names` are tried in order (e.g. whisper-cli, then whisper-cpp)."""
    if env_var and (value := os.environ.get(env_var, "").strip()):
        p = project_path(value)
        return str(p) if p.exists() else None
    setup_path()
    candidates = [names] if isinstance(names, str) else names
    for name in candidates:
        if found := shutil.which(name):  # on Windows, which() also finds name.exe / name.cmd (PATHEXT)
            return found
    # Release zips unpack with their own layout (whisper-bin-x64.zip -> Release/whisper-cli.exe...):
    # look a couple of levels deep inside tools/.
    for name in candidates:
        for pattern in (f"*/*/{exe(name)}", f"*/*/*/{exe(name)}"):
            if hits := sorted(TOOLS.glob(pattern)):
                return str(hits[0])
    return None


def require_tool(names: str | list[str], env_var: str | None = None) -> str:
    found = find_tool(names, env_var)
    if not found:
        first = names if isinstance(names, str) else names[0]
        raise RuntimeError(f"no encuentro «{first}». Ejecuta `uv run reels doctor`: te dice cómo instalarlo en tu sistema.")
    return found


def ffmpeg() -> str:
    return find_tool("ffmpeg", "FFMPEG_BIN") or "ffmpeg"


def ffprobe() -> str:
    return find_tool("ffprobe", "FFPROBE_BIN") or "ffprobe"


# --- Blender ----------------------------------------------------------------------------------------------------


def _version_key(path: Path) -> tuple[int, ...]:
    """Sort key: the highest version number found in the path ("Blender 5.2" > "Blender 4.5")."""
    found = re.findall(r"(\d+)\.(\d+)(?:\.(\d+))?", str(path))
    return max((tuple(int(x or 0) for x in v) for v in found), default=(0,))


def blender_candidates(os_name: str | None = None) -> list[Path]:
    """Where Blender usually lives on each OS (newest first). Not all of them need to exist."""
    os_name = os_name or current_os()
    home = Path.home()
    if os_name == "mac":
        return [Path("/Applications/Blender.app/Contents/MacOS/Blender"),
                home / "Applications/Blender.app/Contents/MacOS/Blender"]
    if os_name == "windows":
        roots = [Path(os.environ.get(v, d)) for v, d in
                 (("ProgramFiles", r"C:\Program Files"), ("ProgramFiles(x86)", r"C:\Program Files (x86)"))]
        found: list[Path] = []
        for r in roots:
            found += r.glob("Blender Foundation/Blender*/blender.exe")
        if local := os.environ.get("LOCALAPPDATA"):
            found += Path(local).glob("Programs/Blender Foundation/Blender*/blender.exe")
        found += TOOLS.glob("blender*/blender.exe")
        return sorted(found, key=_version_key, reverse=True)
    found = [*TOOLS.glob("blender*/blender"), *(home / ".local/opt").glob("blender*/blender"),
             *Path("/opt").glob("blender*/blender"), *home.glob("blender*/blender")]
    return [*sorted(found, key=_version_key, reverse=True), Path("/snap/bin/blender")]


def find_blender() -> str | None:
    if found := find_tool("blender", "BLENDER_BIN"):
        return found
    if os.environ.get("BLENDER_BIN", "").strip():
        return None  # an explicit but wrong BLENDER_BIN must not be silently replaced
    return next((str(p) for p in blender_candidates() if p.is_file()), None)


def blender() -> str:
    found = find_blender()
    if not found:
        raise RuntimeError("no encuentro Blender. Instálalo (`uv run reels doctor` te dice cómo) o pon su ruta en "
                           ".env: BLENDER_BIN=...")
    return found


# --- whisper.cpp, Rhubarb ------------------------------------------------------------------------------------------


def find_whisper() -> str | None:
    # whisper-cli is today's name; whisper-cpp is the old Homebrew one; `main` is the oldest build name.
    return find_tool(["whisper-cli", "whisper-cpp"], "WHISPER_BIN")


def whisper() -> str:
    return require_tool(["whisper-cli", "whisper-cpp"], "WHISPER_BIN")


def whisper_model() -> Path:
    """The ggml model, relative to the project root (so commands work from any folder)."""
    return project_path(os.environ.get("WHISPER_MODEL", "").strip() or DEFAULT_WHISPER_MODEL)


def run_whisper(args: list[str], audio: Path, what: str = "whisper") -> subprocess.CompletedProcess:
    """whisper-cli with its model on `audio`, run from the project folder with relative paths: on Windows it crashes
    (0xC0000409) on an absolute path with accents (see native tools below)."""
    binary, model = whisper(), whisper_model()
    if not model.exists():
        raise RuntimeError(f"falta el modelo de whisper ({model}). Ejecuta `uv run reels doctor`: te dice cómo bajarlo.")
    cmd = [binary, "-m", native_path(model, ROOT), *args, native_path(audio, ROOT)]
    return run_tool(cmd, what, cwd=ROOT, timeout=1800)


def find_rhubarb() -> str | None:
    if found := find_tool("rhubarb", "RHUBARB_BIN"):
        return found
    # The release zip unpacks into Rhubarb-Lip-Sync-<version>-<OS>/rhubarb[.exe].
    hits = sorted([*TOOLS.glob(exe("rhubarb")), *TOOLS.glob(f"[Rr]hubarb*/{exe('rhubarb')}")], key=_version_key, reverse=True)
    return str(hits[0]) if hits else None


def rhubarb() -> str:
    found = find_rhubarb()
    if not found:
        raise RuntimeError("no encuentro Rhubarb Lip Sync. Ejecuta `uv run reels doctor`: te dice cómo instalarlo.")
    return found


# --- ssh (render in the cloud) -------------------------------------------------------------------------------------

SSH_TOOLS = {"ssh": "SSH_BIN", "scp": "SCP_BIN", "ssh-keygen": "SSH_KEYGEN_BIN"}


def ssh_candidates() -> list[Path]:
    """Windows: folders where ssh.exe usually is even when it is not on the PATH (the OpenSSH client of Windows 10/11,
    or the one that comes with Git for Windows, which installs without administrator rights)."""
    if current_os() != "windows":
        return []
    env = os.environ
    dirs = [Path(env.get("SystemRoot", r"C:\Windows")) / "System32" / "OpenSSH"]
    for var, default in (("ProgramFiles", r"C:\Program Files"), ("ProgramW6432", r"C:\Program Files")):
        dirs.append(Path(env.get(var, default)) / "Git" / "usr" / "bin")
    if local := env.get("LOCALAPPDATA"):
        dirs.append(Path(local) / "Programs" / "Git" / "usr" / "bin")
    return dirs


def find_ssh_tool(name: str) -> str | None:
    """ssh, scp or ssh-keygen: .env (SSH_BIN…) → PATH → (Windows) the usual install folders."""
    if found := find_tool(name, SSH_TOOLS.get(name)):
        return found
    if os.environ.get(SSH_TOOLS.get(name, ""), "").strip():
        return None  # an explicit but wrong path must not be silently replaced
    return next((str(d / exe(name)) for d in ssh_candidates() if (d / exe(name)).is_file()), None)


def ssh_tool(name: str) -> str:
    found = find_ssh_tool(name)
    if not found:
        raise RuntimeError(f"no encuentro «{name}» (hace falta para el render en la nube). Ejecuta `uv run reels "
                           "doctor`: te dice cómo instalarlo en tu sistema.")
    return found


# --- processes -----------------------------------------------------------------------------------------------------


def pid_alive(pid: int) -> bool:
    """Is process `pid` still running? (Never os.kill(pid, 0) on Windows: there it would kill the process.)"""
    if pid <= 0:
        return False
    if current_os() == "windows":
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # it exists, it is just someone else's
    except OSError:
        return False
    return True


class exit_cleanly_on_terminate:
    """Context manager: if the OS asks this process to stop (SIGTERM, a closed terminal, Windows' Ctrl+Break or a
    closed console window), raise SystemExit so every `finally` runs. The cloud render needs it: its `finally`
    destroys the rented machine."""

    def __init__(self) -> None:
        self.old: dict = {}

    def _handler(self, signum, frame) -> None:  # noqa: ARG002
        raise SystemExit(128 + int(signum))

    def __enter__(self) -> "exit_cleanly_on_terminate":
        import signal

        names = ["SIGTERM", "SIGHUP", "SIGBREAK"]
        for name in names:
            sig = getattr(signal, name, None)
            if sig is None:
                continue
            try:
                self.old[sig] = signal.signal(sig, self._handler)
            except (ValueError, OSError):  # not the main thread, or not allowed on this OS
                pass
        return self

    def __exit__(self, *exc) -> None:
        import signal

        for sig, old in self.old.items():
            try:
                signal.signal(sig, old)
            except (ValueError, OSError, TypeError):
                pass


# --- native tools and non-ASCII folders (Windows) ------------------------------------------------------------------
# Some C++ tools read their arguments in the old Windows code page instead of Unicode. In a folder like
# "C:\Users\María José\mi fábrica" they cannot open their files (seen in CI):
# - whisper.cpp crashes (exit code 0xC0000409) with an absolute path that has accents; with a relative path, from a
#   working folder that has them, it works.
# - Rhubarb looks for its speech model in res/ next to its own .exe and fails when that path has accents, even
#   through the 8.3 short name (it expands it back). Its .exe must live in an ASCII folder.
# So: these tools run from a working folder with paths relative to it (episode files have ASCII names), and Rhubarb
# is copied once to an ASCII folder that any user can write to without administrator rights.

def is_ascii(text: str | os.PathLike) -> bool:
    return str(text).isascii()


def ascii_base_candidates() -> list[Path]:
    """Folders (Windows) where a copy of a tool can live when the project's path has accents, best first."""
    env = os.environ
    found = [Path(env["PUBLIC"]) if env.get("PUBLIC") else None,  # C:\Users\Public: writable by every user
             Path(env["ProgramData"]) if env.get("ProgramData") else None,  # C:\ProgramData: users may create folders
             Path(env.get("SystemDrive", "C:") + "\\"),
             Path(tempfile.gettempdir())]
    return [p / "fabrica-tools" for p in found if p is not None]


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / f".prueba-{os.getpid()}-{threading.get_ident()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


_ascii_lock = threading.Lock()


def ascii_base() -> Path:
    """The first ASCII, writable folder of `ascii_base_candidates` (created if missing)."""
    for folder in ascii_base_candidates():
        if is_ascii(folder) and _writable(folder):
            return folder
    raise RuntimeError("la ruta de tu proyecto tiene tildes o eñes y no encuentro ninguna carpeta sin ellas donde "
                       "copiar Rhubarb (probé C:\\Users\\Public, C:\\ProgramData, C:\\ y la carpeta temporal). "
                       "Mueve la fábrica a una carpeta sin tildes, por ejemplo C:\\fabrica.")


def ascii_tool(binary: str, extras: tuple[str, ...] = ()) -> str:
    """`binary`, or (Windows, path with accents) a copy of it, its DLLs and the `extras` next to it (Rhubarb: res/)
    in an ASCII folder. The copy is redone only when the original changes, and never half-written (copied aside,
    then renamed)."""
    if current_os() != "windows" or is_ascii(binary):
        return binary
    src = Path(binary)
    stat = src.stat()
    sign = f"{src}|{stat.st_size}|{stat.st_mtime_ns}"
    dest = ascii_base() / f"{src.parent.name}-{hashlib.sha1(str(src.parent).encode()).hexdigest()[:8]}"
    if not is_ascii(dest):  # the original folder name itself has accents
        dest = dest.with_name(f"tool-{hashlib.sha1(str(src.parent).encode()).hexdigest()[:8]}")
    marker = dest / ".copia-de.txt"
    with _ascii_lock:
        if not (marker.exists() and marker.read_text(encoding="utf-8") == sign):
            tmp = dest.with_name(dest.name + f".part-{os.getpid()}")
            shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True)
            for item in [src, *src.parent.glob("*.dll"), *(src.parent / e for e in extras)]:
                if item.is_dir():
                    shutil.copytree(item, tmp / item.name)
                elif item.is_file():
                    shutil.copy2(item, tmp / item.name)
            (tmp / marker.name).write_text(sign, encoding="utf-8")
            shutil.rmtree(dest, ignore_errors=True)
            tmp.replace(dest)
    return str(dest / src.name)


def native_path(path: str | os.PathLike, cwd: str | os.PathLike) -> str:
    """How to name `path` to a tool that reads its arguments in the Windows code page, when it runs from `cwd`:
    unchanged when it is ASCII (or not on Windows), else relative to `cwd`."""
    text = str(path)
    if current_os() != "windows" or is_ascii(text):
        return text
    try:
        rel = os.path.relpath(text, str(cwd))
    except ValueError:  # another drive
        rel = text
    if is_ascii(rel):
        return rel
    raise RuntimeError(f"«{Path(text).name}» está en una carpeta con tildes o eñes ({Path(text).parent}) y las "
                       "herramientas de sonido no saben abrirla en Windows. Muévelo dentro de la fábrica o cambia el "
                       "nombre de la carpeta.")


def tail(text: str | None, lines: int = 6) -> str:
    """The last non-empty lines of a tool's output (where the reason of a failure is)."""
    kept = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return " · ".join(kept[-lines:])


def run_tool(cmd: list[str], what: str, cwd: str | os.PathLike | None = None,
             timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run an external program and, if it fails, raise a plain-Spanish error that names it and says why."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd,
                                timeout=timeout)
    except FileNotFoundError:
        raise RuntimeError(f"no encuentro {what} ({cmd[0]}). Ejecuta `uv run reels doctor`: te dice cómo instalarlo.")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"{what} no ha terminado en {timeout:.0f} s")
    if result.returncode != 0:
        code = result.returncode
        shown = f"0x{code & 0xFFFFFFFF:08X}" if code < 0 or code > 255 else str(code)
        why = tail(result.stderr) or tail(result.stdout) or "no ha dicho por qué"
        raise RuntimeError(f"{what} ha fallado (código {shown}): {why}")
    return result


# --- Node / Remotion -----------------------------------------------------------------------------------------------


def remotion_cmd(remotion_dir: Path) -> list[str]:
    """How to launch the Remotion CLI. Calls node directly (no npx): on Windows `npx` is a .cmd script that
    subprocess cannot start without a shell, and going through cmd.exe would mangle quotes and & in arguments."""
    cli = remotion_dir / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    node = find_tool("node", "NODE_BIN")
    if node and cli.exists():
        return [node, str(cli)]
    if npx := shutil.which("npx"):  # npx.cmd on Windows: which() returns the full path, which subprocess can run
        return [npx, "--no-install", "remotion"]
    if not node:
        raise RuntimeError("no encuentro Node.js. Ejecuta `uv run reels doctor`: te dice cómo instalarlo.")
    raise RuntimeError(f"faltan las piezas de Remotion: entra en {remotion_dir} y ejecuta `npm ci`")


# --- versions ----------------------------------------------------------------------------------------------------


def version_tuple(text: str) -> tuple[int, ...] | None:
    """First x.y[.z] in a program's --version output. ffmpeg git builds ("N-12345-g...") have none."""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(g) for g in m.groups() if g is not None) if m else None


def run_text(cmd: list[str], timeout: float | None = 60) -> str:
    """stdout + stderr of a command as text (always UTF-8, never the Windows ANSI code page)."""
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    return (out.stdout or "") + (out.stderr or "")


def ffmpeg_version(binary: str | None = None) -> tuple[int, ...] | None:
    text = run_text([binary or ffmpeg(), "-hide_banner", "-version"])
    m = re.search(r"ffmpeg version n?(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(g) for g in m.groups() if g is not None) if m else None


def ffmpeg_has_irnorm(binary: str | None = None) -> bool:
    """The voice acoustics (reels/voice.py apply_spaces) use afir's irnorm, missing before ffmpeg 7."""
    return "irnorm" in run_text([binary or ffmpeg(), "-hide_banner", "-h", "filter=afir"])


# --- opening files -------------------------------------------------------------------------------------------------


def open_path(path: str | os.PathLike) -> bool:
    """Open a file or folder with the OS's default app (video player, browser...). Never fails the command."""
    path = str(path)
    try:
        if current_os() == "windows":
            os.startfile(path)  # type: ignore[attr-defined]  # only exists on Windows
        elif current_os() == "mac":
            subprocess.Popen(["open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Not `open`: on Linux that is usually openvt (virtual consoles).
            subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, AttributeError):
        return False


# --- console and downloads -------------------------------------------------------------------------------------------


def setup_console() -> None:
    """Print UTF-8 even when the output is piped (Claude Code reads it through a pipe; on Windows a pipe would
    otherwise use the ANSI code page and crash on ✔ or ñ)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    # Any Python started from here (Blender's own, for instance) also reads and writes UTF-8 by default.
    os.environ.setdefault("PYTHONUTF8", "1")


class keep_awake:
    """Context manager: the computer must not fall asleep during a long render (laptops on battery, lid open).

    Mac: caffeinate tied to this process · Windows: SetThreadExecutionState · Linux: systemd-inhibit when available.
    Best effort: if the OS offers nothing, the render simply runs without it."""

    def __init__(self, why: str = "reels render") -> None:
        self.why = why
        self.proc: subprocess.Popen | None = None

    def __enter__(self) -> "keep_awake":
        try:
            if current_os() == "windows":
                import ctypes

                ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)  # type: ignore[attr-defined]
            elif current_os() == "mac" and shutil.which("caffeinate"):
                self.proc = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
            elif shutil.which("systemd-inhibit"):
                self.proc = subprocess.Popen(
                    ["systemd-inhibit", "--what=sleep:idle", "--who=reels", f"--why={self.why}", "--mode=block",
                     "sleep", "infinity"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, AttributeError):
            self.proc = None
        return self

    def __exit__(self, *exc) -> None:
        try:
            if current_os() == "windows":
                import ctypes

                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # type: ignore[attr-defined]
            if self.proc:
                self.proc.terminate()
        except (OSError, AttributeError):
            pass


def download(url: str, dest: Path) -> Path:
    """Download a big file with a progress bar; a half-finished download never looks like a finished one."""
    import httpx
    from rich.progress import BarColumn, DownloadColumn, Progress, TimeRemainingColumn, TransferSpeedColumn

    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0)) or None
        columns = ("{task.description}", BarColumn(), DownloadColumn(), TransferSpeedColumn(), TimeRemainingColumn())
        with Progress(*columns) as progress, part.open("wb") as fh:
            task = progress.add_task(dest.name, total=total)
            for chunk in r.iter_bytes(1 << 20):
                fh.write(chunk)
                progress.advance(task, len(chunk))
    part.replace(dest)
    return dest
