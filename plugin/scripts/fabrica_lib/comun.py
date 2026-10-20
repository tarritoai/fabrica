"""Shared helpers: plain-Spanish output, the install log, errors with a code the tutor understands, OS facts,
running programs and keeping the computer awake. Standard library only."""

from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

OK, AVISO, FALLO, INFO = "✔", "!", "✘", "·"


# --- errors --------------------------------------------------------------------------------------------------------


class FabricaError(Exception):
    """A failure explained for a beginner. `codigo` is the id of the matching row in the known-errors table
    (plugin/scripts/fabrica_lib/errores.json), so the tutor can give the full explanation."""

    def __init__(self, mensaje: str, codigo: str = "desconocido", pista: str = "") -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.pista = pista


# --- output and log ------------------------------------------------------------------------------------------------


def setup_console() -> None:
    """UTF-8 output even through a pipe (Claude Code reads our output through one; on Windows a pipe would use
    the ANSI code page and crash on ✔ or ñ)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    os.environ.setdefault("PYTHONUTF8", "1")


class Log:
    """Everything we print also goes to a log file (with the raw output of the programs we run)."""

    path: Path | None = None

    @classmethod
    def abrir(cls, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        cls.path = path
        cls.escribir(f"\n===== {_dt.datetime.now().isoformat(timespec='seconds')} · {' '.join(sys.argv[1:])} =====")

    @classmethod
    def escribir(cls, texto: str) -> None:
        if not cls.path:
            return
        try:
            with cls.path.open("a", encoding="utf-8") as fh:
                fh.write(texto.rstrip("\n") + "\n")
        except OSError:
            pass


def decir(texto: str = "", icono: str = "") -> None:
    linea = f"{icono} {texto}" if icono else texto
    print(linea, flush=True)
    Log.escribir(linea)


def titulo(texto: str) -> None:
    decir()
    decir(f"── {texto} ──")


# --- where things live ---------------------------------------------------------------------------------------------


def sistema() -> str:
    """'windows', 'mac' or 'linux'."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def arquitectura() -> str:
    """'x64' or 'arm64' (what download names use)."""
    m = platform.machine().lower()
    if m in ("arm64", "aarch64", "armv8l"):
        return "arm64"
    if m in ("x86_64", "amd64", "x64"):
        return "x64"
    return m


def plataforma() -> str:
    """'linux-x64', 'mac-arm64', 'windows-x64'..."""
    return f"{sistema()}-{arquitectura()}"


def carpeta_cache() -> Path:
    """Where downloads wait (and resume) before being unpacked. FABRICA_CACHE overrides it (the CI caches it)."""
    if env := os.environ.get("FABRICA_CACHE", "").strip():
        return Path(env).expanduser()
    if sistema() == "windows":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "fabrica" / "descargas"
    if sistema() == "mac":
        return Path.home() / "Library" / "Caches" / "fabrica" / "descargas"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "fabrica" / "descargas"


def guardar_descargas() -> bool:
    """Keep the downloaded archives after unpacking? Only when a cache folder was asked for (CI): a student's
    disk is precious (a 256 GB laptop) and the tools are already unpacked in their project."""
    return bool(os.environ.get("FABRICA_CACHE", "").strip()) or os.environ.get("FABRICA_GUARDAR_DESCARGAS") == "1"


def carpeta_claude() -> Path:
    """Claude Code's configuration folder (settings.json, plugins/)."""
    if env := os.environ.get("CLAUDE_CONFIG_DIR", "").strip():
        return Path(env).expanduser()
    return Path.home() / ".claude"


def raiz_plugin() -> Path:
    """plugin/ (this file is plugin/scripts/fabrica_lib/comun.py)."""
    return Path(__file__).resolve().parent.parent.parent


def version_plugin(raiz: Path | None = None) -> str:
    try:
        data = json.loads(((raiz or raiz_plugin()) / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        return str(data.get("version", "0"))
    except (OSError, ValueError):
        return "0"


def version_tupla(texto: str) -> tuple[int, ...]:
    partes = []
    for p in texto.strip().lstrip("v").split("."):
        num = "".join(ch for ch in p if ch.isdigit())
        partes.append(int(num) if num else 0)
    return tuple(partes)


# --- running programs ----------------------------------------------------------------------------------------------


def entorno_limpio(extra_path: list[Path] | None = None) -> dict[str, str]:
    """Environment for the programs we start: UTF-8, no leftovers of the uv environment we run in."""
    env = dict(os.environ)
    for var in ("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "UV_RUN_RECURSION_DEPTH", "CONDA_PREFIX"):
        env.pop(var, None)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if extra_path:
        env["PATH"] = os.pathsep.join([*(str(p) for p in extra_path), env.get("PATH", "")])
    return env


def ejecutar(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None,
             timeout: float | None = None, mostrar: bool = False, prefijo: str = "    ") -> subprocess.CompletedProcess:
    """Run a program (argument list, never a shell). Its output always goes to the log; with `mostrar`, also to the
    screen as it happens (long steps: the student sees life). Returns the result with .stdout (text)."""
    Log.escribir(f"$ {' '.join(cmd)}" + (f"   (en {cwd})" if cwd else ""))
    if not mostrar:
        try:
            r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired as e:
            Log.escribir(f"(se pasó de tiempo: {timeout} s)")
            raise FabricaError(f"«{Path(cmd[0]).name}» tardó demasiado y lo he parado", "tiempo-agotado") from e
        salida = (r.stdout or "") + (r.stderr or "")
        Log.escribir(salida)
        Log.escribir(f"(código de salida {r.returncode})")
        return subprocess.CompletedProcess(cmd, r.returncode, salida, "")
    lineas: list[str] = []
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", bufsize=1)
    inicio = time.time()
    assert proc.stdout is not None
    for linea in proc.stdout:
        linea = linea.rstrip("\r\n")
        lineas.append(linea)
        Log.escribir(linea)
        # Progress bars of other tools redraw with \r: keep only what a person can read.
        visible = linea.split("\r")[-1].strip()
        if visible:
            print(prefijo + visible, flush=True)
        if timeout and time.time() - inicio > timeout:
            proc.kill()
            raise FabricaError(f"«{Path(cmd[0]).name}» tardó demasiado y lo he parado", "tiempo-agotado")
    proc.wait()
    Log.escribir(f"(código de salida {proc.returncode})")
    return subprocess.CompletedProcess(cmd, proc.returncode, "\n".join(lineas), "")


def primera_linea(texto: str) -> str:
    return next((ln.strip() for ln in texto.splitlines() if ln.strip()), "")


# --- facts about this computer -------------------------------------------------------------------------------------


def memoria_gb() -> float | None:
    try:
        if sistema() == "linux":
            for ln in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
                if ln.startswith("MemTotal:"):
                    return int(ln.split()[1]) / 1024 / 1024
        if sistema() == "mac":
            return int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True).stdout) / 1024**3
        if sistema() == "windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]

            st = MEMORYSTATUSEX()
            st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))  # type: ignore[attr-defined]
            return st.ullTotalPhys / 1024**3
    except (OSError, ValueError, AttributeError):
        return None
    return None


def espacio_libre_gb(path: Path) -> float | None:
    p = path
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        return shutil.disk_usage(p).free / 1024**3
    except OSError:
        return None


def linux_distro() -> dict[str, str]:
    datos: dict[str, str] = {}
    try:
        for ln in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in ln:
                k, v = ln.split("=", 1)
                datos[k] = v.strip().strip('"')
    except OSError:
        pass
    return datos


def glibc() -> tuple[int, ...]:
    nombre, version = platform.libc_ver()
    return version_tupla(version) if nombre == "glibc" and version else (0,)


# --- keep the computer awake (mirror of reels/system.py keep_awake: this runs before the project exists) ---------


class despierto:
    """The computer must not fall asleep during long downloads or the first render.
    Mac: caffeinate · Windows: SetThreadExecutionState · Linux: systemd-inhibit. Best effort, never fails."""

    def __init__(self, motivo: str = "instalando la fábrica") -> None:
        self.motivo = motivo
        self.proc: subprocess.Popen | None = None

    def __enter__(self) -> "despierto":
        try:
            if sistema() == "windows":
                import ctypes

                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # type: ignore[attr-defined]
            elif sistema() == "mac" and shutil.which("caffeinate"):
                self.proc = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())])
            elif shutil.which("systemd-inhibit"):
                self.proc = subprocess.Popen(
                    ["systemd-inhibit", "--what=sleep:idle", "--who=fabrica", f"--why={self.motivo}", "--mode=block",
                     "sleep", "infinity"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, AttributeError):
            self.proc = None
        return self

    def __exit__(self, *exc) -> None:
        try:
            if sistema() == "windows":
                import ctypes

                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # type: ignore[attr-defined]
            if self.proc:
                self.proc.terminate()
        except (OSError, AttributeError):
            pass


# --- small file helpers --------------------------------------------------------------------------------------------


def leer_json(path: Path, defecto=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def escribir_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def borrar(path: Path) -> None:
    """Remove a file or folder, retrying a little (on Windows the antivirus holds fresh files for a moment)."""
    for intento in range(5):
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(ruta_larga(path))
            elif path.exists() or path.is_symlink():
                path.unlink()
            return
        except OSError:
            if intento == 4:
                raise
            time.sleep(1 + intento)


def mover(origen: Path, destino: Path) -> None:
    """Rename a file or folder, retrying a little: on Windows an antivirus scanning freshly unpacked files makes the
    first attempts fail with «Access is denied» (WinError 5)."""
    for intento in range(8):
        try:
            os.replace(ruta_larga(origen), ruta_larga(destino))
            return
        except PermissionError:
            if intento == 7:
                raise
            time.sleep(1 + intento)


def ruta_larga(path: Path) -> str:
    """On Windows, the \\\\?\\ form lifts the 260-character limit (deep folders inside Blender or node_modules
    under C:\\Users\\María José\\...). Elsewhere, the path as is."""
    texto = str(path)
    if sistema() == "windows" and not texto.startswith("\\\\?\\"):
        texto = os.path.abspath(texto)
        return "\\\\?\\UNC\\" + texto[2:] if texto.startswith("\\\\") else "\\\\?\\" + texto
    return texto


# --- one installer at a time per project ---------------------------------------------------------------------------


def _vivo(pid: int) -> bool:
    if pid <= 0:
        return False
    if sistema() == "windows":
        import ctypes

        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class candado:
    """A lock file in <project>/.fabrica: a second copy of the installer (a double click, two Claude windows) waits
    for nobody and explains instead of fighting over the same downloads."""

    def __init__(self, proyecto: Path) -> None:
        self.path = proyecto / ".fabrica" / "en-marcha.lock"

    def __enter__(self) -> "candado":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            otro = int(self.path.read_text(encoding="utf-8").split()[0])
        except (OSError, ValueError, IndexError):
            otro = 0
        if otro and otro != os.getpid() and _vivo(otro):
            raise FabricaError(f"ya hay otra instalación trabajando en esta carpeta (proceso {otro})", "en-marcha",
                               "espera a que termine (o ciérrala) y repite este paso")
        self.path.write_text(f"{os.getpid()} {' '.join(sys.argv[1:])}\n", encoding="utf-8")
        return self

    def __exit__(self, *exc) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass
