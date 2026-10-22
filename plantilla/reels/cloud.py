"""Render a built scene on a rented GPU (Vast.ai) and bring back renders/scene.mp4.

Flow: pick the best suitable offer -> create the instance (graphics enabled: EEVEE needs it) with a GUARD that
starts at boot -> install Blender -> upload scene.blend + phone screens + render.py -> render (detached on the
machine, polled from here) -> encode -> download -> destroy the instance (also on errors, Ctrl+C or SIGTERM).
Only the scene goes up: never .env or keys.

Money safety, in layers (a rented GPU bills by the second until it is DESTROYED; «Stop» still bills the disk):
1. here: `finally` destroys the machine; SIGTERM / a closed terminal also run it (system.exit_cleanly_on_terminate);
2. on the machine: the guard (GUARD below, Vast's `onstart`) destroys the machine by itself, with the per-instance
   key Vast gives every container (CONTAINER_API_KEY: it can only start/stop/destroy that one machine), when this
   computer stops sending signs of life for IDLE_MIN minutes (power cut, no internet, laptop shut) or when the
   machine has lived LIFETIME_H hours, whatever happens;
3. next time: every machine this computer rented is written down in .cache/nube/ while its process lives; `reels
   doctor` lists the ones nobody is using (orphans) and `reels render --cloud` / `reels cloud-cleanup` destroy them.

Needs VAST_API_KEY in .env, and ssh + scp + ssh-keygen (the doctor checks them). A dedicated SSH key
(~/.ssh/reels_vast) is created and registered once.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime
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
LABEL = "reels-render"
# Consumer/workstation RTX only: EEVEE draws like a game and needs the graphics side of the GPU.
GPUS = ["RTX 4090", "RTX 5090", "RTX 4080S", "RTX 4080", "RTX 5080", "RTX 5070 Ti", "RTX 4070S Ti", "RTX 4070 Ti",
        "RTX 4070S", "RTX 4070", "RTX 3090", "RTX 3080 Ti", "RTX 3080", "RTX A5000", "RTX A4000", "RTX 3060"]
FAST_GPUS = ["RTX 5090", "RTX 4090", "RTX 4080S", "RTX 4080"]  # --fast: heavy scenes (the miniseries world)
MAX_PRICE = 0.6  # $/h
MAX_HOURS = 1.5  # Blender itself is stopped after this long
LIFETIME_H = MAX_HOURS + 0.75  # the guard destroys the machine after this long no matter what (setup + download too)
IDLE_MIN = 20  # the guard destroys the machine after this many minutes without signs of life from this computer
HEARTBEAT_S = 60  # how often this computer says «still here» to the machine
POLL_S = 30  # how often the render is checked
LOST_MIN = 15  # give up after this many minutes without being able to reach the machine
SSH_KEY = Path.home() / ".ssh" / "reels_vast"
# Rented machines reuse host:port with new keys: a known_hosts of our own, emptied before each render (not /dev/null:
# Git for Windows' ssh would read «nul» as a file name).
KNOWN_HOSTS = SSH_KEY.with_name("reels_vast_known_hosts")
RECORDS = ROOT / ".cache" / "nube"  # one <instance id>.json per machine rented from this folder (deleted on destroy)
GUARD_DIR = "/root/reels-guard"

# Where the offers should be: close to the student makes uploads faster. «europa», «america» or «cualquiera»; by
# default it is guessed from this computer's time zone (UTC-10..-2 → America, UTC-1..+4 → Europe).
EU = {"ES", "PT", "FR", "DE", "IT", "NL", "BE", "LU", "IE", "GB", "UK", "CH", "AT", "DK", "SE", "NO", "FI", "PL", "CZ", "SK",
      "HU", "RO", "BG", "GR", "SI", "HR", "EE", "LV", "LT", "IS"}
AMERICA = {"US", "CA", "MX", "GT", "SV", "HN", "NI", "CR", "PA", "CU", "DO", "PR", "CO", "VE", "EC", "PE", "BO", "CL",
           "AR", "UY", "PY", "BR"}
REGIONS = {"europa": EU, "america": AMERICA}
FAR_PENALTY = 1.3  # an offer far away is taken only if it is >30 % better value (speed per dollar) than a near one


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


# --- the guard: the machine destroys itself if nobody is looking after it ----------------------------------------

# Runs at boot as Vast's `onstart` (max ~4000 characters) and again through ssh, in case a host ignored it
# (idempotent). The guard needs curl, absent from the CUDA image: it installs it first, then says `ready` (SETUP
# waits for that: two apt-get at once would fail). It checks its per-instance key with a harmless «start» (a no-op
# on a running machine) and writes `armada`, or why not, to its `state` file.
GUARD_SH = r"""G=__DIR__; LIFE=__LIFE__; IDLE=__IDLE__; T=__TICK__
echo $$ > $G/pid
log(){ echo "$(date -u +%H:%M:%S) $*" >> $G/log; }
env1(){ tr '\0' '\n' < /proc/1/environ 2>/dev/null | sed -n "s/^$1=//p" | head -1; }
K=${CONTAINER_API_KEY:-$(env1 CONTAINER_API_KEY)}; I=${CONTAINER_ID:-$(env1 CONTAINER_ID)}
[ -z "$K" ] && [ -f /root/.vast_api_key ] && K=$(cat /root/.vast_api_key)
U=https://console.vast.ai/api/v0/instances/$I/
call(){
  c=$(curl -s -o /dev/null -w '%{http_code}' -m 30 -X $1 -H "Authorization: Bearer $K" -H 'Content-Type: application/json' -d "$2" $U)
  case $c in 2*) ;; *) c=$(curl -s -o /dev/null -w '%{http_code}' -m 30 -X $1 -H 'Content-Type: application/json' -d "$2" "$U?api_key=$K");; esac
  echo $c
}
if ! command -v curl > /dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  for n in 1 2 3; do apt-get -qq update > /dev/null 2>&1; apt-get -qq install -y curl ca-certificates > /dev/null 2>&1 && break; sleep 15; done
fi
touch $G/ready
if [ -z "$K" ] || [ -z "$I" ]; then echo sin-clave > $G/state
elif ! command -v curl > /dev/null; then echo sin-curl > $G/state
else c=$(call PUT '{"state":"running"}'); case $c in 2*) echo armada > $G/state;; *) echo "api-$c" > $G/state;; esac; fi
log "seguro: $(cat $G/state)"
B=$(cat $G/born)
while :; do
  N=$(date +%s); A=$(stat -c %Y $G/alive 2>/dev/null || echo $B)
  if [ $((N-B)) -gt $LIFE ]; then W="tiempo maximo"; break; fi
  if [ $((N-A)) -gt $IDLE ]; then W="sin noticias de la computadora"; break; fi
  sleep $T
done
log "autodestruccion: $W"
n=0
while :; do  # until it works: if destroying keeps failing, at least stop the GPU billing (the disk still bills)
  c=$(call DELETE ''); log "destruir: $c"; case $c in 2*|404) exit 0;; esac
  n=$((n+1)); [ $n -eq 5 ] && log "parar: $(call PUT '{"state":"stopped"}')"
  sleep $T
done
"""

GUARD_START = """G=__DIR__
mkdir -p $G
[ -e $G/born ] || date +%s > $G/born
touch $G/alive
if [ -e $G/pid ] && kill -0 "$(cat $G/pid)" 2> /dev/null; then exit 0; fi
cat > $G/guard.sh << 'REELS_GUARD'
__GUARD__REELS_GUARD
nohup bash $G/guard.sh > $G/out.log 2>&1 < /dev/null &
"""


def guard_script(lifetime_s: float = LIFETIME_H * 3600, idle_s: float = IDLE_MIN * 60, tick_s: int = 30,
                 where: str = GUARD_DIR) -> str:
    """The bash script that starts the guard on the machine (Vast's `onstart`, and again through ssh)."""
    body = (GUARD_SH.replace("__DIR__", where).replace("__LIFE__", str(int(lifetime_s)))
            .replace("__IDLE__", str(int(idle_s))).replace("__TICK__", str(tick_s)))
    return GUARD_START.replace("__DIR__", where).replace("__GUARD__", body)


class Heartbeat(threading.Thread):
    """Tells the machine «this computer is still here» every HEARTBEAT_S seconds (the guard counts the silence)."""

    def __init__(self, host: str, port: int) -> None:
        super().__init__(daemon=True)
        self.host, self.port = host, port
        self._done = threading.Event()

    def run(self) -> None:
        while True:
            try:
                subprocess.run([*_ssh(self.host, self.port), f"touch {GUARD_DIR}/alive"], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
            except (OSError, subprocess.TimeoutExpired, RuntimeError):
                pass
            if self._done.wait(HEARTBEAT_S):
                return

    def stop(self) -> None:
        self._done.set()


# --- machines rented from this computer (to find the orphans later) ---------------------------------------------


def _remember(iid: int, offer: dict, slug: str) -> None:
    RECORDS.mkdir(parents=True, exist_ok=True)
    data = {"id": iid, "pid": os.getpid(), "slug": slug, "gpu": offer.get("gpu_name"), "usd_h": offer.get("dph_total"),
            "created": datetime.now().astimezone().isoformat(timespec="seconds")}
    (RECORDS / f"{iid}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _forget(iid: int) -> None:
    (RECORDS / f"{iid}.json").unlink(missing_ok=True)


def in_use_here() -> set[int]:
    """Ids of the machines that a render still running on this computer is using."""
    ids = set()
    for f in RECORDS.glob("*.json") if RECORDS.is_dir() else []:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if system.pid_alive(int(data.get("pid") or 0)):
            ids.add(int(data["id"]))
    return ids


def list_machines(c: httpx.Client) -> list[dict]:
    """Every machine of the fábrica (label reels-render) in the Vast account, running or not (all of them bill)."""
    try:
        data = _check(c.get("https://console.vast.ai/api/v1/instances/"))
    except (CloudError, httpx.HTTPError):
        data = _check(c.get("/instances/", params={"owner": "me"}))
    return [i for i in data.get("instances") or [] if i.get("label") == LABEL]


def orphans(c: httpx.Client) -> tuple[list[dict], list[dict]]:
    """(machines nobody is using, machines a render on this computer is using right now)."""
    busy = in_use_here()
    machines = list_machines(c)
    alive = {int(m["id"]) for m in machines}
    for f in RECORDS.glob("*.json") if RECORDS.is_dir() else []:  # records of machines that no longer exist
        if f.stem.isdigit() and int(f.stem) not in alive and int(f.stem) not in busy:
            f.unlink(missing_ok=True)
    return [m for m in machines if int(m["id"]) not in busy], [m for m in machines if int(m["id"]) in busy]


def destroy_orphans(c: httpx.Client, everything: bool = False) -> tuple[list[dict], list[dict]]:
    """Destroy the machines nobody is using (all of them with `everything`). Returns (destroyed, left in use)."""
    lost, busy = orphans(c)
    targets = lost + (busy if everything else [])
    done = [m for m in targets if destroy(c, int(m["id"]))]
    return done, [] if everything else busy


def cleanup(everything: bool = False) -> int:
    """Destroy every reels-render machine nobody is using (e.g. after the computer switched off mid-render)."""
    with _client() as c:
        return len(destroy_orphans(c, everything)[0])


# --- Vast -----------------------------------------------------------------------------------------------------------


def ensure_ssh_key(c: httpx.Client) -> None:
    if not SSH_KEY.exists():
        SSH_KEY.parent.mkdir(parents=True, exist_ok=True)  # a fresh Windows or Mac user may have no ~/.ssh yet
        p = subprocess.run([system.ssh_tool("ssh-keygen"), "-q", "-t", "ed25519", "-N", "", "-C", "reels-vast",
                            "-f", str(SSH_KEY)], capture_output=True, stdin=subprocess.DEVNULL)
        if p.returncode != 0 or not SSH_KEY.exists():
            why = system.tail((p.stderr or p.stdout or b"").decode("utf-8", "replace"))
            raise CloudError(f"no pude crear la clave SSH ({SSH_KEY}): {why}")
    pub = SSH_KEY.with_suffix(".pub").read_text(encoding="utf-8").strip()
    keys = _check(c.get("/ssh/"))
    listed = keys if isinstance(keys, list) else keys.get("keys", [])
    if not any(pub.split()[1] in (k.get("public_key") or k.get("key") or "") for k in listed):
        _check(c.post("/ssh/", json={"ssh_key": pub}))
        console.print("  clave SSH registrada en Vast")


def home_region() -> str:
    """«europa», «america» or «cualquiera»: VAST_REGION in .env, else guessed from this computer's time zone."""
    chosen = os.environ.get("VAST_REGION", "").strip().lower().replace("é", "e")
    if chosen in ("europa", "america", "cualquiera"):
        return chosen
    offset = datetime.now().astimezone().utcoffset()
    hours = offset.total_seconds() / 3600 if offset else 0.0
    if -10 <= hours <= -2:
        return "america"  # from Mexico and California to Buenos Aires and São Paulo
    if -1 <= hours <= 4:
        return "europa"  # Spain (also the Canary Islands), Portugal, the rest of Europe
    return "cualquiera"


def country(offer: dict) -> str:
    return (offer.get("geolocation") or "").split(",")[-1].strip().upper()


def rank_offers(offers: list[dict], region: str) -> list[dict]:
    """Best value first (price per unit of speed); offers far from the student need to be >30 % better value,
    because the scene has to travel there and back over a home connection."""
    near = REGIONS.get(region)

    def key(o: dict) -> float:
        value = o["dph_total"] / max(o.get("total_flops") or 1, 1)
        return value * (FAR_PENALTY if near is not None and country(o) not in near else 1.0)

    return sorted(offers, key=key)


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
    return rank_offers(offers, home_region())


def create(c: httpx.Client, offer: dict) -> int:
    body = {
        "client_id": "me", "image": IMAGE, "disk": 25, "runtype": "ssh",
        "env": {"NVIDIA_DRIVER_CAPABILITIES": "all", "NVIDIA_VISIBLE_DEVICES": "all"},
        "label": LABEL, "onstart": guard_script(),
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


def destroy(c: httpx.Client, iid: int) -> bool:
    """Destroy a machine (the only thing that stops the billing: «Stop» keeps charging for the disk)."""
    for attempt in range(5):
        try:
            r = c.delete(f"/instances/{iid}/")
            ok = r.status_code == 404 or (r.status_code < 400 and (r.json() if r.content else {}).get("success", True))
            if ok:
                _forget(iid)
                console.print(f"  máquina {iid} destruida")
                return True
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(3 * (attempt + 1))
    console.print(f"[red bold]  ⚠ no pude destruir la máquina {iid}: bórrala a mano en console.vast.ai (Instances → "
                  f"papelera) o ejecuta `uv run reels cloud-cleanup`. Si tenía el seguro puesto, se destruirá sola en "
                  f"menos de {IDLE_MIN} min.[/]")
    return False


# --- ssh: the same on Windows, Mac and Linux -------------------------------------------------------------------------

# Scripts travel to the machine through ssh's stdin and run there with bash: never as a command-line argument, so
# PowerShell / cmd (Windows), zsh (Mac) and bash (Linux) cannot mangle quotes, $ or newlines on the way.
REMOTE_RUNNER = "f=$(mktemp); cat > $f; bash $f < /dev/null; r=$?; rm -f $f; exit $r"


def _ssh_opts() -> list[str]:
    # The known_hosts path goes quoted and with forward slashes: ssh splits option values on spaces
    # ("C:\\Users\\María José\\…") and both Windows OpenSSH and Git's ssh understand C:/….
    return ["-i", str(SSH_KEY), "-o", "StrictHostKeyChecking=no", "-o", f'UserKnownHostsFile="{KNOWN_HOSTS.as_posix()}"',
            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=20", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
            "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=4"]


def _ssh(host: str, port: int) -> list[str]:
    return [system.ssh_tool("ssh"), *_ssh_opts(), "-p", str(port), f"root@{host}"]


def remote(host: str, port: int, script: str, capture: bool = False, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run a bash script on the machine (stdout+stderr captured as bytes with `capture`, else shown)."""
    out = subprocess.PIPE if capture else None
    try:
        return subprocess.run([*_ssh(host, port), REMOTE_RUNNER], input=script.encode("utf-8"), stdout=out,
                              stderr=subprocess.STDOUT if capture else None, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess([], 124, b"", b"")


def _text(p: subprocess.CompletedProcess) -> str:
    return (p.stdout or b"").decode("utf-8", "replace") if isinstance(p.stdout, bytes) else (p.stdout or "")


def run(host: str, port: int, script: str, retries: int = 1, timeout: float | None = 3600) -> None:
    for attempt in range(retries):
        if remote(host, port, script, timeout=timeout).returncode == 0:
            return
        if attempt < retries - 1:
            time.sleep(8)
    raise CloudError(f"falló en remoto: {script.strip().splitlines()[0][:80]}")


def _remote_size(host: str, port: int, path: str) -> int:
    p = remote(host, port, f"stat -c %s {path}", capture=True, timeout=60)
    text = _text(p).strip()
    return int(text) if p.returncode == 0 and text.isdigit() else -1


def upload(host: str, port: int, local: Path, dest: str) -> None:
    """Copy a file to the machine through ssh (no scp: its protocol and its «C:» handling differ between OpenSSH
    versions and systems), and check that it arrived whole."""
    tmp = f"{dest}.part"
    for attempt in range(3):
        with local.open("rb") as fh:
            p = subprocess.run([*_ssh(host, port), f"mkdir -p $(dirname {dest}) && cat > {tmp} && mv {tmp} {dest}"],
                               stdin=fh, timeout=3600)
        if p.returncode == 0 and _remote_size(host, port, dest) == local.stat().st_size:
            return
        time.sleep(5 * (attempt + 1))
    raise CloudError(f"no se pudo subir {local.name} a la máquina")


def download(host: str, port: int, src: str, local: Path) -> None:
    """Bring a file back through ssh, check its size, and only then put it in place."""
    part = local.with_name(local.name + ".part")
    expected = _remote_size(host, port, src)
    for attempt in range(3):
        with part.open("wb") as fh:
            p = subprocess.run([*_ssh(host, port), f"cat {src}"], stdout=fh, stdin=subprocess.DEVNULL, timeout=3600)
        if p.returncode == 0 and expected > 0 and part.stat().st_size == expected:
            part.replace(local)
            return
        time.sleep(5 * (attempt + 1))
    part.unlink(missing_ok=True)
    raise CloudError(f"no se pudo bajar {Path(src).name} de la máquina")


REMAP = '''import bpy, os, re
# Phone screens were linked with this computer's paths (maybe C:\\...): point them at the uploaded copies.
d = os.environ["REELS_DIR"]
for img in bpy.data.images:
    if img.source == "MOVIE":
        img.filepath = os.path.join(d, "screens", re.split(r"[\\\\/]", img.filepath)[-1])
'''


SETUP = (
    f"for i in $(seq 120); do [ -e {GUARD_DIR}/ready ] && break; sleep 2; done; "  # the guard's apt-get goes first
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


def _arm(host: str, port: int) -> str:
    """Make sure the guard is running (Vast's onstart should have started it) and return its state."""
    run(host, port, guard_script(), timeout=120)
    state = ""
    for _ in range(48):  # it may still be installing curl
        p = remote(host, port, f"cat {GUARD_DIR}/state 2> /dev/null", capture=True, timeout=60)
        state = _text(p).strip()
        if state:
            break
        time.sleep(5)
    if state == "armada":
        console.print(f"  seguro puesto: si esta computadora se apaga o pierde internet, la máquina se destruye sola "
                      f"en {IDLE_MIN} min (y siempre a las {int(LIFETIME_H)} h {round(LIFETIME_H % 1 * 60)} min de alquilarla)")
    else:
        console.print(f"[yellow]  ⚠ la máquina no ha podido ponerse el seguro ({state or 'sin respuesta'}): si esta "
                      "computadora se apaga a mitad, ejecuta `uv run reels cloud-cleanup` en cuanto vuelvas[/]")
    return state or "?"


def _prepare(c: httpx.Client, offer: dict, out: Path, blend: Path) -> tuple[int, str, int, Heartbeat]:
    """Rent, boot, arm the guard, install, upload and prove the GPU draws. Any failure (also Ctrl+C) destroys it."""
    iid = create(c, offer)
    beat = None
    try:
        _remember(iid, offer, out.name)
        host, port = wait_ready(c, iid)
        console.print(f"  máquina {iid} lista ({host}:{port})")
        run(host, port, "true", retries=6, timeout=60)  # sshd can take a moment
        beat = Heartbeat(host, port)
        beat.start()
        _arm(host, port)
        t0 = time.time()
        run(host, port, SETUP, timeout=1800)
        run(host, port, NVIDIA_GL, timeout=1800)
        console.print(f"[dim]  Blender instalado en {time.time() - t0:.0f}s[/]")
        remap = out / "renders" / "_remap.py"
        remap.parent.mkdir(parents=True, exist_ok=True)  # a fresh episode has no renders/ yet
        remap.write_text(REMAP, encoding="utf-8")
        size = blend.stat().st_size / 1e6
        console.print(f"[dim]  subiendo la escena ({size:.0f} MB)…[/]")
        for f in (blend, ROOT / "blender" / "render.py", remap):
            upload(host, port, f, f"/work/{f.name}")
        for f in sorted((out / "screens").glob("*.mp4")):
            upload(host, port, f, f"/work/screens/{f.name}")
        res = remote(host, port, PROBE, capture=True, timeout=600)
        line = (_text(res).strip().splitlines() or ["PROBE ? ? ?"])[-1]
        console.print(f"  fotograma de prueba: {line.replace('PROBE ', '')}")
        if "NVIDIA" not in line or "llvmpipe" in line.lower():
            raise CloudError("la GPU no dibuja en esta máquina (render por software)")
        return iid, host, port, beat
    except BaseException:  # also Ctrl+C or the terminal closing while preparing: never leave it running
        if beat:
            beat.stop()
        destroy(c, iid)
        raise


def _render_remote(host: str, port: int, quality: str, total: int) -> None:
    """Start Blender on the machine detached (a dropped connection does not kill it) and follow it from here."""
    start = (
        "cd /work && rm -f render.exit && setsid nohup bash -c \"REELS_DIR=/work timeout "
        f"{int(MAX_HOURS * 3600)} /opt/blender/blender --python-exit-code 1 -b scene.blend -P _remap.py -P render.py "
        f"-- /work/frames {quality} full > /tmp/render.log 2>&1; echo \\$? > /work/render.exit\" "
        "> /dev/null 2>&1 < /dev/null &"
    )
    run(host, port, start, retries=3, timeout=120)
    last_ok = shown = time.time()
    while True:
        time.sleep(POLL_S)
        p = remote(host, port, "cat /work/render.exit 2> /dev/null || echo -; ls /work/frames 2> /dev/null | wc -l",
                   capture=True, timeout=90)
        words = _text(p).split()
        if p.returncode != 0 or not words:
            if time.time() - last_ok > LOST_MIN * 60:
                raise CloudError(f"no hay conexión con la máquina desde hace {LOST_MIN} min (¿internet?)")
            continue
        last_ok = time.time()
        if words[0] != "-":
            if words[0] != "0":
                log = _text(remote(host, port, "tail -n 5 /tmp/render.log", capture=True, timeout=60))
                why = "se pasó del tiempo máximo" if words[0] == "124" else system.tail(log, 3)
                raise CloudError(f"Blender falló en la máquina: {why}")
            return
        if time.time() - shown > 120:
            done = int(words[1]) if len(words) > 1 and words[1].isdigit() else 0
            console.print(f"[dim]  render: {done} de {total or '?'} fotogramas[/]")
            shown = time.time()


def render(slug: str, quality: str = "final", max_price: float = MAX_PRICE, offer_id: int | None = None, fast: bool = False) -> Path:
    out = episode_dir(slug)
    tl = json.loads((out / "timeline.json").read_text(encoding="utf-8"))
    blend = out / "scene.blend"
    if not blend.exists():
        raise CloudError("no hay scene.blend: ejecuta antes `reels build`")
    try:  # before renting anything: without ssh the machine could not be used
        system.ssh_tool("ssh")
        system.ssh_tool("ssh-keygen")
    except RuntimeError as e:
        raise CloudError(str(e)) from None
    with _client() as c:
        # Machines of a render that died with its computer (and whose guard failed too): they are still billing.
        try:
            gone, _ = destroy_orphans(c)
        except (CloudError, httpx.HTTPError, ValueError, KeyError) as e:  # never a reason not to render
            gone = []
            console.print(f"[yellow]  no he podido revisar si quedan máquinas de otros renders ({str(e)[:80]})[/]")
        if gone:
            console.print(f"[yellow]  {len(gone)} máquina(s) de un render anterior seguían encendidas y cobrando: "
                          "destruidas[/]")
        ensure_ssh_key(c)
        KNOWN_HOSTS.write_text("", encoding="utf-8")
        # Cheap offers vanish in seconds, some hosts never boot, some lack GPU graphics:
        # walk down the ranking until one machine passes every check.
        iid = host = port = beat = chosen = None
        spent = 0.0
        t_try = time.time()
        console.print(f"[dim]  ofertas: primero las de la región «{home_region()}» (VAST_REGION en .env para cambiarla)[/]")
        for offer in find_offers(c, max_price, offer_id, fast)[:12]:
            console.print(f"  oferta {offer['id']}: {offer['gpu_name']} · {offer.get('geolocation', '?')} · ${offer['dph_total']:.3f}/h")
            t_try = time.time()
            time.sleep(2)
            try:
                iid, host, port, beat = _prepare(c, offer, out, blend)
                chosen = offer
                break
            except CloudError as e:
                spent += (time.time() - t_try) / 3600 * offer["dph_total"]
                console.print(f"[yellow]    descartada: {str(e)[:90]}[/]")
        if iid is None or chosen is None:
            raise CloudError("ninguna máquina pasó las comprobaciones")
        t_start = t_try  # Vast bills from creation: preparing the machine (Blender, upload) counts too
        try:
            t0 = time.time()
            _render_remote(host, port, quality, int(tl.get("total_frames") or 0))
            # EEVEE drops shadows silently when its pool overflows: say so instead of shipping it.
            warn = _text(remote(host, port, "grep -c 'Shadow buffer full' /tmp/render.log", capture=True, timeout=60)).strip()
            if warn not in ("", "0"):
                console.print(f"[yellow]  ⚠ faltan sombras en {warn} avisos de Blender (shadow_pool_size en build_scene.py)[/]")
            encode = (
                f"cd /work && ffmpeg -y -loglevel error -framerate {tl['fps']} -start_number 0 -i frames/%04d.png "
                f"-vf scale={tl['width']}:{tl['height']}:flags=lanczos -c:v libx264 -pix_fmt yuv420p -crf 16 scene.mp4"
            )
            run(host, port, encode, timeout=1800)
            console.print(f"[dim]  render remoto en {time.time() - t0:.0f}s[/]")
            video = out / "renders" / "scene.mp4"
            download(host, port, "/work/scene.mp4", video)
            return video
        finally:
            beat.stop()
            destroy(c, iid)
            hours = (time.time() - t_start) / 3600
            usd = spent + hours * chosen["dph_total"]
            cost.log(out, "render_cloud", usd, gpu=chosen["gpu_name"], minutes=round(hours * 60, 1))
            console.print(f"  coste aproximado: ${usd:.3f} ({hours * 60:.1f} min de máquina, preparación incluida)")
