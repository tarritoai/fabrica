"""Downloads that survive bad connections (retries, resume where they stopped) and are checked (size, SHA-256),
plus safe unpacking of zip / tar archives. Standard library only."""

from __future__ import annotations

import hashlib
import os
import shutil
import ssl
import stat
import subprocess
import tarfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .comun import FabricaError, Log, borrar, decir, mover, ruta_larga, sistema

# Some servers (download.blender.org) answer 403 to Python's default User-Agent.
USER_AGENT = "fabrica-instalador/1.0 (+https://github.com/tarritoai/fabrica)"
INTENTOS = 5
TROZO = 1 << 20  # 1 MiB
# A connection that crawls (a stuck CDN node: seen with Hugging Face at < 1 KB/s) is dropped and resumed: a new
# connection usually lands on a healthy server. Less than LENTO_BYTES in LENTO_SEGUNDOS counts as stuck.
LENTO_SEGUNDOS = 45
LENTO_BYTES = 256 * 1024


class DescargaLenta(TimeoutError):
    pass


_CONTEXTO: ssl.SSLContext | None = None


def contexto_ssl() -> ssl.SSLContext:
    """The system's certificates. The Python that uv downloads (python-build-standalone) may not find the macOS or
    Linux certificate bundle on its own, so the usual bundle files are added explicitly when they exist."""
    global _CONTEXTO
    if _CONTEXTO is None:
        ctx = ssl.create_default_context()
        for bundle in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt"):
            if os.path.isfile(bundle):
                try:
                    ctx.load_verify_locations(bundle)
                except (ssl.SSLError, OSError):
                    pass
        _CONTEXTO = ctx
    return _CONTEXTO


def _abrir(url: str, desde: int = 0, timeout: float = 60):
    headers = {"User-Agent": USER_AGENT}
    if desde:
        headers["Range"] = f"bytes={desde}-"
    req = urllib.request.Request(url, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=contexto_ssl())
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
            raise FabricaError(
                "tu ordenador no se fía del certificado de seguridad de la web de descargas "
                "(suele ser la fecha y hora del ordenador mal puestas, o un antivirus que inspecciona las conexiones)",
                "certificado") from e
        raise


def texto(url: str, timeout: float = 30) -> str:
    """A small text file (checksums, version lists), with retries."""
    ultimo: Exception | None = None
    for intento in range(INTENTOS):
        try:
            with _abrir(url, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except FabricaError as e:
            curl = shutil.which("curl")
            if e.codigo != "certificado" or not curl:
                raise
            r = subprocess.run([curl, "-fsSL", "-A", USER_AGENT, url], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if r.returncode == 0:
                return r.stdout
            raise
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            ultimo = e
            time.sleep(2 * (intento + 1))
    raise FabricaError(f"no he podido leer {url}: {ultimo}", "sin-conexion")


def sha256_de(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for bloque in iter(lambda: fh.read(TROZO), b""):
            h.update(bloque)
    return h.hexdigest()


def _mb(n: float) -> str:
    return f"{n / 1e6:,.0f} MB".replace(",", ".")


def _tiempo(seg: float) -> str:
    if seg < 90:
        return f"{seg:.0f} s"
    return f"{seg / 60:.0f} min"


def descargar(url: str, destino: Path, sha256: str | None = None, tamano: int | None = None,
              nombre: str | None = None) -> Path:
    """Download `url` to `destino`. Resumes a half-finished `.part` file, retries with pauses, prints a readable
    progress line every few seconds and checks the SHA-256 when we know it. Idempotent: an existing file with the
    right hash is not downloaded again."""
    nombre = nombre or destino.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        if (not sha256 or sha256_de(destino) == sha256.lower()) and (not tamano or destino.stat().st_size == tamano):
            decir(f"{nombre}: ya estaba descargado", "✔")
            return destino
        borrar(destino)
    parte = destino.with_name(destino.name + ".part")
    intento = 0
    hash_fallido = False
    while True:
        intento += 1
        hecho = parte.stat().st_size if parte.exists() else 0
        try:
            _bajar(url, parte, hecho, tamano, nombre)
        except FabricaError as e:
            # Python cannot check the certificate but the system's curl may (it uses the OS certificate store,
            # which is where an antivirus that inspects HTTPS installs its own certificate).
            if e.codigo != "certificado" or not _bajar_con_curl(url, parte, nombre):
                raise
        except (urllib.error.URLError, OSError, TimeoutError, ConnectionError) as e:
            Log.escribir(f"fallo de descarga ({intento}/{INTENTOS}): {e!r}")
            if isinstance(e, urllib.error.HTTPError) and e.code in (404, 410):
                raise FabricaError(f"{nombre}: la dirección de descarga ya no existe ({url})", "descarga-404") from e
            if intento >= INTENTOS:
                raise FabricaError(f"{nombre}: la descarga ha fallado {INTENTOS} veces ({e}). Revisa tu conexión y "
                                   "vuelve a lanzar el mismo paso: seguirá donde se quedó", "sin-conexion") from e
            espera = min(30, 3 * intento)
            motivo = "la conexión iba lentísima" if isinstance(e, DescargaLenta) else "se cortó la conexión"
            decir(f"{nombre}: {motivo}; reintento en {espera} s ({intento}/{INTENTOS})", "!")
            time.sleep(espera)
            continue
        if tamano and parte.stat().st_size != tamano:
            Log.escribir(f"tamaño {parte.stat().st_size} != {tamano}")
            if parte.stat().st_size > tamano or intento >= INTENTOS:
                borrar(parte)
                raise FabricaError(f"{nombre}: el archivo descargado no tiene el tamaño esperado", "descarga-hash")
            continue
        if sha256:
            real = sha256_de(parte)
            if real != sha256.lower():
                Log.escribir(f"sha256 {real} != {sha256}")
                borrar(parte)
                if hash_fallido:
                    raise FabricaError(f"{nombre}: el archivo descargado no coincide con su huella de seguridad "
                                       "(SHA-256) ni a la segunda: no lo instalo", "descarga-hash")
                hash_fallido = True
                decir(f"{nombre}: la huella de seguridad no coincide; lo descargo otra vez desde cero", "!")
                continue
        parte.replace(destino)
        return destino


def _bajar(url: str, parte: Path, hecho: int, tamano: int | None, nombre: str) -> None:
    if tamano and hecho == tamano:
        return
    with _abrir(url, desde=hecho) as r:
        if hecho and getattr(r, "status", 200) != 206:
            hecho = 0  # the server ignored Range: start over
        largo = r.headers.get("Content-Length")
        total = tamano or ((int(largo) + hecho) if largo else None)
        if hecho:
            decir(f"{nombre}: sigo donde se quedó ({_mb(hecho)} ya bajados)", "·")
        inicio = ultimo = ventana = time.time()
        bajado_ahora = en_ventana = 0
        leer = getattr(r, "read1", r.read)  # read1: returns what has arrived, so a slow link is noticed
        with parte.open("ab" if hecho else "wb") as fh:
            while True:
                bloque = leer(TROZO)
                if not bloque:
                    break
                fh.write(bloque)
                bajado_ahora += len(bloque)
                en_ventana += len(bloque)
                ahora = time.time()
                if ahora - ventana >= LENTO_SEGUNDOS:
                    if en_ventana < LENTO_BYTES:
                        raise DescargaLenta(f"la conexión va a {en_ventana / (ahora - ventana) / 1000:.1f} KB/s")
                    ventana, en_ventana = ahora, 0
                if ahora - ultimo >= 5:
                    ultimo = ahora
                    vel = bajado_ahora / max(0.1, ahora - inicio)
                    llevado = hecho + bajado_ahora
                    if total:
                        quedan = (total - llevado) / vel if vel else 0
                        decir(f"  {nombre}: {_mb(llevado)} de {_mb(total)} ({100 * llevado / total:.0f} %) · "
                              f"{vel / 1e6:.1f} MB/s · quedan ~{_tiempo(quedan)}")
                    else:
                        decir(f"  {nombre}: {_mb(llevado)} · {vel / 1e6:.1f} MB/s")
        segundos = time.time() - inicio
        decir(f"{nombre}: descargado ({_mb(hecho + bajado_ahora)} en {_tiempo(segundos)})", "✔")


def _bajar_con_curl(url: str, parte: Path, nombre: str) -> bool:
    curl = shutil.which("curl")
    if not curl:
        return False
    decir(f"{nombre}: Python no puede comprobar el certificado; descargo con curl, que usa los del sistema", "!")
    r = subprocess.run([curl, "-fL", "--retry", "3", "-C", "-", "-A", USER_AGENT, "-o", str(parte), url],
                       capture_output=True, text=True, errors="replace")
    Log.escribir(f"curl {url}: código {r.returncode} {r.stderr[-500:]}")
    return r.returncode == 0


# --- unpacking -----------------------------------------------------------------------------------------------------


def _dentro(base: Path, nombre: str) -> Path:
    """The destination of an archive member; refuses absolute paths and ../ tricks."""
    nombre = nombre.replace("\\", "/")
    if nombre.startswith("/") or (len(nombre) > 1 and nombre[1] == ":"):
        raise FabricaError(f"el archivo comprimido trae una ruta peligrosa: {nombre}", "archivo-roto")
    destino = (base / nombre).resolve()
    if destino != base.resolve() and base.resolve() not in destino.parents:
        raise FabricaError(f"el archivo comprimido intenta escribir fuera de su carpeta: {nombre}", "archivo-roto")
    return destino


def extraer(archivo: Path, destino: Path) -> None:
    """Unpack a .zip / .tar.xz / .tar.gz into `destino` (created). Unpacks into a temporary sibling folder first and
    renames at the end, so an interrupted unpack never looks finished."""
    tmp = destino.with_name(destino.name + ".extrayendo")
    if tmp.exists():
        borrar(tmp)
    tmp.mkdir(parents=True)
    nombre = archivo.name.lower()
    try:
        if nombre.endswith(".zip") or nombre.endswith(".whl"):
            _extraer_zip(archivo, tmp)
        elif nombre.endswith((".tar.xz", ".tar.gz", ".tgz", ".tar")):
            with tarfile.open(archivo) as tf:
                try:
                    tf.extractall(tmp, filter="data")  # Python >= 3.12: refuses links and paths that escape
                except TypeError:
                    tf.extractall(tmp)  # noqa: S202  very old Python; members were not checked
        else:
            raise FabricaError(f"no sé descomprimir {archivo.name}", "archivo-roto")
    except (zipfile.BadZipFile, tarfile.TarError, EOFError) as e:
        borrar(tmp)
        borrar(archivo)  # a broken archive must be downloaded again next time
        raise FabricaError(f"{archivo.name} está dañado (descarga incompleta); vuelve a lanzar el paso", "archivo-roto") from e
    if destino.exists():
        borrar(destino)
    mover(tmp, destino)


def _extraer_zip(archivo: Path, base: Path) -> None:
    with zipfile.ZipFile(archivo) as zf:
        for info in zf.infolist():
            dest = _dentro(base, info.filename)
            if info.is_dir():
                os.makedirs(ruta_larga(dest), exist_ok=True)
                continue
            os.makedirs(ruta_larga(dest.parent), exist_ok=True)
            modo = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(modo):
                continue  # zips from these projects carry no needed symlinks; skipping is the safe choice
            with zf.open(info) as src, open(ruta_larga(dest), "wb") as dst:
                shutil.copyfileobj(src, dst, TROZO)
            if sistema() != "windows" and modo & 0o111:
                os.chmod(dest, 0o755)


def una_sola_carpeta(path: Path) -> Path:
    """If a folder only contains one folder (archives that wrap everything), that inner folder."""
    hijos = [p for p in path.iterdir() if not p.name.startswith(".")]
    return hijos[0] if len(hijos) == 1 and hijos[0].is_dir() else path
