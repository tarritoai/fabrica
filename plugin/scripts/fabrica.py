"""fabrica: install, check and update a student's factory. Launched by fabrica.sh / fabrica.ps1 (which bring uv and
Python 3.12); every step is idempotent and can be repeated after a failure.

Steps of /fabrica:instalar, in order:  sistema → preparar → herramientas → dependencias → doctor → humo → ajustes
CI and power users:                     todo  (all the steps, non-interactive)

Two kinds of factory share these steps: the 3D one (plantilla/, the course's) and the 2D «¿Y si…?» one
(plantilla-2d/, «la nave de enfrente», /fabrica:nave), chosen with --tipo 2d at `sistema`/`preparar`/`todo`. After
`preparar` the project remembers its kind, so the later steps need no flag. The 2D factory needs no Blender, no
Rhubarb and no graphics card, and reuses the tools another factory of this computer already downloaded.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fabrica_lib import ajustes, comprobar, diagnostico, herramientas, plantilla  # noqa: E402
from fabrica_lib.comun import (FabricaError, Log, ResumenUv, candado, carpeta_cache, decir, despierto, ejecutar,  # noqa: E402
                               entorno_limpio, espacio_libre_gb, glibc, leer_json, linux_distro, memoria_gb, plataforma,
                               resumen_remotion, setup_console, sistema, titulo, version_plugin, version_tupla)

MIN_GB, AVISO_GB = 8, 15
SINCRONIZADAS = ("OneDrive", "iCloud", "Mobile Documents", "Dropbox", "Google Drive", "GoogleDrive", "Box Sync")


# --- the computer and the folder -------------------------------------------------------------------------------------


def carpeta_recomendada(tipo: str = "3d") -> Path:
    nombre = "nave-2d" if tipo == "2d" else "fabrica"
    if sistema() == "windows":
        return Path((os.environ.get("SystemDrive") or "C:") + "\\") / nombre
    return Path.home() / nombre


def revisar_carpeta(carpeta: Path) -> tuple[list[str], list[str], str]:
    """(errors, warnings, kind) for a candidate project folder. kind: 'nueva' | 'vacia' | 'fabrica' | 'ocupada'."""
    errores: list[str] = []
    avisos: list[str] = []
    texto = str(carpeta)
    sync = [s for s in SINCRONIZADAS if s.lower() in texto.lower()]
    if not sync and sistema() == "windows" and (od := os.environ.get("OneDrive")):
        if texto.lower().startswith(od.lower()):
            sync = ["OneDrive"]
    if sync:
        errores.append(f"está dentro de {sync[0]}: se sincroniza con la nube y el render se atasca con eso "
                       f"[código: carpeta-onedrive]")
    if sistema() == "windows":
        if " " in texto or not texto.isascii():
            avisos.append("tiene espacios o tildes: la fábrica lo soporta, pero una ruta corta y sin tildes "
                          f"({carpeta_recomendada()}) evita problemas con programas externos")
        if len(texto) > 60:
            avisos.append(f"es una ruta larga ({len(texto)} letras): Windows limita las rutas a 260; mejor algo corto")
    libre = espacio_libre_gb(carpeta)
    if libre is not None and libre < MIN_GB:
        errores.append(f"solo quedan {libre:.1f} GB libres en ese disco; hacen falta al menos {MIN_GB} GB [código: sin-espacio]")
    elif libre is not None and libre < AVISO_GB:
        avisos.append(f"quedan {libre:.0f} GB libres: basta para instalar, pero cada vídeo ocupa; mejor {AVISO_GB} GB o más")
    if not carpeta.exists():
        tipo = "nueva"
    elif (carpeta / "reels" / "cli.py").exists() or (carpeta / ".fabrica" / "plantilla.json").exists():
        tipo = "fabrica"
    elif any(p for p in carpeta.iterdir() if not p.name.startswith(".") and p.name not in ("logs", "desktop.ini")):
        tipo = "ocupada"
        errores.append("ya tiene otros archivos: la fábrica necesita una carpeta para ella sola [código: carpeta-no-vacia]")
    else:
        tipo = "vacia"
    if carpeta.exists() and not os.access(carpeta, os.W_OK):
        errores.append("no puedo escribir en ella (es de otro usuario o del sistema)")
    elif not carpeta.exists():
        padre = next((p for p in carpeta.parents if p.exists()), None)
        if padre and not os.access(padre, os.W_OK):
            errores.append(f"no puedo crearla: no tengo permiso para escribir en {padre}")
    return errores, avisos, tipo


def info_sistema(tipo: str = "3d") -> dict:
    so = sistema()
    datos: dict = {"sistema": so, "plataforma": plataforma(), "python": sys.version.split()[0], "tipo": tipo,
                   "memoria_gb": round(memoria_gb() or 0, 1), "carpeta_recomendada": str(carpeta_recomendada(tipo)),
                   "cache_descargas": str(carpeta_cache()), "plugin": version_plugin(),
                   "git": bool(shutil.which("git")), "avisos": [], "bloqueos": []}
    import platform

    if so == "windows":
        build = int((platform.version().split(".") + ["0", "0", "0"])[2] or 0)
        datos["version"] = f"Windows {'11' if build >= 22000 else '10'} (build {build})"
        if build and build < 17763:
            datos["bloqueos"].append("Windows 10 anterior a la versión 1809: actualiza Windows")
        if plataforma() == "windows-arm64":
            datos["avisos"].append("Windows en ARM: no está probado (debería funcionar con las versiones ARM)")
    elif so == "mac":
        ver = platform.mac_ver()[0]
        datos["version"] = f"macOS {ver}"
        if plataforma() != "mac-arm64":
            datos["bloqueos"].append("Mac con Intel: Blender 5 solo existe para Mac con chip Apple [código: mac-intel]"
                                     if tipo == "3d" else "Mac con Intel: el instalador aún no tiene versiones probadas "
                                     "de Node y ffmpeg para él [código: mac-intel]")
        if ver and version_tupla(ver) < (13,) and tipo == "3d":
            datos["bloqueos"].append("macOS anterior a 13 (Ventura): Blender 5 no funciona; actualiza macOS")
        datos["homebrew"] = bool(herramientas._brew())
        datos["herramientas_apple"] = subprocess.run(["xcode-select", "-p"], capture_output=True).returncode == 0
    else:
        d = linux_distro()
        datos["version"] = d.get("PRETTY_NAME", "Linux")
        g = glibc()
        datos["glibc"] = ".".join(map(str, g))
        if g < (2, 35):
            datos["avisos"].append("Linux antiguo (glibc < 2.35): la guía cubre Ubuntu 22.04+, Debian 12+ y Mint 21+")
        if plataforma() != "linux-x64" and tipo == "3d":
            datos["bloqueos"].append("Linux en ARM: Blender no publica versión oficial [código: plataforma-no-soportada]")
        elif plataforma() != "linux-x64":
            datos["avisos"].append("Linux en ARM: la fábrica 2D debería funcionar, pero no está probada")
    if tipo == "2d":
        datos["avisos"] = [a for a in datos["avisos"] if "renders irán justos" not in a]
    if (m := datos["memoria_gb"]) and m < (3.5 if tipo == "2d" else 7.5):
        datos["avisos"].append(f"tiene {m:.0f} GB de memoria: funciona, pero los renders irán justos (recomendado 16 GB)")
    return datos


def cmd_sistema(a: argparse.Namespace) -> int:
    datos = info_sistema(a.tipo)
    carpeta = _ruta(a.carpeta) if a.carpeta else carpeta_recomendada(a.tipo)
    errores, avisos, tipo = revisar_carpeta(carpeta)
    datos["carpeta"] = {"ruta": str(carpeta), "tipo": tipo, "errores": errores, "avisos": avisos,
                        "libre_gb": round(espacio_libre_gb(carpeta) or 0, 1)}
    if a.json:
        print(json.dumps(datos, ensure_ascii=False, indent=1))
        return 0 if not (errores or datos["bloqueos"]) else 1
    decir(f"{datos['version']} · {datos['plataforma']} · {datos['memoria_gb']} GB de memoria"
          + (" · fábrica 2D (sin Blender ni gráfica)" if a.tipo == "2d" else ""), "·")
    for b in datos["bloqueos"]:
        decir(b, "✘")
    for av in datos["avisos"]:
        decir(av, "!")
    decir(f"Carpeta propuesta: {carpeta}  ({ {'nueva': 'no existe: la crearé', 'vacia': 'existe y está vacía', 'fabrica': 'ya tiene una fábrica', 'ocupada': 'tiene otras cosas'}[tipo] }; "
          f"{datos['carpeta']['libre_gb']} GB libres)", "·")
    for e in errores:
        decir(e, "✘")
    for av in avisos:
        decir(av, "!")
    if datos["bloqueos"] and a.tipo == "3d" and plataforma() in ("linux-arm64",):
        decir("La fábrica 2D (/fabrica:nave) no necesita Blender: esa sí puede funcionar aquí.", "→")
    if not (errores or datos["bloqueos"]):
        decir("Este ordenador y esta carpeta sirven.", "✔")
    return 0 if not (errores or datos["bloqueos"]) else 1


# --- steps ---------------------------------------------------------------------------------------------------------


def _ruta(texto: str) -> Path:
    """A folder typed or passed by Claude. Windows PowerShell 5.1 turns a trailing backslash before the closing quote
    ("C:\\fabrica\\") into a stray quote: clean it up."""
    return Path(texto.strip().strip('"').strip("'").rstrip("\\/") or ".").expanduser().resolve()


def _proyecto(a: argparse.Namespace) -> Path:
    p = _ruta(a.proyecto)
    Log.abrir(p / "logs" / "instalacion.log" if (p / "reels").exists() or a.comando == "preparar"
              else carpeta_cache().parent / "instalacion.log")
    return p


def _exigir_fabrica(p: Path) -> None:
    if not (p / "reels" / "cli.py").exists():
        raise FabricaError(f"{p} no es una fábrica (falta reels/); primero el paso «preparar»", "no-es-proyecto")


def _uv() -> str:
    uv = os.environ.get("FABRICA_UV") or shutil.which("uv")
    if not uv:
        raise FabricaError("no encuentro uv", "uv-falta")
    return uv


def cmd_preparar(a: argparse.Namespace) -> int:
    p = _proyecto(a)
    titulo("Preparar tu carpeta")
    errores, avisos, tipo = revisar_carpeta(p)
    errores = [e for e in errores if not (tipo == "fabrica" and "otros archivos" in e)]
    for av in avisos:
        decir(av, "!")
    if errores:
        raise FabricaError(f"no uso {p}: " + "; ".join(errores),
                           re.search(r"\[código: ([\w-]+)\]", errores[0]).group(1) if "[código:" in errores[0] else "carpeta")
    tipo = plantilla.tipo_de(p) if tipo_carpeta(p) == "fabrica" else a.tipo
    if tipo_carpeta(p) == "fabrica" and tipo != a.tipo and a.tipo_dado:
        raise FabricaError(f"{p} ya es una {plantilla.NOMBRE_TIPO[tipo]}; la {plantilla.NOMBRE_TIPO[a.tipo]} va en "
                           f"otra carpeta (p. ej. {carpeta_recomendada(a.tipo)})", "carpeta-no-vacia")
    origen, version = plantilla.localizar(tipo=tipo)
    n = plantilla.copiar(origen, version, p, tipo)
    decir(f"{n} archivos copiados a {p}" if n else f"la plantilla ya estaba en {p} (no he tocado nada tuyo)", "✔")
    plantilla.registrar(p, tipo)
    env = p / ".env"
    if not env.exists() and (p / ".env.example").exists():
        shutil.copy2(p / ".env.example", env)
        decir(".env creado (tus claves irán ahí; de momento no hace falta ninguna)", "✔")
    if shutil.which("git") and not (p / ".git").exists():
        r = ejecutar(["git", "init", "-q"], cwd=p)
        if r.returncode == 0:
            decir("historial de cambios (git) preparado", "✔")
    decir(f"Siguiente: herramientas (registro en {Log.path})", "→")
    return 0


def tipo_carpeta(p: Path) -> str:
    return revisar_carpeta(p)[2] if p.exists() else "nueva"


def cmd_herramientas(a: argparse.Namespace) -> int:
    p = _proyecto(a)
    _exigir_fabrica(p)
    titulo("Herramientas (en tu carpeta, sin permisos de administrador)")
    tipo = plantilla.tipo_de(p)
    plantilla.registrar(p, tipo)
    claves = [c.strip() for c in a.solo.split(",")] if a.solo else herramientas.orden(tipo)
    desconocidas = [c for c in claves if c not in herramientas.ORDEN]
    if desconocidas:
        raise FabricaError(f"no conozco: {', '.join(desconocidas)} (valen: {', '.join(herramientas.ORDEN)})", "uso")
    with despierto("descargando las herramientas de la fábrica"):
        for clave in claves:
            herramientas.instalar(clave, p, forzar=a.forzar)
    herramientas.escribir_env(p)
    decir("Herramientas listas y apuntadas en .env.", "✔")
    return 0


def _node_y_npm(p: Path) -> tuple[Path, Path]:
    reg = leer_json(p / "tools" / ".fabrica.json", {}) or {}
    if "node" not in reg:
        raise FabricaError("falta Node.js: lanza antes el paso de herramientas", "node-no-arranca")
    node = p / reg["node"]["bin"]
    base = node.parent if sistema() == "windows" else node.parent.parent
    npm = base / ("node_modules" if sistema() == "windows" else "lib/node_modules") / "npm" / "bin" / "npm-cli.js"
    return node, npm


def cmd_dependencias(a: argparse.Namespace) -> int:
    p = _proyecto(a)
    _exigir_fabrica(p)
    titulo("Piezas de Python y de Remotion")
    env = entorno_limpio()
    env.setdefault("UV_SYSTEM_CERTS", "1")
    with despierto("instalando las piezas de la fábrica"):
        decir("Python 3.12 y sus librerías (uv sync)…", "→")
        r = ejecutar([_uv(), "sync"], cwd=p, env=env, timeout=1800, mostrar=True, traducir=ResumenUv())
        if r.returncode != 0:
            raise FabricaError("no se han podido instalar las piezas de Python (uv sync)", "uv-sin-python")
        decir("Python listo", "✔")
        node, npm = _node_y_npm(p)
        env_node = dict(entorno_limpio([node.parent]), NPM_CONFIG_UPDATE_NOTIFIER="false", NPM_CONFIG_FUND="false")
        remotion = p / "remotion"
        if (remotion / "node_modules" / "@remotion" / "cli" / "remotion-cli.js").exists() and not a.forzar:
            decir("piezas de Remotion: ya estaban", "✔")
        else:
            decir("piezas de Remotion (npm ci; 1–3 minutos)…", "→")
            r = ejecutar([str(node), str(npm), "ci", "--no-audit", "--no-fund", "--loglevel", "error"], cwd=remotion,
                         env=env_node, timeout=1800, mostrar=True)
            if r.returncode != 0:
                raise FabricaError("no se han podido instalar las piezas de Remotion (npm ci)", "npm-red")
            decir("Remotion listo", "✔")
        decir("navegador invisible para montar los vídeos…", "→")
        cli = remotion / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
        r = ejecutar([str(node), str(cli), "browser", "ensure"], cwd=remotion, env=env_node, timeout=900, mostrar=True,
                     traducir=resumen_remotion)
        if r.returncode != 0:
            decir("no he podido preparar el navegador ahora; Remotion lo intentará solo en el primer montaje", "!")
        else:
            decir("navegador listo", "✔")
        if sistema() == "linux":
            _revisar_libs_chrome(remotion)
    return 0


def _revisar_libs_chrome(remotion: Path) -> None:
    """Linux: does the headless browser find its system libraries? (Desktops have them; minimal installs may not.)"""
    shell = next(iter(sorted(remotion.glob("node_modules/.remotion/**/chrome-headless-shell"))), None)
    if not shell or not shutil.which("ldd"):
        return
    salida = subprocess.run(["ldd", str(shell)], capture_output=True, text=True, errors="replace").stdout
    faltan = sorted({ln.split()[0] for ln in salida.splitlines() if "not found" in ln})
    if faltan:
        decir(f"al navegador del montaje le faltan librerías del sistema: {', '.join(faltan)}", "!")
        decir("Esto necesita a alguien con la contraseña de administrador, una vez [código: linux-libs-chrome]", "!")
    else:
        decir("librerías del navegador: completas", "✔")


def cmd_doctor(a: argparse.Namespace) -> int:
    p = _proyecto(a)
    _exigir_fabrica(p)
    titulo("Revisión (reels doctor)")
    r = ejecutar([_uv(), "run", "reels", "doctor", "--skip-api"], cwd=p, env=entorno_limpio(), timeout=900,
                 mostrar=True, prefijo="  ")
    if r.returncode != 0:
        raise FabricaError("el doctor ve piezas sin instalar (mira las líneas con ✘ de arriba)", "doctor")
    return 0


HUMO_RENDER = re.compile(r"\d/\d render")
HUMO_MONTAJE = re.compile(r"\d/\d montaje")


def cmd_humo(a: argparse.Namespace) -> int:
    p = _proyecto(a)
    _exigir_fabrica(p)
    if plantilla.tipo_de(p) == "2d":
        return _humo_2d(a, p)
    titulo("Tu primer vídeo (prueba de humo, gratis)")
    decir("Tarda unos minutos: el ordenador no se dormirá mientras tanto.", "·")
    modelo = p / "models" / "ggml-small.bin"
    if a.comprobar and not (modelo.exists() and modelo.stat().st_size == herramientas.MODEL_SIZE):
        decir("El modelo del «oído» aún no está (paso herramientas --solo modelo): hago el vídeo sin la comprobación "
              "final; cuando lo tengas, repite este paso para comprobarlo.", "!")
        a.comprobar = False

    def lanzar(motor: str | None) -> subprocess.CompletedProcess:
        cmd = [_uv(), "run", "reels", "humo", "--no-abrir"]
        if motor:
            cmd += ["--motor", motor]
        if not a.comprobar:
            cmd.append("--sin-comprobar")
        with despierto("renderizando la prueba de humo"):
            return ejecutar(cmd, cwd=p, env=entorno_limpio(), timeout=7200, mostrar=True, prefijo="  ")

    r = lanzar(a.motor)
    if r.returncode != 0 and a.motor != "cycles" and HUMO_RENDER.search(r.stdout) and not HUMO_MONTAJE.search(r.stdout):
        decir("El motor rápido (EEVEE) no funciona con la gráfica de este ordenador; repito con Cycles (sin gráfica, "
              "más lento) [código: eevee-sin-gpu]", "!")
        r = lanzar("cycles")
        if r.returncode == 0:
            herramientas.poner_extra(p, "REELS_RENDER_ENGINE", "cycles")
            decir("He apuntado REELS_RENDER_ENGINE=cycles en tu .env: tus renders usarán Cycles", "!")
    if r.returncode != 0:
        raise FabricaError("la prueba de humo no ha terminado (el motivo está en las últimas líneas de arriba)", "humo")
    final = p / "episodes" / "humo" / "final.mp4"
    decir(f"¡La fábrica funciona! Tu primer vídeo: {final}", "✔")
    if a.abrir:
        abrir(final)
    return 0


def _humo_2d(a: argparse.Namespace, p: Path) -> int:
    titulo("Tu primer reel 2D (prueba de humo, gratis)")
    decir("Menos de un minuto: dibujo, voz ya grabada, música y la comprobación final.", "·")
    modelo = p / "models" / "ggml-small.bin"
    if a.comprobar and not (modelo.exists() and modelo.stat().st_size == herramientas.MODEL_SIZE):
        decir("El modelo del «oído» aún no está: hago el reel sin la comprobación final.", "!")
        a.comprobar = False
    cmd = [_uv(), "run", "reels", "humo", "--no-abrir"] + ([] if a.comprobar else ["--sin-comprobar"])
    with despierto("dibujando la prueba de humo"):
        r = ejecutar(cmd, cwd=p, env=entorno_limpio(), timeout=3600, mostrar=True, prefijo="  ")
    if r.returncode != 0:
        raise FabricaError("la prueba de humo no ha terminado (el motivo está en las últimas líneas de arriba)", "humo")
    final = p / "episodes" / "humo" / "final.mp4"
    decir(f"¡Tu nave 2D funciona! Tu primer reel: {final}", "✔")
    if a.abrir:
        abrir(final)
    return 0


def abrir(path: Path) -> bool:
    try:
        if sistema() == "windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sistema() == "mac":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, AttributeError):
        return False


def cmd_abrir(a: argparse.Namespace) -> int:
    p = _ruta(a.proyecto)
    objetivo = {"video": p / "episodes" / "humo" / "final.mp4", "carpeta": p, "env": p / ".env"}[a.que]
    if a.que == "env":
        if not objetivo.exists() and (p / ".env.example").exists():
            shutil.copy2(p / ".env.example", objetivo)
        editor = {"windows": ["notepad.exe"], "mac": ["open", "-e"]}.get(sistema())
        if editor:
            subprocess.Popen([*editor, str(objetivo)])
            decir(f"Abierto {objetivo} en el editor de texto: pega tu clave después del =, guarda y cierra.", "✔")
            return 0
    if not objetivo.exists():
        raise FabricaError(f"no existe {objetivo}", "no-es-proyecto")
    decir(f"Abriendo {objetivo}" if abrir(objetivo) else f"No puedo abrirlo yo: está en {objetivo}", "·")
    return 0


def cmd_todo(a: argparse.Namespace) -> int:
    pasos = [("preparar", cmd_preparar), ("herramientas", cmd_herramientas), ("dependencias", cmd_dependencias),
             ("doctor", cmd_doctor), ("humo", cmd_humo)]
    a.solo, a.forzar, a.abrir = None, False, a.abrir
    for nombre, fn in pasos:
        a.comando = nombre
        fn(a)
        if a.hasta == nombre:
            break
    return 0


def cmd_ajustes(a: argparse.Namespace) -> int:
    if a.auto_update:
        ajustes.activar_auto_update()
    if a.idioma:
        ajustes.poner_idioma(a.idioma)
    if a.estado or not (a.auto_update or a.idioma):
        print(json.dumps(ajustes.estado(), ensure_ascii=False, indent=1))
    return 0


def cmd_actualizar(a: argparse.Namespace) -> int:
    p = _proyecto(a)
    _exigir_fabrica(p)
    titulo("Actualizar tu fábrica (sin tocar tu memoria)")
    origen, version = plantilla.localizar(tipo=plantilla.tipo_de(p))
    actual = plantilla.manifiesto(p).get("version", "?")
    decir(f"Tu fábrica: {actual} · disponible: {version}", "·")
    plan = plantilla.planificar(origen, p)
    nombres = {"nuevos": "archivos nuevos que se añadirán", "actualizar": "archivos que se actualizarán (no los habías tocado)",
               "conflictos": "archivos que TÚ cambiaste y la plantilla también (se quedan los tuyos)",
               "memoria": "tu memoria (no se toca nunca)", "retirar": "archivos que la plantilla ya no usa (a la copia de seguridad)"}
    for clave, texto in nombres.items():
        lista = plan[clave]
        if lista:
            decir(f"{len(lista)} {texto}:", "·")
            for rel in lista[:25]:
                decir(f"    {rel}")
            if len(lista) > 25:
                decir(f"    … y {len(lista) - 25} más")
    if not any(plan[k] for k in ("nuevos", "actualizar", "retirar", "conflictos")):
        decir("Ya estás al día.", "✔")
        return 0
    if not a.aplicar:
        decir("Esto es solo el plan. Para aplicarlo: el mismo comando con --aplicar", "→")
        return 0
    propuestas = plantilla.aplicar(origen, version, p, plan)
    decir(f"Actualizada a {version}. Copia de lo sustituido en .fabrica/copias/", "✔")
    if plan["conflictos"] or plan["memoria"]:
        decir(f"Las versiones nuevas de tus archivos cambiados están en {propuestas} para comparar con calma", "·")
    cambiados = set(plan["nuevos"] + plan["actualizar"])
    if cambiados & {"pyproject.toml", "uv.lock"}:
        decir("Cambiaron las piezas de Python: uv sync…", "→")
        ejecutar([_uv(), "sync"], cwd=p, env=entorno_limpio(), timeout=1800, mostrar=True, traducir=ResumenUv())
    if cambiados & {"remotion/package.json", "remotion/package-lock.json"}:
        node, npm = _node_y_npm(p)
        decir("Cambiaron las piezas de Remotion: npm ci…", "→")
        ejecutar([str(node), str(npm), "ci", "--no-audit", "--no-fund", "--loglevel", "error"], cwd=p / "remotion",
                 env=entorno_limpio([node.parent]), timeout=1800, mostrar=True)
    decir("Si cambió alguna herramienta, el paso «herramientas» la pone al día (lo que ya está, no se repite).", "·")
    return 0


def cmd_clave(a: argparse.Namespace) -> int:
    """Use in this factory the same ElevenLabs key as another factory of this computer (only with the student's OK:
    the skill asks first). The key is copied between the student's own .env files and never printed."""
    p = _proyecto(a)
    _exigir_fabrica(p)
    variable = "ELEVENLABS_API_KEY"
    destino = p / ".env"
    if not destino.exists() and (p / ".env.example").exists():
        shutil.copy2(p / ".env.example", destino)

    def valor(env: Path) -> str:
        if not env.exists():
            return ""
        for ln in env.read_text(encoding="utf-8", errors="replace").splitlines():
            if ln.strip().startswith(f"{variable}="):
                return ln.split("=", 1)[1].strip().strip("'\"")
        return ""

    if valor(destino):
        decir("Esta fábrica ya tiene su clave de ElevenLabs: no toco nada.", "✔")
        return 0
    otras = [_ruta(a.desde)] if a.desde else [o for o, _t in plantilla.otras_fabricas(p, con_herramientas=False)] + [
        x for x in (carpeta_recomendada("3d"),) if x != p]
    origen = next((o for o in otras if valor(o / ".env")), None)
    if origen is None:
        decir("No encuentro ninguna clave de ElevenLabs en tus otras fábricas. Pégala tú en el .env de esta "
              f"(FABRICA abrir env --proyecto \"{p}\").", "!")
        return 1
    texto = destino.read_text(encoding="utf-8") if destino.exists() else ""
    clave = valor(origen / ".env")
    lineas = texto.splitlines()
    for i, ln in enumerate(lineas):
        if ln.strip().startswith(f"{variable}="):
            lineas[i] = f"{variable}={clave}"
            break
    else:
        lineas.insert(0, f"{variable}={clave}")
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    decir(f"Clave de ElevenLabs copiada de {origen} (no la enseño: sigue solo en tus archivos .env).", "✔")
    return 0


def cmd_comprobar(a: argparse.Namespace) -> int:
    """Delegates to the project's checker (.claude/skills/tarrito/comprobar.py) when the factory exists; before it
    exists, checks the pre-install lots (0·2, 1·1, 1·3) with the installer's own rules."""
    p = _proyecto(a)
    return comprobar.comprobar(p, a.lote, a.respuesta, revisar_carpeta=revisar_carpeta, info_sistema=info_sistema)


def cmd_diagnosticar(a: argparse.Namespace) -> int:
    if a.codigo:
        filas = [f for f in [diagnostico.por_codigo(a.codigo)] if f]
    else:
        texto = Path(a.archivo).read_text(encoding="utf-8", errors="replace")[-20000:] if a.archivo else (
            sys.stdin.read() if a.texto in (None, "-") else a.texto)
        filas = diagnostico.diagnosticar(texto, sistema())
    if not filas:
        decir("No está en la tabla de errores conocidos. Lee el error con calma: la línea importante suele ser la "
              "última que empieza por «Error» o «✘».", "·")
        return 1
    for f in filas:
        decir(f"[{f['id']}] {f['texto']}", "·")
        decir(f"  Significa: {f['significa']}")
        decir(f"  Qué hacer: {f['arreglo']}")
    return 0


def cmd_estado(a: argparse.Namespace) -> int:
    p = _ruta(a.proyecto)
    datos = {"proyecto": str(p), "plugin": version_plugin(), "plantilla": plantilla.manifiesto(p).get("version"),
             "tipo": plantilla.tipo_de(p) if (p / "reels").exists() else None,
             "herramientas": herramientas.estado(p, plantilla.tipo_de(p)) if (p / "reels").exists() else {},
             "ajustes": ajustes.estado(), "sellos": comprobar.sellos(p),
             "registro": str(p / "logs" / "instalacion.log")}
    print(json.dumps(datos, ensure_ascii=False, indent=1))
    return 0


def cmd_errores_md(a: argparse.Namespace) -> int:
    sys.stdout.write(diagnostico.markdown())
    return 0


# --- CLI -----------------------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    setup_console()
    ap = argparse.ArgumentParser(prog="fabrica", description="Instala, revisa y actualiza tu fábrica de reels.")
    sub = ap.add_subparsers(dest="comando", required=True)

    def con_proyecto(nombre: str, ayuda: str) -> argparse.ArgumentParser:
        sp = sub.add_parser(nombre, help=ayuda)
        sp.add_argument("--proyecto", default=".", help="carpeta de tu fábrica (por defecto, la actual)")
        return sp

    def con_tipo(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--tipo", choices=["3d", "2d"], default=None,
                        help="3d = la fábrica del curso (por defecto); 2d = la nave «¿Y si…?» (sin Blender ni gráfica)")

    sp = sub.add_parser("sistema", help="¿sirve este ordenador? ¿y esta carpeta?")
    con_tipo(sp)
    sp.add_argument("--carpeta", help="carpeta propuesta para la fábrica")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_sistema)

    sp = con_proyecto("preparar", "copia la plantilla a tu carpeta")
    con_tipo(sp)
    sp.set_defaults(fn=cmd_preparar)
    sp = con_proyecto("herramientas", "descarga Blender, ffmpeg, whisper, Rhubarb, Node y el modelo")
    sp.add_argument("--solo", help=f"solo estas, separadas por comas: {','.join(herramientas.ORDEN)}")
    sp.add_argument("--forzar", action="store_true", help="reinstalar aunque ya estén")
    sp.set_defaults(fn=cmd_herramientas)
    sp = con_proyecto("dependencias", "uv sync + npm ci + navegador de Remotion")
    sp.add_argument("--forzar", action="store_true")
    sp.set_defaults(fn=cmd_dependencias)
    con_proyecto("doctor", "revisión completa (reels doctor)").set_defaults(fn=cmd_doctor)
    for nombre, fn, ayuda in (("humo", cmd_humo, "tu primer vídeo, gratis"),
                              ("todo", cmd_todo, "todos los pasos seguidos (CI)")):
        sp = con_proyecto(nombre, ayuda)
        sp.add_argument("--motor", choices=["cycles", "eevee"], help="cycles = sin gráfica (CI, máquinas virtuales)")
        sp.add_argument("--sin-comprobar", dest="comprobar", action="store_false", help="no re-escuchar con whisper")
        sp.add_argument("--abrir", action="store_true", help="abrir el vídeo al terminar")
        if nombre == "todo":
            sp.add_argument("--hasta", choices=["preparar", "herramientas", "dependencias", "doctor", "humo"])
            con_tipo(sp)
        sp.set_defaults(fn=fn)
    sp = con_proyecto("abrir", "abre el vídeo de humo, la carpeta o .env (para pegar tus claves)")
    sp.add_argument("que", choices=["video", "carpeta", "env"])
    sp.set_defaults(fn=cmd_abrir)

    sp = sub.add_parser("ajustes", help="ajustes de Claude Code (con permiso del alumno)")
    sp.add_argument("--auto-update", action="store_true", help="activar las actualizaciones automáticas de la fábrica")
    sp.add_argument("--idioma", help="p. ej. spanish")
    sp.add_argument("--estado", action="store_true")
    sp.set_defaults(fn=cmd_ajustes)

    sp = con_proyecto("clave", "usa en esta fábrica la misma clave de ElevenLabs que en otra tuya (sin enseñarla)")
    sp.add_argument("--desde", help="la otra fábrica (por defecto, la que encuentre)")
    sp.set_defaults(fn=cmd_clave)
    sp = con_proyecto("actualizar", "trae la plantilla nueva sin tocar tu memoria")
    sp.add_argument("--aplicar", action="store_true", help="sin esto, solo enseña el plan")
    sp.set_defaults(fn=cmd_actualizar)
    sp = con_proyecto("comprobar", "comprueba el entregable de un lote (en la fábrica: delega en /tarrito comprobar)")
    sp.add_argument("lote", nargs="?", help="p. ej. 1·5 (vale 1.5); sin lote, todos los pendientes")
    sp.add_argument("--respuesta", help="para los lotes que son una pregunta")
    sp.set_defaults(fn=cmd_comprobar)
    sp = sub.add_parser("diagnosticar", help="busca un error en la tabla de errores conocidos")
    sp.add_argument("texto", nargs="?", help="el error (o - para leerlo de la entrada)")
    sp.add_argument("--archivo", help="un registro (log) en el que buscar")
    sp.add_argument("--codigo", help="el código que dio el instalador")
    sp.set_defaults(fn=cmd_diagnosticar)
    con_proyecto("estado", "qué hay instalado (JSON)").set_defaults(fn=cmd_estado)
    sub.add_parser("errores-md", help="tabla de errores en Markdown").set_defaults(fn=cmd_errores_md)

    a = ap.parse_args(argv)
    if hasattr(a, "tipo"):
        a.tipo_dado = a.tipo is not None
        a.tipo = a.tipo or "3d"
    try:
        if a.comando in ("herramientas", "dependencias", "humo", "todo", "actualizar"):
            with candado(_ruta(a.proyecto)):
                return a.fn(a)
        return a.fn(a)
    except FabricaError as e:
        decir()
        decir(str(e), "✘")
        fila = diagnostico.por_codigo(e.codigo)
        if e.pista:
            decir(f"  Qué hacer: {e.pista}")
        elif fila:
            decir(f"  Qué hacer: {fila['arreglo']}")
        decir(f"  (código del error: {e.codigo}" + (f" · registro: {Log.path}" if Log.path else "") + ")")
        decir("  Puedes repetir este mismo paso cuando quieras: lo que ya está hecho no se repite. Ayuda: /fabrica:tarrito")
        return 1
    except KeyboardInterrupt:
        decir("Parado. Puedes repetir este mismo paso: seguirá donde se quedó.", "!")
        return 130
    except Exception as e:  # noqa: BLE001  never a bare traceback for a beginner: plain words + the full trace in the log
        import traceback

        Log.escribir(traceback.format_exc())
        decir()
        decir(f"algo inesperado ha fallado: {type(e).__name__}: {e}", "✘")
        filas = diagnostico.diagnosticar(f"{type(e).__name__}: {e}", sistema())
        if filas:
            decir(f"  Qué hacer: {filas[0]['arreglo']}")
            decir(f"  (código del error: {filas[0]['id']}" + (f" · registro: {Log.path}" if Log.path else "") + ")")
        elif Log.path:
            decir(f"  (los detalles están en el registro: {Log.path})")
        decir("  Puedes repetir este mismo paso: lo hecho no se repite. Si vuelve a pasar: /fabrica:tarrito")
        return 1


if __name__ == "__main__":
    sys.exit(main())
