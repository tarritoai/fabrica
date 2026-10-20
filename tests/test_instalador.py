"""Tests of the plugin's installer library (plugin/scripts/fabrica_lib). No network: downloads use a local server.

    uvx pytest tests -q
"""

from __future__ import annotations

import hashlib
import http.server
import io
import json
import os
import sys
import tarfile
import threading
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "plugin" / "scripts"))

import fabrica  # noqa: E402
from fabrica_lib import ajustes, comprobar, descargas, diagnostico, herramientas, plantilla  # noqa: E402
from fabrica_lib.comun import FabricaError  # noqa: E402

# --- a tiny HTTP server with Range support (resume) ------------------------------------------------------------------


class _Handler(http.server.BaseHTTPRequestHandler):
    archivos: dict[str, bytes] = {}
    cortar_en: int | None = None  # simulate a dropped connection after N bytes (first request only)

    def log_message(self, *a):  # noqa: D401
        pass

    def do_GET(self):  # noqa: N802
        data = self.archivos.get(self.path)
        if data is None:
            self.send_response(404)
            self.end_headers()
            return
        inicio = 0
        if rango := self.headers.get("Range"):
            inicio = int(rango.split("=")[1].split("-")[0])
            self.send_response(206)
        else:
            self.send_response(200)
        cuerpo = data[inicio:]
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        if _Handler.cortar_en is not None:
            n, _Handler.cortar_en = _Handler.cortar_en, None
            self.wfile.write(cuerpo[:n])
            self.wfile.flush()
            self.connection.shutdown(2)
            return
        self.wfile.write(cuerpo)


@pytest.fixture()
def servidor():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    monkeypatch.setattr(descargas.time, "sleep", lambda s: None)


def test_descarga_reanuda_y_comprueba_hash(servidor, tmp_path):
    data = os.urandom(3 * descargas.TROZO + 123)
    _Handler.archivos["/a.bin"] = data
    _Handler.cortar_en = descargas.TROZO + 10  # the connection drops once
    sha = hashlib.sha256(data).hexdigest()
    destino = descargas.descargar(f"{servidor}/a.bin", tmp_path / "a.bin", sha256=sha)
    assert destino.read_bytes() == data
    assert not (tmp_path / "a.bin.part").exists()
    # idempotent: a second call does not download again
    _Handler.archivos.pop("/a.bin")
    assert descargas.descargar(f"{servidor}/a.bin", tmp_path / "a.bin", sha256=sha).read_bytes() == data


def test_descarga_con_hash_malo_no_se_instala(servidor, tmp_path):
    _Handler.archivos["/b.bin"] = b"hola"
    with pytest.raises(FabricaError) as e:
        descargas.descargar(f"{servidor}/b.bin", tmp_path / "b.bin", sha256="0" * 64)
    assert e.value.codigo == "descarga-hash"
    assert not (tmp_path / "b.bin").exists()


def test_descarga_lentisima_se_reintenta_y_acaba_explicando(servidor, tmp_path, monkeypatch):
    _Handler.archivos["/lento.bin"] = os.urandom(3 * descargas.TROZO)
    monkeypatch.setattr(descargas, "LENTO_SEGUNDOS", 0)
    monkeypatch.setattr(descargas, "LENTO_BYTES", 1 << 40)
    with pytest.raises(FabricaError) as e:
        descargas.descargar(f"{servidor}/lento.bin", tmp_path / "lento.bin")
    assert e.value.codigo == "sin-conexion"
    assert (tmp_path / "lento.bin.part").stat().st_size > 0  # what arrived is kept for the next attempt


def test_descarga_404(servidor, tmp_path):
    with pytest.raises(FabricaError) as e:
        descargas.descargar(f"{servidor}/no-existe", tmp_path / "x")
    assert e.value.codigo == "descarga-404"


def _zip(entradas: dict[str, bytes], modos: dict[str, int] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for nombre, contenido in entradas.items():
            info = zipfile.ZipInfo(nombre)
            info.external_attr = ((modos or {}).get(nombre, 0o644) | 0o100000) << 16
            zf.writestr(info, contenido)
    return buf.getvalue()


def test_extraer_zip_respeta_permisos_y_carpeta_unica(tmp_path):
    z = tmp_path / "t.zip"
    z.write_bytes(_zip({"pkg-1.0/bin/tool": b"#!/bin/sh\n", "pkg-1.0/LEEME": b"x"}, {"pkg-1.0/bin/tool": 0o755}))
    descargas.extraer(z, tmp_path / "out")
    interior = descargas.una_sola_carpeta(tmp_path / "out")
    assert interior.name == "pkg-1.0"
    if os.name != "nt":
        assert os.access(interior / "bin" / "tool", os.X_OK)


@pytest.mark.parametrize("malo", ["../fuera.txt", "/etc/passwd", "a/../../fuera.txt"])
def test_extraer_rechaza_rutas_que_escapan(tmp_path, malo):
    z = tmp_path / "m.zip"
    z.write_bytes(_zip({malo: b"x"}))
    with pytest.raises(FabricaError):
        descargas.extraer(z, tmp_path / "out")
    assert not (tmp_path / "fuera.txt").exists()


def test_extraer_tar_xz(tmp_path):
    t = tmp_path / "t.tar.xz"
    with tarfile.open(t, "w:xz") as tf:
        info = tarfile.TarInfo("node-v1/bin/node")
        info.mode = 0o755
        info.size = 2
        tf.addfile(info, io.BytesIO(b"ok"))
        link = tarfile.TarInfo("node-v1/bin/npm")
        link.type = tarfile.SYMTYPE
        link.linkname = "node"
        tf.addfile(link)
    descargas.extraer(t, tmp_path / "out")
    assert (tmp_path / "out" / "node-v1" / "bin" / "node").read_bytes() == b"ok"


def test_archivo_roto_se_borra_para_bajarlo_otra_vez(tmp_path):
    z = tmp_path / "roto.zip"
    z.write_bytes(b"PK\x03\x04 esto no es un zip")
    with pytest.raises(FabricaError) as e:
        descargas.extraer(z, tmp_path / "out")
    assert e.value.codigo == "archivo-roto"
    assert not z.exists()


# --- pinned tools --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("plat", ["linux-x64", "mac-arm64", "windows-x64", "windows-arm64"])
def test_cada_descarga_tiene_huella(plat):
    todas = herramientas.specs(plat)
    assert {"blender", "ffmpeg", "whisper", "rhubarb"} <= set(todas)
    for clave, spec in todas.items():
        for f in [*spec.fuentes, *spec.alternativas]:
            assert f.url.startswith("https://"), (clave, f.url)
            assert f.sha256 or f.sha256_de, f"{clave} sin huella en {plat}"
            if f.sha256:
                assert len(f.sha256) == 64
    if plat == "mac-arm64":
        assert todas["whisper"].fuentes == []  # Homebrew or built from source
        assert todas["blender"].binario.startswith("Blender.app/")


def test_versiones_fijadas():
    assert herramientas.BLENDER == "5.2.2" and herramientas.RHUBARB == "1.14.0"
    assert herramientas.MODEL_SIZE == 487601967


def test_bloque_env_conserva_las_claves_del_alumno(tmp_path):
    (tmp_path / ".env.example").write_text("ELEVENLABS_API_KEY=\n", encoding="utf-8")
    (tmp_path / "tools").mkdir()
    herramientas._guardar_registro(tmp_path, {"blender": {"version": "5.2.2", "bin": "tools/blender-5.2.2/blender",
                                                           "env": {"BLENDER_BIN": "tools/blender-5.2.2/blender"}}})
    herramientas.escribir_env(tmp_path)
    env = tmp_path / ".env"
    env.write_text(env.read_text(encoding="utf-8").replace("ELEVENLABS_API_KEY=", "ELEVENLABS_API_KEY=sk_secreta"),
                   encoding="utf-8")
    herramientas.poner_extra(tmp_path, "REELS_RENDER_ENGINE", "cycles")
    herramientas.escribir_env(tmp_path)
    texto = env.read_text(encoding="utf-8")
    assert "ELEVENLABS_API_KEY=sk_secreta" in texto
    assert texto.count(herramientas.INICIO_ENV) == 1
    assert "BLENDER_BIN='tools/blender-5.2.2/blender'" in texto
    assert "REELS_RENDER_ENGINE='cycles'" in texto
    # python-dotenv reads it as intended (single quotes: no escape sequences)
    dotenv = pytest.importorskip("dotenv")
    vals = dotenv.dotenv_values(env)
    assert vals["BLENDER_BIN"] == "tools/blender-5.2.2/blender" and vals["ELEVENLABS_API_KEY"] == "sk_secreta"


# --- template: copy and 3-way update ---------------------------------------------------------------------------------


def _plantilla(raiz: Path, archivos: dict[str, str]) -> Path:
    for rel, txt in archivos.items():
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text(txt, encoding="utf-8")
    return raiz


def test_actualizar_no_pisa_lo_del_alumno(tmp_path):
    v1 = _plantilla(tmp_path / "v1", {"reels/cli.py": "v1", "reels/a.py": "a1", "reels/b.py": "b1", "reels/viejo.py": "x",
                                      "docs/hipotesis.md": "plantilla", "docs/piezas.md": "p1", "CLAUDE.md": "c1",
                                      "pyproject.toml": "t"})
    proyecto = tmp_path / "alumno"
    plantilla.copiar(v1, "0.1.0", proyecto)
    (proyecto / "reels" / "b.py").write_text("b del alumno", encoding="utf-8")
    (proyecto / "docs" / "hipotesis.md").write_text("mis hipótesis", encoding="utf-8")
    (proyecto / "ideas").mkdir()
    (proyecto / "ideas" / "mia.md").write_text("idea", encoding="utf-8")
    (proyecto / ".env").write_text("ELEVENLABS_API_KEY=x", encoding="utf-8")

    v2 = _plantilla(tmp_path / "v2", {"reels/cli.py": "v2", "reels/a.py": "a2", "reels/b.py": "b2", "reels/nuevo.py": "n",
                                      "docs/hipotesis.md": "plantilla nueva", "docs/piezas.md": "p2", "CLAUDE.md": "c1",
                                      "pyproject.toml": "t"})
    plan = plantilla.planificar(v2, proyecto)
    assert plan["actualizar"] == ["docs/piezas.md", "reels/a.py", "reels/cli.py"]
    assert plan["conflictos"] == ["reels/b.py"]
    assert plan["memoria"] == ["docs/hipotesis.md"]
    assert plan["nuevos"] == ["reels/nuevo.py"]
    assert plan["retirar"] == ["reels/viejo.py"]
    propuestas = plantilla.aplicar(v2, "0.2.0", proyecto, plan)
    leer = lambda rel: (proyecto / rel).read_text(encoding="utf-8")  # noqa: E731
    assert leer("reels/a.py") == "a2" and leer("reels/nuevo.py") == "n"
    assert leer("reels/b.py") == "b del alumno"
    assert leer("docs/hipotesis.md") == "mis hipótesis"
    assert leer("ideas/mia.md") == "idea" and leer(".env") == "ELEVENLABS_API_KEY=x"
    assert not (proyecto / "reels" / "viejo.py").exists()
    assert (propuestas / "reels" / "b.py").read_text(encoding="utf-8") == "b2"
    copias = list((proyecto / ".fabrica" / "copias").iterdir())[0]
    assert (copias / "reels" / "a.py").read_text(encoding="utf-8") == "a1"
    assert (copias / "reels" / "viejo.py").exists()
    assert plantilla.manifiesto(proyecto)["version"] == "0.2.0"
    # a second update with the same template changes nothing
    plan2 = plantilla.planificar(v2, proyecto)
    assert not (plan2["nuevos"] or plan2["actualizar"] or plan2["retirar"])


def test_copiar_ignora_entornos_y_claves(tmp_path):
    origen = _plantilla(tmp_path / "p", {"reels/cli.py": "x", ".env": "SECRETO", ".venv/lib.py": "x",
                                         "remotion/node_modules/a.js": "x", "reels/__pycache__/c.pyc": "x"})
    n = plantilla.copiar(origen, "1", tmp_path / "dst")
    assert n == 1 and not (tmp_path / "dst" / ".env").exists()


def test_localizar_plantilla_del_repositorio():
    path, version = plantilla.localizar(descargar_si_falta=False)
    assert path == RAIZ / "plantilla"
    assert version == json.loads((RAIZ / "plugin" / ".claude-plugin" / "plugin.json").read_text())["version"]


# --- Claude Code settings --------------------------------------------------------------------------------------------


def test_ajustes_conservan_lo_que_habia(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text(json.dumps({"theme": "dark", "extraKnownMarketplaces": {
        "tarritoai": {"source": {"source": "github", "repo": "tarritoai/fabrica"}}}}), encoding="utf-8")
    assert ajustes.activar_auto_update() is True
    assert ajustes.poner_idioma("spanish") is True
    data = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert data["theme"] == "dark" and data["language"] == "spanish"
    assert data["extraKnownMarketplaces"]["tarritoai"] == {"source": {"source": "github", "repo": "tarritoai/fabrica"},
                                                           "autoUpdate": True}
    assert ajustes.activar_auto_update() is False
    assert list(tmp_path.glob("settings.json.antes-de-fabrica-*"))


def test_ajustes_no_tocan_un_json_roto(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text("{ roto", encoding="utf-8")
    with pytest.raises(FabricaError) as e:
        ajustes.activar_auto_update()
    assert e.value.codigo == "settings-invalido"
    assert (tmp_path / "settings.json").read_text(encoding="utf-8") == "{ roto"


# --- lesson checks ---------------------------------------------------------------------------------------------------


def _proyecto_minimo(raiz: Path) -> Path:
    """A project with just the course checker (no reels, no .venv): enough for the archivo/video/stamp lots."""
    for rel in (".claude/skills/tarrito/comprobar.py", "curso/comprobaciones.json"):
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_bytes((RAIZ / "plantilla" / rel).read_bytes())
    return raiz


def test_comprobar_delega_en_el_proyecto_y_migra_los_sellos(tmp_path, monkeypatch, capfd):
    p = _proyecto_minimo(tmp_path / "fabrica")
    (p / ".fabrica").mkdir()
    (p / ".fabrica" / "sellos.json").write_text(json.dumps({"1·4": {"titulo": "Instalar", "aprobado": "2026-05-01 18:30"}}),
                                                encoding="utf-8")
    monkeypatch.setenv("FFPROBE_BIN", str(tmp_path / "no-hay-ffprobe"))
    assert comprobar.normalizar("1.5") == comprobar.normalizar("01-5") == comprobar.normalizar("lote 1·5") == "1·5"
    assert comprobar.comprobar(p, "1.5") == 1  # no video yet: the project's script says what is missing
    (p / "episodes" / "humo").mkdir(parents=True)
    (p / "episodes" / "humo" / "final.mp4").write_bytes(b"\0" * 1000)
    assert comprobar.comprobar(p, "1·5") == 1  # almost empty
    (p / "episodes" / "humo" / "final.mp4").write_bytes(b"\0" * 300_000)
    assert comprobar.comprobar(p, "1-5") == 0
    assert "APROBADO · 1·5" in capfd.readouterr().out  # the project's script talks to the terminal directly
    progreso = json.loads((p / "curso" / "progreso.json").read_text(encoding="utf-8"))["sellos"]
    assert {"1·4", "1·5"} <= set(progreso) and progreso["1·4"].startswith("2026-05-01T18:30")
    assert {"1·4", "1·5"} <= set(comprobar.sellos(p))
    assert comprobar.comprobar(p, "99·9") == 2


def test_comprobar_antes_de_instalar(tmp_path, monkeypatch):
    args = {"revisar_carpeta": fabrica.revisar_carpeta, "info_sistema": fabrica.info_sistema}
    nube = tmp_path / "OneDrive" / "fabrica"
    assert comprobar.comprobar(nube, "1·1", **args) == 1
    buena = tmp_path / "fabrica"
    assert comprobar.comprobar(buena, "1.1", **args) == 0
    assert not buena.exists()  # no stamp, nothing written: «preparar» still sees a new folder
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-demo-123")
    assert comprobar.comprobar(buena, "1·3", **args) == 1
    with pytest.raises(FabricaError) as e:
        comprobar.comprobar(buena, "4·6", **args)
    assert e.value.codigo == "no-es-proyecto"


def test_comprobaciones_de_la_plantilla_son_validas():
    import importlib.util

    spec = importlib.util.spec_from_file_location("comprobar_plantilla",
                                                  RAIZ / "plantilla" / ".claude" / "skills" / "tarrito" / "comprobar.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data = json.loads((RAIZ / "plantilla" / "curso" / "comprobaciones.json").read_text(encoding="utf-8"))
    lotes = {x["lote"]: x for x in data["lotes"]}
    assert len(data["lotes"]) == len(lotes) == 50
    tipos = set(mod.TYPES) | {"pregunta", "lotes"}
    for lote, info in lotes.items():
        assert comprobar.normalizar(lote) == mod.lot_id(lote) == lote
        assert info["titulo"] and info["comprobaciones"] and info["aprobado"]
        assert all(c["tipo"] in tipos for c in info["comprobaciones"]), lote
    # the installer's checks live here now (one source of truth)
    assert [c["tipo"] for c in lotes["1·1"]["comprobaciones"]] == ["carpeta"]
    assert [c["tipo"] for c in lotes["1·4"]["comprobaciones"]] == ["archivo", "doctor"]
    assert [c["tipo"] for c in lotes["1·5"]["comprobaciones"]] == ["video"]
    assert set(comprobar.ANTES_DE_INSTALAR) <= set(lotes)


# --- known errors ----------------------------------------------------------------------------------------------------


def test_tabla_de_errores_bien_formada():
    ids = set()
    for e in diagnostico.tabla():
        assert {"id", "so", "cuando", "texto", "patrones", "significa", "arreglo", "origen"} <= set(e)
        assert e["origen"] in ("probado", "documentado", "esperado")
        assert e["id"] not in ids
        ids.add(e["id"])


@pytest.mark.parametrize("texto,esperado", [
    ("bash: line 1: ./rhubarb: Bad CPU type in executable", "mac-rosetta"),
    ("✘ Failed to add marketplace: … Executable not found in $PATH: \"git\"", "plugin-sin-git"),
    ("PermissionError: [WinError 5] Access is denied: 'C:\\\\fabrica\\\\tools'", "acceso-denegado"),
    ("The code execution cannot proceed because VCOMP140.DLL was not found.", "windows-dll"),
    ("[Parsed_afir_0 @ 0x55] Option 'irnorm' not found", "ffmpeg-viejo"),
    ("./whisper-cli: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.34' not found", "glibc-vieja"),
])
def test_diagnostico_reconoce_errores_reales(texto, esperado):
    assert diagnostico.diagnosticar(texto)[0]["id"] == esperado


def test_todos_los_codigos_del_instalador_estan_en_la_tabla():
    import re

    fuentes = "".join(p.read_text(encoding="utf-8") for p in (RAIZ / "plugin" / "scripts").rglob("*.py"))
    codigos = set(re.findall(r'FabricaError\([^)]*?,\s*"([a-z0-9-]+)"', fuentes, re.S))
    codigos |= set(re.findall(r"\[código: ([a-z0-9-]+)\]", fuentes))
    sin_fila = {c for c in codigos if not diagnostico.por_codigo(c)} - {"uso", "doctor", "humo", "carpeta",
                                                                          "desconocido", "lote-desconocido"}
    sin_fila = {c for c in sin_fila if not c.endswith("-no-arranca")}
    assert not sin_fila, f"códigos sin explicación en errores.json: {sin_fila}"


def test_markdown_de_errores_al_dia():
    md = (RAIZ / "plugin" / "skills" / "tarrito" / "errores-conocidos.md").read_text(encoding="utf-8")
    assert md == diagnostico.markdown(), "ejecuta: python tools/gen_errores.py"


# --- choosing the folder ---------------------------------------------------------------------------------------------


def test_carpeta_en_onedrive_se_rechaza(tmp_path):
    errores, _, _ = fabrica.revisar_carpeta(tmp_path / "OneDrive" / "Documentos" / "fabrica")
    assert any("OneDrive" in e for e in errores)


def test_carpeta_con_cosas_se_rechaza_y_fabrica_se_reconoce(tmp_path):
    (tmp_path / "fotos.jpg").write_text("x", encoding="utf-8")
    assert fabrica.revisar_carpeta(tmp_path)[2] == "ocupada"
    (tmp_path / "fotos.jpg").unlink()
    (tmp_path / "logs").mkdir()
    assert fabrica.revisar_carpeta(tmp_path)[2] == "vacia"
    (tmp_path / "reels").mkdir()
    (tmp_path / "reels" / "cli.py").write_text("", encoding="utf-8")
    assert fabrica.revisar_carpeta(tmp_path)[2] == "fabrica"


def test_skills_usan_solo_el_instalador():
    """The skills must call the robust scripts, with the exact command, not improvise installs."""
    for skill in (RAIZ / "plugin" / "skills").glob("*/SKILL.md"):
        texto = skill.read_text(encoding="utf-8")
        assert texto.startswith("---\nname: "), skill
        assert '"${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.sh"' in texto, skill
        assert 'powershell -NoProfile -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/scripts/fabrica.ps1"' in texto


def test_candado_impide_dos_instalaciones_a_la_vez(tmp_path):
    from fabrica_lib.comun import candado

    (tmp_path / ".fabrica").mkdir()
    (tmp_path / ".fabrica" / "en-marcha.lock").write_text(f"{os.getppid()} herramientas\n", encoding="utf-8")
    with pytest.raises(FabricaError) as e:
        with candado(tmp_path):
            pass
    assert e.value.codigo == "en-marcha"
    (tmp_path / ".fabrica" / "en-marcha.lock").write_text("999999999 viejo\n", encoding="utf-8")  # dead process
    with candado(tmp_path):
        assert (tmp_path / ".fabrica" / "en-marcha.lock").exists()
    assert not (tmp_path / ".fabrica" / "en-marcha.lock").exists()
