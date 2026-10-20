"""The programs the factory needs, installed WITHOUT administrator rights inside the student's project (tools/),
with pinned versions and checksums. Each tool: download (resumable) → check SHA-256 → unpack → run it once →
write its path in .env (BLENDER_BIN, FFMPEG_BIN...), which reels/system.py reads first.

Idempotent: a tool already installed at the pinned version and that still runs is skipped.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import descargas
from .comun import (FabricaError, borrar, carpeta_cache, decir, ejecutar, entorno_limpio, escribir_json,
                    guardar_descargas, leer_json, mover, plataforma, primera_linea, sistema)

# --- pinned versions (change them here; CI caches downloads by the hash of this file) -------------------------------

BLENDER = "5.2.2"
NODE = "24.22.0"
RHUBARB = "1.14.0"
WHISPER = "1.9.5"
WHISPER_BUILD = "b5454"  # the release that carries the 1.9.5 binaries (the v1.9.x tags have no files attached)
FFMPEG = "9.0"
FFMPEG_MAC = "9.0.2"

GH = "https://github.com"
BLENDER_URL = f"https://download.blender.org/release/Blender{BLENDER.rsplit('.', 1)[0]}/blender-{BLENDER}"
BTBN = f"{GH}/BtbN/FFmpeg-Builds/releases/download/latest"
RIEDL = "https://ffmpeg.martin-riedl.de"
RIEDL_PINNED = f"{RIEDL}/download/macos/arm64/1789931890_{FFMPEG_MAC}"
WHISPER_REL = f"{GH}/ggml-org/whisper.cpp/releases/download/{WHISPER_BUILD}"
RHUBARB_REL = f"{GH}/DanielSWolf/rhubarb-lip-sync/releases/download/v{RHUBARB}/Rhubarb-Lip-Sync-{RHUBARB}"
NODE_DIST = f"https://nodejs.org/dist/v{NODE}/node-v{NODE}"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
# Same file (MIT licence), same SHA-256, uploaded by the course to a release of its repo: used when Hugging Face's
# CDN crawls. Until that release exists the URL answers 404 and only Hugging Face is used.
MODEL_URLS = [MODEL_URL, f"{GH}/tarritoai/fabrica/releases/download/modelos/ggml-small.bin"]
MODEL_SHA = "1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b"
MODEL_SIZE = 487601967
EMOJI_URL = f"{GH}/googlefonts/noto-emoji/raw/v2.051/fonts/NotoColorEmoji.ttf"
EMOJI_SHA = "72a635cb3d2f3524c51620cdde406b217204e8a6a06c6a096ff8ed4b5fd6e27b"
WHISPER_SRC = f"{GH}/ggml-org/whisper.cpp/archive/refs/tags/v{WHISPER}.tar.gz"
WHISPER_SRC_SHA = "ff1a9053feb509ff9d7729703355541ae9690073a6b1c40eb692c962e0dc1720"
# Microsoft's C++ runtime DLLs (redistributable), copied next to whisper-cli.exe so a Windows without the
# "Visual C++ Redistributable" (which needs an administrator to install) still runs it. From PyPI "msvc-runtime".
CRT = {
    "windows-x64": ("https://files.pythonhosted.org/packages/21/3b/134d04268ab8e35853cd007582076429b45d60d6abb1036d159be9c50342/"
                    "msvc_runtime-14.44.35112-cp312-cp312-win_amd64.whl",
                    "32f9c706009e16ccc319d6947ce3bffe20e5192bee52b18cf48313f9e7bedfbe"),
    "windows-arm64": ("https://files.pythonhosted.org/packages/a0/38/f245d6d30a76655293575683aaa5f72a7a70fc8efa1637bf6fd9e5e7e665/"
                      "msvc_runtime-14.44.35112-cp312-cp312-win_arm64.whl",
                      "62f272c51f30ce0de1b7a796e50af4d3911b76cbc9bc909917435d094f68d5fe"),
}


@dataclass
class Fuente:
    url: str
    sha256: str | None = None          # pinned digest
    sha256_de: str | None = None       # or: a checksums file published next to it ("<hash>  <name>" lines)
    nombre: str | None = None          # file name in the download cache


@dataclass
class Spec:
    nombre: str                        # shown to the student
    version: str
    carpeta: str                       # tools/<carpeta>
    binario: str                       # inside tools/<carpeta>
    fuentes: list[Fuente] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)  # .env variable -> path inside tools/<carpeta>
    alternativas: list[Fuente] = field(default_factory=list)  # other places to download the same thing from


def _exe(nombre: str) -> str:
    return nombre + ".exe" if sistema() == "windows" else nombre


def specs(plat: str | None = None) -> dict[str, Spec]:
    """What to install on this platform ('linux-x64', 'mac-arm64', 'windows-x64'...)."""
    plat = plat or plataforma()
    so = plat.split("-")[0]
    e = (lambda n: n + ".exe") if so == "windows" else (lambda n: n)
    out: dict[str, Spec] = {}

    blender = {
        "linux-x64": Fuente(f"{BLENDER_URL}-linux-x64.tar.xz", "84098912789dc450e95697c4184fb8a90acbe5111c2ba4aede3fecb57806a168"),
        "windows-x64": Fuente(f"{BLENDER_URL}-windows-x64.zip", "3849d17a682cba006075aaa3f3597ecb5c9c30ec31035b2e092c53e40679b535"),
        "windows-arm64": Fuente(f"{BLENDER_URL}-windows-arm64.zip", "2e90b53c9443cc56d2be75a61550a38e4aba942c8cded046ceff98ed58ebc67b"),
        "mac-arm64": Fuente(f"{BLENDER_URL}-macos-arm64.dmg", "dc4125399b8bfefe283cc1624d6cfc7809d1cac20ace51072127eb371f31f210"),
    }
    if plat in blender:
        binario = "Blender.app/Contents/MacOS/Blender" if so == "mac" else e("blender")
        out["blender"] = Spec("Blender (escena 3D)", BLENDER, f"blender-{BLENDER}", binario, [blender[plat]],
                              {"BLENDER_BIN": binario})

    if so == "mac":
        out["ffmpeg"] = Spec("ffmpeg (vídeo y sonido)", FFMPEG_MAC, f"ffmpeg-{FFMPEG}", "ffmpeg", [
            Fuente(f"{RIEDL_PINNED}/ffmpeg.zip", "c8ed4c4e6978a03c485edbfe4e0a5dc2380f8a30bba5150531b31b094492d924", nombre=f"ffmpeg-{FFMPEG_MAC}-macos-arm64.zip"),
            Fuente(f"{RIEDL_PINNED}/ffprobe.zip", "fcbe839537485eaee7a7a8bc5cbc0f90d53617e80943e8a5b2e31cb851197ea6", nombre=f"ffprobe-{FFMPEG_MAC}-macos-arm64.zip"),
        ], {"FFMPEG_BIN": "ffmpeg", "FFPROBE_BIN": "ffprobe"})
    else:
        tag = {"linux-x64": "linux64", "linux-arm64": "linuxarm64", "windows-x64": "win64", "windows-arm64": "winarm64"}.get(plat)
        if tag:
            ext = "zip" if so == "windows" else "tar.xz"
            name = f"ffmpeg-n{FFMPEG}-latest-{tag}-gpl-{FFMPEG}.{ext}"
            fuentes = [Fuente(f"{BTBN}/{name}", sha256_de=f"{BTBN}/checksums.sha256")]
            if plat == "windows-x64":  # second builder, in case GitHub is unreachable
                fuentes.append(Fuente("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
                                      sha256_de="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256"))
            out["ffmpeg"] = Spec("ffmpeg (vídeo y sonido)", FFMPEG, f"ffmpeg-{FFMPEG}", f"bin/{e('ffmpeg')}", fuentes[:1],
                                 {"FFMPEG_BIN": f"bin/{e('ffmpeg')}", "FFPROBE_BIN": f"bin/{e('ffprobe')}"},
                                 alternativas=fuentes[1:])

    whisper = {
        "linux-x64": Fuente(f"{WHISPER_REL}/whisper-bin-ubuntu-x64.tar.gz", "a72becf15d7917f990f6313867a52638b82b7f9ef237fb0c980dac56a135781c", nombre=f"whisper-{WHISPER}-ubuntu-x64.tar.gz"),
        "linux-arm64": Fuente(f"{WHISPER_REL}/whisper-bin-ubuntu-arm64.tar.gz", "6b95ebfc60447df48e70ef00a73bdc3f41679ed2d01ef465827206a2ff325149", nombre=f"whisper-{WHISPER}-ubuntu-arm64.tar.gz"),
        "windows-x64": Fuente(f"{WHISPER_REL}/whisper-bin-x64.zip", "6ba69e3482d7826214f90a6a9c84ca07782aec1e1d0c6a7c30c994fd5d816ccb", nombre=f"whisper-{WHISPER}-win-x64.zip"),
        "windows-arm64": Fuente(f"{WHISPER_REL}/whisper-bin-win-cpu-arm64.zip", "28c37e7b598c3d9bbfef94f3bd67f2ee6f12b7c86f3da5edcf5e4308d615ff6d", nombre=f"whisper-{WHISPER}-win-arm64.zip"),
    }
    # Mac: no official command-line binary exists → Homebrew, or built here from the pinned source (see _whisper_mac).
    out["whisper"] = Spec("whisper.cpp (el oído)", WHISPER, f"whisper-{WHISPER}", e("whisper-cli"),
                          [whisper[plat]] if plat in whisper else [], {"WHISPER_BIN": e("whisper-cli")})

    rh_os = {"linux": "Linux", "mac": "macOS", "windows": "Windows"}[so]
    rh_sha = {"Linux": "a9a9074862cff47b2d59b8bf399a678a3b0b74f9452ad6ad94cb292913dd8667",
              "macOS": "f991deacac6c973a14a4431a16a58b842f436531e120cfaea142c87c0d3ab4c5",
              "Windows": "62fa416a8d5e382a3828ee4bef358ce520d0b4cabdeaea75a7ac266d098d1fe3"}[rh_os]
    if plat != "linux-arm64":  # Rhubarb only ships x86-64 builds (Mac: Rosetta; Windows on ARM: emulation)
        out["rhubarb"] = Spec("Rhubarb (labios)", RHUBARB, f"rhubarb-{RHUBARB}", e("rhubarb"),
                              [Fuente(f"{RHUBARB_REL}-{rh_os}.zip", rh_sha)], {"RHUBARB_BIN": e("rhubarb")})

    node = {
        "linux-x64": ("linux-x64.tar.xz", "cc2f601cee82d9a5a233302fe307abc600727035fd7d2c3a3571755989e95008"),
        "linux-arm64": ("linux-arm64.tar.xz", "fef00bb4d36e1c50104a9775a10359beee98f162b4104dd12472c75065c6a143"),
        "mac-arm64": ("darwin-arm64.tar.gz", "6a9724d9b50a5f22b4816cded441b5a8d9ddae546191a5e5b7efa5a5e2ee26d5"),
        "windows-x64": ("win-x64.zip", "f9683a19877e12a9b167305c8db71040d812876359de21f0d2e97c3f321f80c3"),
    }
    if plat in node:
        suf, sha = node[plat]
        binario = "node.exe" if so == "windows" else "bin/node"
        out["node"] = Spec("Node.js (pantallas y montaje)", NODE, f"node-{NODE}", binario,
                           [Fuente(f"{NODE_DIST}-{suf}", sha)], {"NODE_BIN": binario})
    return out


ORDEN = ["blender", "ffmpeg", "whisper", "modelo", "rhubarb", "node", "emojis"]
NOMBRES = {"modelo": "modelo de whisper (~490 MB)", "emojis": "fuente de emojis"}


# --- bookkeeping (tools/.fabrica.json) and .env --------------------------------------------------------------------


def _registro(proyecto: Path) -> dict:
    return leer_json(proyecto / "tools" / ".fabrica.json", {}) or {}


def _guardar_registro(proyecto: Path, reg: dict) -> None:
    escribir_json(proyecto / "tools" / ".fabrica.json", reg)


INICIO_ENV = "# >>> herramientas: las escribe /fabrica:instalar (no edites entre estas dos líneas) >>>"
FIN_ENV = "# <<< herramientas <<<"


def escribir_env(proyecto: Path) -> None:
    """Write the managed block of .env with the path of every installed tool (relative to the project, forward
    slashes, single quotes: python-dotenv would read \\n inside double quotes as a newline). Keys outside the block
    (the student's own) are never touched."""
    env = proyecto / ".env"
    if not env.exists():
        ejemplo = proyecto / ".env.example"
        env.write_text(ejemplo.read_text(encoding="utf-8") if ejemplo.exists() else "", encoding="utf-8")
    texto = env.read_text(encoding="utf-8")
    if INICIO_ENV in texto and FIN_ENV in texto:
        antes, resto = texto.split(INICIO_ENV, 1)
        despues = resto.split(FIN_ENV, 1)[1]
    else:
        antes, despues = texto, ""
    reg = _registro(proyecto)
    lineas = []
    for clave in ORDEN:
        for var, ruta in (reg.get(clave, {}).get("env") or {}).items():
            lineas.append(f"{var}='{ruta}'")
    for var, valor in (reg.get("_extra") or {}).items():
        lineas.append(f"{var}='{valor}'")
    bloque = "\n".join([INICIO_ENV, *lineas, FIN_ENV])
    nuevo = antes.rstrip("\n") + "\n\n" + bloque + "\n" + despues.lstrip("\n")
    env.write_text(nuevo, encoding="utf-8")


def poner_extra(proyecto: Path, var: str, valor: str | None) -> None:
    """A setting of the managed .env block that is not a tool path (e.g. REELS_RENDER_ENGINE=cycles)."""
    reg = _registro(proyecto)
    extra = reg.setdefault("_extra", {})
    if valor is None:
        extra.pop(var, None)
    else:
        extra[var] = valor
    _guardar_registro(proyecto, reg)
    escribir_env(proyecto)


def _rel(proyecto: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(proyecto.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


# --- checking that a tool really runs ------------------------------------------------------------------------------


def probar(clave: str, binario: Path) -> tuple[bool, str]:
    """Run the tool once. (True, version line) or (False, why)."""
    if not binario.exists():
        return False, f"no existe {binario}"
    args = {"blender": ["--version"], "ffmpeg": ["-hide_banner", "-version"], "whisper": ["--help"],
            "rhubarb": ["--version"], "node": ["--version"]}[clave]
    try:
        r = subprocess.run([str(binario), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=180, env=entorno_limpio())
    except OSError as e:
        if sistema() == "mac" and getattr(e, "errno", None) == 86:
            return False, "Bad CPU type in executable"
        return False, str(e)
    except subprocess.TimeoutExpired:
        return False, "no responde (tardó más de 3 minutos)"
    salida = (r.stdout or "") + (r.stderr or "")
    if clave == "whisper":
        ok = "usage" in salida.lower()
    else:
        ok = r.returncode == 0
    if r.returncode in (3221225781, -1073741515):  # Windows STATUS_DLL_NOT_FOUND
        return False, "le falta una DLL de Windows (0xC0000135)"
    if ok and clave == "whisper":
        return True, "responde"  # --help prints usage with the full path: nothing useful to show
    return ok, primera_linea(salida) if ok else (primera_linea(salida) or f"código de salida {r.returncode}")


def _probar_ffmpeg_completo(binario: Path) -> str | None:
    """The factory needs ffmpeg >= 7 (afir's irnorm) with libx264. None if fine, else the problem."""
    filtro = subprocess.run([str(binario), "-hide_banner", "-h", "filter=afir"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace").stdout
    if "irnorm" not in filtro:
        return "este ffmpeg es demasiado viejo (le falta afir irnorm)"
    enc = subprocess.run([str(binario), "-hide_banner", "-encoders"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    if "libx264" not in enc:
        return "este ffmpeg no trae libx264"
    return None


# --- install one tool ----------------------------------------------------------------------------------------------


def instalar(clave: str, proyecto: Path, forzar: bool = False) -> None:
    """Install one tool (see ORDEN) into proyecto/tools. Raises FabricaError with a plain explanation."""
    tools = proyecto / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    if clave == "modelo":
        return _modelo(proyecto, forzar)
    if clave == "emojis":
        return _emojis()
    todas = specs()
    if clave not in todas:
        if clave == "blender" and sistema() == "mac":
            raise FabricaError("Blender 5 solo funciona en Mac con chip Apple (M1 o posterior)", "mac-intel")
        if clave == "blender":
            raise FabricaError(f"Blender no publica versión para {plataforma()}", "plataforma-no-soportada")
        decir(f"{clave}: no hace falta en {plataforma()}", "·")
        return
    spec = todas[clave]
    reg = _registro(proyecto)
    previo = reg.get(clave)
    destino = tools / spec.carpeta
    if previo and previo.get("version") == spec.version and not forzar:
        binario = proyecto / previo["bin"] if not Path(previo["bin"]).is_absolute() else Path(previo["bin"])
        ok, info = probar(clave, binario)
        if ok:
            decir(f"{spec.nombre}: ya está ({info})", "✔")
            return
        decir(f"{spec.nombre}: estaba instalado pero no arranca ({info}); lo reinstalo", "!")
    decir(f"{spec.nombre} {spec.version}", "→")

    if clave == "whisper" and sistema() == "mac":
        binario = _whisper_mac(proyecto, spec)
        env = {"WHISPER_BIN": _rel(proyecto, binario)}
    else:
        if clave == "blender" and sistema() == "mac":
            _blender_mac(spec, destino)
        else:
            _bajar_y_extraer(clave, spec, destino)
        binario = destino / spec.binario
        env = {var: _rel(proyecto, destino / ruta) for var, ruta in spec.env.items()}
        _despues(clave, spec, destino, binario, proyecto)

    ok, info = probar(clave, binario)
    if not ok and clave == "whisper" and sistema() == "linux" and "libgomp" in info:
        decir("a whisper.cpp le falta libgomp (OpenMP); copio la de tu sistema a su carpeta, sin contraseña", "!")
        if _libgomp_linux(binario.parent):
            ok, info = probar(clave, binario)
    if not ok and clave == "whisper" and sistema() == "linux":
        decir(f"whisper.cpp descargado no arranca en este Linux ({info}); intento construirlo aquí", "!")
        binario = _compilar_whisper(proyecto, spec)
        env = {"WHISPER_BIN": _rel(proyecto, binario)}
        ok, info = probar(clave, binario)
    if not ok:
        codigo = {"Bad CPU type in executable": "mac-rosetta"}.get(info, f"{clave}-no-arranca")
        if "0xC0000135" in info:
            codigo = "windows-dll"
        raise FabricaError(f"{spec.nombre} se ha instalado pero no arranca: {info}", codigo)
    if clave == "ffmpeg" and (problema := _probar_ffmpeg_completo(binario)):
        raise FabricaError(f"ffmpeg: {problema}", "ffmpeg-viejo")
    reg[clave] = {"version": spec.version, "bin": _rel(proyecto, binario), "env": env}
    _guardar_registro(proyecto, reg)
    escribir_env(proyecto)
    decir(f"{spec.nombre}: listo ({info})", "✔")


def _sha_de_lista(fuente: Fuente, nombre: str) -> str:
    for ln in descargas.texto(fuente.sha256_de or "").splitlines():
        partes = ln.split()
        if len(partes) == 1 and len(partes[0]) == 64:
            return partes[0]  # gyan.dev: the file holds just the hash
        if len(partes) >= 2 and partes[-1].lstrip("*") == nombre:
            return partes[0]
    raise FabricaError(f"no encuentro la huella de seguridad de {nombre}", "descarga-hash")


def _bajar(fuente: Fuente, etiqueta: str) -> Path:
    nombre = fuente.nombre or fuente.url.rsplit("/", 1)[-1]
    archivo = carpeta_cache() / nombre
    sha = fuente.sha256
    for intento in (1, 2):
        if not sha and fuente.sha256_de:
            sha = _sha_de_lista(fuente, fuente.url.rsplit("/", 1)[-1])
        try:
            return descargas.descargar(fuente.url, archivo, sha256=sha, nombre=etiqueta)
        except FabricaError as e:
            # "latest" builds are rebuilt daily: the published hash may have moved while we downloaded.
            if e.codigo == "descarga-hash" and fuente.sha256_de and intento == 1:
                sha = None
                continue
            raise
    raise AssertionError


def _archivos(clave: str, spec: Spec) -> list[Path]:
    """Download what a tool needs (one archive; two on a Mac for ffmpeg + ffprobe), trying the alternatives."""
    if sistema() == "mac" and clave == "ffmpeg":
        try:
            return [_bajar(f, spec.nombre) for f in spec.fuentes]
        except FabricaError as e:
            if e.codigo != "descarga-404":
                raise
            decir("ffmpeg: la versión fijada ya no está en la web; bajo la más reciente de la misma fuente", "!")
            carpeta = url_redirigida(f"{RIEDL}/redirect/latest/macos/arm64/release/ffmpeg.zip").rsplit("/", 1)[0]
            return [_bajar(Fuente(f"{carpeta}/{n}.zip", sha256_de=f"{carpeta}/{n}.zip.sha256",
                                  nombre=f"{n}-latest-macos-arm64.zip"), spec.nombre) for n in ("ffmpeg", "ffprobe")]
    fuentes = [*spec.fuentes, *spec.alternativas]
    for i, fuente in enumerate(fuentes):
        try:
            return [_bajar(fuente, spec.nombre)]
        except FabricaError as e:
            if i + 1 == len(fuentes) or e.codigo not in ("descarga-404", "sin-conexion", "descarga-hash"):
                raise
            decir(f"{spec.nombre}: esa web de descarga falla ({e}); pruebo otra", "!")
    raise FabricaError(f"{spec.nombre}: no hay de dónde descargarlo en {plataforma()}", "plataforma-no-soportada")


def _bajar_y_extraer(clave: str, spec: Spec, destino: Path) -> None:
    archivos = _archivos(clave, spec)
    decir(f"{spec.nombre}: descomprimiendo…", "·")
    tmp = destino.with_name(destino.name + ".nuevo")
    if tmp.exists():
        borrar(tmp)
    tmp.mkdir(parents=True)
    for archivo in archivos:
        parcial = tmp / ("_" + archivo.name)
        descargas.extraer(archivo, parcial)
        interior = descargas.una_sola_carpeta(parcial)
        for hijo in list(interior.iterdir()):
            mover(hijo, tmp / hijo.name)
        borrar(parcial)
        if not guardar_descargas():
            borrar(archivo)
    if destino.exists():
        borrar(destino)
    mover(tmp, destino)
    if sistema() != "windows":
        for ruta in spec.env.values():
            p = destino / ruta
            if p.exists():
                p.chmod(0o755)


def _despues(clave: str, spec: Spec, destino: Path, binario: Path, proyecto: Path) -> None:
    """Per-OS touches after unpacking."""
    if sistema() == "mac":
        # Files we downloaded ourselves carry no quarantine flag, but if the student copied a folder from a browser
        # download they would: clearing it is harmless and needs no password (they are their own files).
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(destino)], capture_output=True)
        if clave == "rhubarb":
            _rosetta()
    if sistema() == "windows" and clave == "whisper":
        _crt_windows(destino)


def _crt_windows(carpeta: Path) -> None:
    """Copy Microsoft's C++ runtime DLLs next to whisper-cli.exe (app-local deployment): works on a Windows that never
    installed the Visual C++ Redistributable, without administrator rights."""
    url, sha = CRT.get(plataforma(), CRT["windows-x64"])
    whl = _bajar(Fuente(url, sha), "librerías de Windows para whisper")
    tmp = carpeta.with_name(carpeta.name + ".crt")
    descargas.extraer(whl, tmp)
    origen = next(tmp.glob("*.data/data/Scripts"), None)
    for dll in (origen.glob("*.dll") if origen else []):
        if not (carpeta / dll.name).exists():
            shutil.copy2(dll, carpeta / dll.name)
    borrar(tmp)


def _libgomp_linux(carpeta: Path) -> bool:
    """whisper.cpp's Linux build needs libgomp.so.1 (GCC's OpenMP runtime), present on desktop distros but not on
    minimal ones. Without administrator: `apt-get download` fetches the distro's own package into a temporary folder
    (no root needed), `dpkg-deb -x` unpacks it, and the library goes next to whisper-cli (its RUNPATH is $ORIGIN)."""
    if not (shutil.which("apt-get") and shutil.which("dpkg-deb")):
        return False
    with tempfile.TemporaryDirectory(prefix="fabrica-libgomp-") as tmp:
        r = ejecutar(["apt-get", "download", "libgomp1"], cwd=Path(tmp), timeout=300)
        deb = next(Path(tmp).glob("libgomp1_*.deb"), None)
        if r.returncode != 0 or not deb:
            return False
        if ejecutar(["dpkg-deb", "-x", str(deb), str(Path(tmp) / "x")], timeout=120).returncode != 0:
            return False
        libs = sorted((Path(tmp) / "x").glob("usr/lib/*/libgomp.so.1*"))
        for lib in libs:
            shutil.copy2(lib, carpeta / lib.name, follow_symlinks=True)
        if libs and not (carpeta / "libgomp.so.1").exists():
            shutil.copy2(libs[-1], carpeta / "libgomp.so.1")
        return bool(libs)


def _rosetta() -> None:
    """Rhubarb for Mac is an Intel program: Apple Silicon runs it through Rosetta 2."""
    if subprocess.run(["arch", "-x86_64", "/usr/bin/true"], capture_output=True).returncode == 0:
        return
    decir("Rhubarb necesita Rosetta (el traductor de Apple para programas de Intel); la instalo…", "·")
    r = ejecutar(["softwareupdate", "--install-rosetta", "--agree-to-license"], timeout=900)
    if r.returncode != 0 and subprocess.run(["arch", "-x86_64", "/usr/bin/true"], capture_output=True).returncode != 0:
        raise FabricaError("no he podido instalar Rosetta yo solo", "mac-rosetta",
                           "abre la app Terminal y escribe: softwareupdate --install-rosetta --agree-to-license")


def _blender_mac(spec: Spec, destino: Path) -> None:
    dmg = _bajar(spec.fuentes[0], spec.nombre)
    decir(f"{spec.nombre}: copiando la app (sin instalar nada en el sistema)…", "·")
    with tempfile.TemporaryDirectory(prefix="fabrica-dmg-") as punto:
        r = subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-noautoopen", "-mountpoint", punto, str(dmg)],
                           input="Y\n", capture_output=True, text=True)
        if r.returncode != 0:
            borrar(dmg)
            raise FabricaError(f"no he podido abrir el instalador de Blender: {primera_linea(r.stderr)}", "archivo-roto")
        try:
            app = next(Path(punto).glob("Blender*.app"))
            tmp = destino.with_name(destino.name + ".nuevo")
            if tmp.exists():
                borrar(tmp)
            tmp.mkdir(parents=True)
            r = ejecutar(["ditto", str(app), str(tmp / "Blender.app")])
            if r.returncode != 0:
                raise FabricaError("no he podido copiar Blender (¿falta espacio en el disco?)", "sin-espacio")
        finally:
            subprocess.run(["hdiutil", "detach", punto, "-quiet"], capture_output=True)
    if destino.exists():
        borrar(destino)
    mover(tmp, destino)
    if not guardar_descargas():
        borrar(dmg)


def _brew() -> str | None:
    return shutil.which("brew") or next((p for p in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew") if Path(p).exists()), None)


def _whisper_mac(proyecto: Path, spec: Spec) -> Path:
    """No official Mac command-line binary: Homebrew if the Mac has it; if not, build the pinned source here with
    Apple's command line tools (no password); if those are missing too, explain both options."""
    if os.environ.get("FABRICA_WHISPER_MAC") != "compilar" and (brew := _brew()):
        decir("whisper.cpp: lo instalo con Homebrew (ya lo tienes)…", "·")
        env = dict(entorno_limpio(), HOMEBREW_NO_INSTALL_CLEANUP="1", HOMEBREW_NO_ENV_HINTS="1")
        for formula in ("whisper-cpp", "whisper.cpp"):
            r = ejecutar([brew, "install", formula], env=env, timeout=1800, mostrar=True)
            if r.returncode == 0:
                break
        prefijo = subprocess.run([brew, "--prefix"], capture_output=True, text=True).stdout.strip() or "/opt/homebrew"
        for nombre in ("whisper-cli", "whisper-cpp"):
            if (p := Path(prefijo) / "bin" / nombre).exists():
                return p
        decir("whisper.cpp: Homebrew no lo ha dejado instalado; pruebo a construirlo aquí", "!")
    if subprocess.run(["xcode-select", "-p"], capture_output=True).returncode == 0:
        return _compilar_whisper(proyecto, spec)
    raise FabricaError("para el «oído» (whisper.cpp) tu Mac necesita las herramientas de Apple", "mac-sin-herramientas",
                       "escribe en Terminal: xcode-select --install  · acepta la ventana de Apple, espera a que termine "
                       "(10–20 min) y vuelve a pedir /fabrica:instalar. (Si ya usas Homebrew, también vale: brew install whisper-cpp)")


def _compilar_whisper(proyecto: Path, spec: Spec) -> Path:
    """Build whisper-cli from the pinned source. cmake comes from PyPI through uv (no administrator)."""
    uv = os.environ.get("FABRICA_UV") or shutil.which("uv")
    if not uv:
        raise FabricaError("falta uv para construir whisper.cpp", "uv-falta")
    if not (shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")):
        raise FabricaError("no hay compilador para construir whisper.cpp", "whisper-no-arranca")
    src_tar = _bajar(Fuente(WHISPER_SRC, WHISPER_SRC_SHA, nombre=f"whisper.cpp-{WHISPER}-src.tar.gz"), "código de whisper.cpp")
    trabajo = carpeta_cache().parent / "compilar" / f"whisper-{WHISPER}"
    descargas.extraer(src_tar, trabajo)
    src = descargas.una_sola_carpeta(trabajo)
    build = trabajo / "build"
    cmake = [uv, "tool", "run", "--from", "cmake", "cmake"]
    decir("whisper.cpp: construyéndolo en tu ordenador (2–5 minutos)…", "·")
    r = ejecutar([*cmake, "-S", str(src), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=OFF",
                  "-DWHISPER_BUILD_TESTS=OFF", "-DWHISPER_SDL2=OFF", "-DGGML_NATIVE=OFF"],
                 env=entorno_limpio(), timeout=900, mostrar=True)
    if r.returncode == 0:
        r = ejecutar([*cmake, "--build", str(build), "--config", "Release", "-j", "--target", "whisper-cli"],
                     env=entorno_limpio(), timeout=1800, mostrar=True)
    hecho = next(iter([*build.glob("bin/whisper-cli"), *build.glob("bin/Release/whisper-cli*")]), None)
    if r.returncode != 0 or not hecho:
        raise FabricaError("no he podido construir whisper.cpp", "whisper-no-arranca")
    destino = proyecto / "tools" / spec.carpeta
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hecho, destino / hecho.name)
    (destino / hecho.name).chmod(0o755)
    if not guardar_descargas():
        borrar(trabajo)
    return destino / hecho.name


def _modelo(proyecto: Path, forzar: bool) -> None:
    destino = proyecto / "models" / "ggml-small.bin"
    if destino.exists() and destino.stat().st_size == MODEL_SIZE and not forzar:
        decir("modelo de whisper: ya está", "✔")
        return
    decir("modelo de whisper (el «oído»; ~490 MB)", "→")
    cache = carpeta_cache() / "ggml-small.bin"
    primero: FabricaError | None = None
    for i, url in enumerate(MODEL_URLS):
        try:
            descargas.descargar(url, cache, sha256=MODEL_SHA, tamano=MODEL_SIZE, nombre="modelo de whisper")
            break
        except FabricaError as e:
            primero = primero or e
            if i + 1 == len(MODEL_URLS) or e.codigo not in ("sin-conexion", "descarga-404", "descarga-hash"):
                # a missing course mirror must not hide the real problem (usually the connection)
                raise (primero if e.codigo == "descarga-404" else e) from None
            decir(f"modelo de whisper: esa web no responde bien ({e.codigo}); pruebo la copia del curso", "!")
    destino.parent.mkdir(parents=True, exist_ok=True)
    if guardar_descargas():
        shutil.copy2(cache, destino)
    else:
        shutil.move(str(cache), str(destino))
    decir("modelo de whisper: listo (comprobado con su huella SHA-256)", "✔")


def _emojis() -> None:
    """Linux only: without a color emoji font, emojis on the phone screens render as boxes. Installed for this user
    only (~/.local/share/fonts): no administrator."""
    if sistema() != "linux":
        return
    fc_list = shutil.which("fc-list")
    if not fc_list:
        decir("fuente de emojis: no puedo comprobarla (falta fontconfig); sigo", "!")
        return
    if "emoji" in subprocess.run([fc_list], capture_output=True, text=True, errors="replace").stdout.lower():
        decir("fuente de emojis: ya está", "✔")
        return
    fuentes = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "fonts"
    descargas.descargar(EMOJI_URL, fuentes / "NotoColorEmoji.ttf", sha256=EMOJI_SHA, nombre="fuente de emojis")
    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(fuentes)], capture_output=True)
    decir("fuente de emojis: instalada solo para tu usuario", "✔")


def estado(proyecto: Path) -> dict[str, dict]:
    """What is installed (for `fabrica estado`)."""
    reg = _registro(proyecto)
    out = {}
    for clave, spec in specs().items():
        r = reg.get(clave)
        out[clave] = {"nombre": spec.nombre, "fijada": spec.version, "instalada": r.get("version") if r else None,
                      "bin": r.get("bin") if r else None}
    m = proyecto / "models" / "ggml-small.bin"
    out["modelo"] = {"nombre": NOMBRES["modelo"], "instalada": m.exists() and m.stat().st_size == MODEL_SIZE}
    return out


def url_redirigida(url: str) -> str:
    """Final URL after redirects (used to find the newest Mac ffmpeg build if the pinned one disappears)."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": descargas.USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.geturl()
