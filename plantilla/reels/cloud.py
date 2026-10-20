"""Render a built scene on a rented GPU (Vast.ai) and bring back renders/scene.mp4.

Flow: pick the cheapest suitable offer -> create the instance (graphics enabled: EEVEE needs it) ->
install Blender -> upload scene.blend + phone screens + render.py -> render -> encode -> download ->
ALWAYS destroy the instance (also on errors / Ctrl+C). Only the scene goes up: never .env or keys.

Needs VAST_API_KEY in .env. A dedicated SSH key (~/.ssh/reels_vast) is created and registered once.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import httpx
from rich.console import Console

from reels import cost
from reels import system
from reels.assets import ROOT, episode_dir

console = Console()

API = "https://console.vast.ai/api/v0"
BLENDER_VERSION = "5.2.2"
BLENDER_URL = f"https://download.blender.org/release/Blender{BLENDER_VERSION.rsplit('.', 1)[0]}/blender-{BLENDER_VERSION}-linux-x64.tar.xz"
IMAGE = "nvidia/cuda:12.4.1-runtime-ubuntu22.04"  # (nvidia/opengl exits on Vast: no long-running process)
# Consumer/workstation RTX only: EEVEE draws like a game and needs the graphics side of the GPU.
GPUS = ["RTX 4090", "RTX 5090", "RTX 4080S", "RTX 4080", "RTX 5080", "RTX 5070 Ti", "RTX 4070S Ti", "RTX 4070 Ti",
        "RTX 4070S", "RTX 4070", "RTX 3090", "RTX 3080 Ti", "RTX 3080", "RTX A5000", "RTX A4000", "RTX 3060"]
FAST_GPUS = ["RTX 5090", "RTX 4090", "RTX 4080S", "RTX 4080"]  # --fast: heavy scenes (the miniseries world)
MAX_PRICE = 0.6  # $/h
MAX_HOURS = 1.5  # hard stop: the instance is destroyed after this long no matter what
SSH_KEY = Path.home() / ".ssh" / "reels_vast"
EU = {"ES", "PT", "FR", "DE", "IT", "NL", "BE", "LU", "IE", "GB", "UK", "CH", "AT", "DK", "SE", "NO", "FI", "PL", "CZ", "SK",
      "HU", "RO", "BG", "GR", "SI", "HR", "EE", "LV", "LT", "IS"}


class CloudError(RuntimeError):
    pass


def _client() -> httpx.Client:
    key = os.environ.get("VAST_API_KEY", "").strip()
    if not key:
        raise CloudError("falta VAST_API_KEY en .env (console.vast.ai → Account → API Keys)")
    return httpx.Client(base_url=API, headers={"Authorization": f"Bearer {key}"}, timeout=60)


def _check(r: httpx.Response) -> dict:
    if r.status_code >= 400:
        raise CloudError(f"Vast HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def ensure_ssh_key(c: httpx.Client) -> None:
    if not SSH_KEY.exists():
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-C", "reels-vast", "-f", str(SSH_KEY)], check=True,
                       capture_output=True)
    pub = SSH_KEY.with_suffix(".pub").read_text(encoding="utf-8").strip()
    keys = _check(c.get("/ssh/"))
    listed = keys if isinstance(keys, list) else keys.get("keys", [])
    if not any(pub.split()[1] in (k.get("public_key") or k.get("key") or "") for k in listed):
        _check(c.post("/ssh/", json={"ssh_key": pub}))
        console.print("  clave SSH registrada en Vast")


def find_offers(c: httpx.Client, max_price: float = MAX_PRICE, offer_id: int | None = None, fast: bool = False) -> list[dict]:
    q = {
        "verified": {"eq": True}, "rentable": {"eq": True}, "rented": {"eq": False}, "num_gpus": {"eq": 1},
        "gpu_name": {"in": FAST_GPUS if fast else GPUS}, "reliability2": {"gte": 0.97}, "inet_down": {"gte": 300}, "inet_up": {"gte": 100},
        "disk_space": {"gte": 25}, "dph_total": {"lte": max_price}, "type": "on-demand", "order": [["dph_total", "asc"]],
    }
    if offer_id:  # a specific offer: same filters, any price, then pick it by id
        q["dph_total"] = {"lte": 5.0}
    offers = _check(c.get("/bundles/", params={"q": json.dumps(q)})).get("offers", [])
    if offer_id:
        offers = [o for o in offers if o["id"] == offer_id]
        if not offers:
            raise CloudError(f"la oferta {offer_id} ya no está disponible")
    if not offers:
        raise CloudError("no hay ofertas que cumplan los requisitos (prueba subiendo --max-price)")
    # Europe first (fast uploads from Spain), then cheapest per unit of speed (TFLOPS per dollar).
    def rank(o):
        eu = (o.get("geolocation") or "").split(",")[-1].strip() in EU
        return (not eu, o["dph_total"] / max(o.get("total_flops") or 1, 1))

    return sorted(offers, key=rank)


def create(c: httpx.Client, offer: dict) -> int:
    body = {
        "client_id": "me", "image": IMAGE, "disk": 25, "runtype": "ssh",
        "env": {"NVIDIA_DRIVER_CAPABILITIES": "all", "NVIDIA_VISIBLE_DEVICES": "all"},
        "label": "reels-render",
    }
    res = _check(c.put(f"/asks/{offer['id']}/", json=body))
    if not res.get("success"):
        raise CloudError(f"no se pudo alquilar: {res}")
    return int(res["new_contract"])


def wait_ready(c: httpx.Client, iid: int, timeout: float = 300) -> tuple[str, int]:
    t0 = time.time()
    while time.time() - t0 < timeout:
        inst = _check(c.get(f"/instances/{iid}/")).get("instances") or {}
        status = inst.get("actual_status")
        if status == "running" and inst.get("ssh_host"):
            return inst["ssh_host"], int(inst["ssh_port"])
        console.print(f"[dim]  esperando a la máquina… ({status or 'creando'})[/]")
        time.sleep(10)
    raise CloudError("la máquina no arrancó a tiempo")


def destroy(c: httpx.Client, iid: int) -> None:
    for _ in range(3):
        try:
            c.delete(f"/instances/{iid}/")
            console.print(f"  máquina {iid} destruida")
            return
        except httpx.HTTPError:
            time.sleep(3)
    console.print(f"[red bold]  ⚠ no pude destruir la máquina {iid}: bórrala a mano en console.vast.ai[/]")


def _ssh(host: str, port: int) -> list[str]:
    return ["ssh", "-i", str(SSH_KEY), "-p", str(port), "-o", "StrictHostKeyChecking=no", "-o", f"UserKnownHostsFile={system.DEVNULL}",
            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=20", f"root@{host}"]


def run(host: str, port: int, cmd: str, retries: int = 1) -> None:
    for attempt in range(retries):
        r = subprocess.run([*_ssh(host, port), cmd])
        if r.returncode == 0:
            return
        time.sleep(8)
    raise CloudError(f"falló en remoto: {cmd[:80]}")


def scp(host: str, port: int, src: list[str], dest: str, download: bool = False) -> None:
    base = ["scp", "-i", str(SSH_KEY), "-P", str(port), "-o", "StrictHostKeyChecking=no", "-o", f"UserKnownHostsFile={system.DEVNULL}",
            "-o", "LogLevel=ERROR", "-q"]
    args = [*base, f"root@{host}:{src[0]}", dest] if download else [*base, "-r", *src, f"root@{host}:{dest}"]
    if subprocess.run(args).returncode != 0:
        raise CloudError("falló la transferencia de archivos")


REMAP = '''import bpy, os, re
# Phone screens were linked with this computer's paths (maybe C:\\...): point them at the uploaded copies.
d = os.environ["REELS_DIR"]
for img in bpy.data.images:
    if img.source == "MOVIE":
        img.filepath = os.path.join(d, "screens", re.split(r"[\\\\/]", img.filepath)[-1])
'''


SETUP = (
    "export DEBIAN_FRONTEND=noninteractive && apt-get -qq update && apt-get -qq install -y "
    "wget xz-utils ffmpeg libegl1 libgl1 libglu1-mesa libxrender1 libxi6 libxkbcommon0 libsm6 libxfixes3 "
    "libxxf86vm1 libxkbcommon-x11-0 libvulkan1 > /dev/null 2>&1 && "
    f"wget -q {BLENDER_URL} -O /tmp/b.tar.xz && tar -xf /tmp/b.tar.xz -C /opt && mv /opt/blender-* /opt/blender && mkdir -p /work/screens"
)
# Some hosts only mount the compute side of the driver. Then copy the graphics (EGL/GL) libraries out of
# the official NVIDIA installer of the *same* version as the host driver (no install, no kernel module).
NVIDIA_GL = r"""
L=/usr/lib/x86_64-linux-gnu
if ! ls $L/libEGL_nvidia.so.0 >/dev/null 2>&1; then
  V=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
  cd /tmp && wget -q https://us.download.nvidia.com/XFree86/Linux-x86_64/$V/NVIDIA-Linux-x86_64-$V.run -O nv.run \
    && sh nv.run --extract-only --target /tmp/nv > /dev/null
  for f in libEGL_nvidia libGLX_nvidia libGLESv2_nvidia libnvidia-eglcore libnvidia-glcore libnvidia-glsi libnvidia-tls \
           libnvidia-gpucomp libnvidia-glvkspirv libnvidia-egl-gbm; do
    cp -n /tmp/nv/$f.so.* $L/ 2>/dev/null
  done
  ln -sf $L/libEGL_nvidia.so.$V $L/libEGL_nvidia.so.0
  ln -sf $L/libGLX_nvidia.so.$V $L/libGLX_nvidia.so.0
  ln -sf $L/libGLESv2_nvidia.so.$V $L/libGLESv2_nvidia.so.2
  mkdir -p /usr/share/glvnd/egl_vendor.d
  printf '{"file_format_version":"1.0.0","ICD":{"library_path":"libEGL_nvidia.so.0"}}' > /usr/share/glvnd/egl_vendor.d/10_nvidia.json
  ldconfig
  echo "librerias graficas de NVIDIA $V instaladas"
fi
"""
# One real frame of the scene: proves the GPU is drawing (software GL would say llvmpipe/Mesa).
PROBE = (
    "cd /work && REELS_DIR=/work timeout 300 /opt/blender/blender -b scene.blend -P _remap.py "
    "--python-expr 'import bpy,gpu,time; s=bpy.context.scene; s.render.resolution_percentage=50; "
    "s.eevee.taa_render_samples=8; s.frame_set(10); s.render.filepath=\"/tmp/probe.png\"; t=time.time(); "
    "bpy.ops.render.render(write_still=True); "
    "print(\"PROBE\", round(time.time()-t,1), gpu.platform.vendor_get(), gpu.platform.renderer_get())' 2>&1 | grep PROBE"
)


def _prepare(c: httpx.Client, offer: dict, out: Path, blend: Path) -> tuple[int, str, int]:
    """Rent, boot, install, upload and prove the GPU draws. Any failure destroys the machine."""
    iid = create(c, offer)
    try:
        host, port = wait_ready(c, iid)
        console.print(f"  máquina {iid} lista ({host}:{port})")
        run(host, port, "true", retries=6)  # sshd can take a moment
        t0 = time.time()
        run(host, port, SETUP)
        run(host, port, NVIDIA_GL)
        console.print(f"[dim]  Blender instalado en {time.time() - t0:.0f}s[/]")
        remap = out / "renders" / "_remap.py"
        remap.parent.mkdir(parents=True, exist_ok=True)  # a fresh episode has no renders/ yet
        remap.write_text(REMAP, encoding="utf-8")
        scp(host, port, [str(blend), str(ROOT / "blender/render.py"), str(remap)], "/work/")
        scp(host, port, [str(p) for p in (out / "screens").glob("*.mp4")] or [str(remap)], "/work/screens/")
        res = subprocess.run([*_ssh(host, port), PROBE], capture_output=True, text=True, encoding="utf-8", errors="replace")
        line = (res.stdout.strip().splitlines() or ["PROBE ? ? ?"])[-1]
        console.print(f"  fotograma de prueba: {line.replace('PROBE ', '')}")
        if "NVIDIA" not in line or "llvmpipe" in line.lower():
            raise CloudError("la GPU no dibuja en esta máquina (render por software)")
        return iid, host, port
    except Exception:
        destroy(c, iid)
        raise


def render(slug: str, quality: str = "final", max_price: float = MAX_PRICE, offer_id: int | None = None, fast: bool = False) -> Path:
    out = episode_dir(slug)
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    blend = out / "scene.blend"
    if not blend.exists():
        raise CloudError("no hay scene.blend: ejecuta antes `reels build`")
    with _client() as c:
        ensure_ssh_key(c)
        # Cheap offers vanish in seconds, some hosts never boot, some lack GPU graphics:
        # walk down the ranking until one machine passes every check.
        iid = host = port = None
        spent = 0.0
        for offer in find_offers(c, max_price, offer_id, fast)[:12]:
            console.print(f"  oferta {offer['id']}: {offer['gpu_name']} · {offer.get('geolocation', '?')} · ${offer['dph_total']:.3f}/h")
            t_try = time.time()
            time.sleep(2)
            try:
                iid, host, port = _prepare(c, offer, out, blend)
                break
            except CloudError as e:
                spent += (time.time() - t_try) / 3600 * offer["dph_total"]
                console.print(f"[yellow]    descartada: {str(e)[:90]}[/]")
        if iid is None:
            raise CloudError("ninguna máquina pasó las comprobaciones")
        t_start = t_try  # Vast bills from creation: preparing the machine (Blender, upload) counts too
        try:
            t0 = time.time()
            render_cmd = (
                f"cd /work && REELS_DIR=/work timeout {int(MAX_HOURS * 3600)} /opt/blender/blender --python-exit-code 1 -b scene.blend "
                f"-P _remap.py -P render.py -- /work/frames {quality} full > /tmp/render.log 2>&1"
            )
            run(host, port, render_cmd)
            # EEVEE drops shadows silently when its pool overflows: say so instead of shipping it.
            warn = subprocess.run([*_ssh(host, port), "grep -c 'Shadow buffer full' /tmp/render.log"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if warn.stdout.strip() not in ("", "0"):
                console.print(f"[yellow]  ⚠ faltan sombras en {warn.stdout.strip()} avisos de Blender (shadow_pool_size en build_scene.py)[/]")
            encode = (
                f"cd /work && ffmpeg -y -loglevel error -framerate {tl['fps']} -start_number 0 -i frames/%04d.png "
                f"-vf scale={tl['width']}:{tl['height']}:flags=lanczos -c:v libx264 -pix_fmt yuv420p -crf 16 scene.mp4"
            )
            run(host, port, encode)
            console.print(f"[dim]  render remoto en {time.time() - t0:.0f}s[/]")
            video = out / "renders" / "scene.mp4"
            scp(host, port, ["/work/scene.mp4"], str(video), download=True)
            return video
        finally:
            destroy(c, iid)
            hours = (time.time() - t_start) / 3600
            usd = spent + hours * offer["dph_total"]
            cost.log(out, "render_cloud", usd, gpu=offer["gpu_name"], minutes=round(hours * 60, 1))
            console.print(f"  coste aproximado: ${usd:.3f} ({hours * 60:.1f} min de máquina, preparación incluida)")


def cleanup() -> int:
    """Destroy every reels-render instance still alive (e.g. after the computer slept mid-render)."""
    with _client() as c:
        inst = _check(c.get("https://console.vast.ai/api/v1/instances/")).get("instances", [])
        mine = [i for i in inst if i.get("label") == "reels-render"]
        for i in mine:
            destroy(c, int(i["id"]))
        return len(mine)
