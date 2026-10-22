"""Rehearsal of the Vast machine side with Docker (no Vast, no money): an Ubuntu 22.04 container with sshd plays the
rented machine, a local HTTP server plays the Vast API. It checks reels/cloud.py's machine side for real: the guard
starts from `onstart` (with sh), installs curl, arms itself with the instance key, the heartbeat keeps it alive
through a detached render, uploads/downloads arrive whole, and when the heartbeat stops it calls DELETE.

    cd plantilla && uv run python ../tools/ensayo_nube_docker.py      (needs Docker and internet for apt-get)

What it cannot prove: Vast's real API answer to the instance key, and ssh from Windows or Mac."""

import http.server
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from reels import cloud  # noqa: E402

API_PORT, SSH_PORT, NAME = 18765, 2222, "fabrica-ensayo-vast"
calls: list[tuple[str, str, str, str]] = []


class Api(http.server.BaseHTTPRequestHandler):
    def _any(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode() if n else ""
        calls.append((self.command, self.path, self.headers.get("Authorization", ""), body))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"success": true}')

    do_PUT = do_DELETE = do_GET = _any

    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(("0.0.0.0", API_PORT), Api)
threading.Thread(target=srv.serve_forever, daemon=True).start()

cloud.HEARTBEAT_S = 5
tmp = Path(tempfile.mkdtemp(prefix="ensayo-vast-"))
cloud.SSH_KEY = tmp / "Carpeta con espacios" / "reels_vast"
cloud.KNOWN_HOSTS = tmp / "Carpeta con espacios" / "kh"
cloud.SSH_KEY.parent.mkdir(parents=True)
subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(cloud.SSH_KEY)], check=True)
pub = cloud.SSH_KEY.with_suffix(".pub").read_text().strip()

onstart = cloud.guard_script(lifetime_s=3600, idle_s=25, tick_s=2).replace(
    "https://console.vast.ai/api/v0/instances/", f"http://host.docker.internal:{API_PORT}/api/v0/instances/")
(tmp / "onstart.sh").write_text(onstart)
boot = f"""set -e
export DEBIAN_FRONTEND=noninteractive
apt-get -qq update > /dev/null && apt-get -qq install -y openssh-server > /dev/null
mkdir -p /root/.ssh /run/sshd && echo '{pub}' > /root/.ssh/authorized_keys
# a fake Blender: writes frames and exits 0
mkdir -p /opt/blender && printf '#!/bin/bash\\nmkdir -p /work/frames; for i in 0 1 2; do touch /work/frames/000$i.png; sleep 1; done\\n' > /opt/blender/blender && chmod +x /opt/blender/blender
sh /onstart.sh
exec /usr/sbin/sshd -D
"""
(tmp / "boot.sh").write_text(boot)
subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
import base64
b64 = lambda t: base64.b64encode(t.encode()).decode()  # noqa: E731
subprocess.run(["docker", "run", "-d", "--name", NAME, "--add-host=host.docker.internal:host-gateway",
                "-e", "CONTAINER_API_KEY=clave-de-la-maquina", "-e", "CONTAINER_ID=4242", "-p", f"{SSH_PORT}:22",
                "-e", f"ONSTART={b64(onstart)}", "-e", f"BOOT={b64(boot)}", "ubuntu:22.04", "bash", "-c",
                'echo "$ONSTART" | base64 -d > /onstart.sh; echo "$BOOT" | base64 -d > /boot.sh; exec bash /boot.sh'],
               check=True, capture_output=True)
host, port = "127.0.0.1", SSH_PORT
try:
    cloud.run(host, port, "true", retries=30, timeout=30)
    print("ssh ok")
    beat = cloud.Heartbeat(host, port)
    beat.start()
    state = cloud._arm(host, port)
    print("estado del seguro:", state)
    assert state == "armada", state
    assert any(c[0] == "PUT" and c[1].endswith("/4242/") and "clave-de-la-maquina" in c[2] for c in calls), calls
    p = cloud.remote(host, port, "x='a \"b\" $c ñ'; echo \"$x\"; ls /root/reels-guard", capture=True)
    print("remote:", cloud._text(p).split())
    src = tmp / "escena.blend"
    src.write_bytes(b"\x00\r\n" * 200_000)
    cloud.upload(host, port, src, "/work/scene.blend")
    cloud._render_remote(host, port, "final", 3)
    print("render remoto acabado")
    cloud.run(host, port, "cp /work/scene.blend /work/scene.mp4")
    back = tmp / "vuelta.mp4"
    cloud.download(host, port, "/work/scene.mp4", back)
    assert back.read_bytes() == src.read_bytes()
    print("subida y bajada íntegras")
    # The computer «switches off»: no more heartbeats. The guard must call DELETE within ~25 s.
    beat.stop()
    t0 = time.time()
    while time.time() - t0 < 90 and not any(c[0] == "DELETE" for c in calls):
        time.sleep(2)
    dels = [c for c in calls if c[0] == "DELETE"]
    print(f"DELETE recibido a los {time.time() - t0:.0f} s:", dels[:1])
    assert dels and dels[0][1] == "/api/v0/instances/4242/" and "clave-de-la-maquina" in dels[0][2]
    print(cloud._text(cloud.remote(host, port, "cat /root/reels-guard/log", capture=True)))
    print("ENSAYO OK")
finally:
    subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    srv.shutdown()
