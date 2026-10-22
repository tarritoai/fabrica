"""The cloud render (reels/cloud.py) without renting anything: the money safeguards (guard on the machine, orphans,
destroy on Ctrl+C), the choice of offers by region and the ssh plumbing that has to work on Windows, Mac and Linux."""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import timedelta

import httpx
import pytest

from reels import cloud, system

LINUX_BASH = sys.platform.startswith("linux") and shutil.which("bash")


def _client(handler) -> httpx.Client:
    return httpx.Client(base_url=cloud.API, transport=httpx.MockTransport(handler))


@pytest.fixture
def records(tmp_path, monkeypatch):
    monkeypatch.setattr(cloud, "RECORDS", tmp_path / "nube")
    monkeypatch.setattr(cloud.time, "sleep", lambda s: None)
    return tmp_path / "nube"


# --- the guard: the machine destroys itself -----------------------------------------------------------------------


def test_guard_fits_in_vast_onstart_and_is_valid_bash(tmp_path):
    script = cloud.guard_script()
    assert len(script) < 4000  # Vast's onstart limit is ~4048 characters
    assert "DELETE" in script and "CONTAINER_API_KEY" in script and "/api/v0/instances/" in script
    if shutil.which("bash"):
        f = tmp_path / "g.sh"
        f.write_text(script, encoding="utf-8")
        assert subprocess.run(["bash", "-n", str(f)]).returncode == 0
        f.write_text(script.split("<< 'REELS_GUARD'\n", 1)[1].split("REELS_GUARD\n", 1)[0], encoding="utf-8")
        assert subprocess.run(["bash", "-n", str(f)]).returncode == 0


def test_create_sends_the_guard_as_onstart():
    sent = {}

    def handler(req):
        sent.update(json.loads(req.content))
        return httpx.Response(200, json={"success": True, "new_contract": 77})

    with _client(handler) as c:
        assert cloud.create(c, {"id": 5}) == 77
    assert sent["onstart"] == cloud.guard_script() and sent["label"] == cloud.LABEL


def _run_guard(tmp_path, idle_s, life_s, curl_code="200"):
    """Run the guard for real (bash) with a fake curl that logs its calls; return the curl log once it destroys."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "curl.log"
    curl = bin_dir / "curl"
    curl.write_text(f'#!/bin/bash\necho "$@" >> {calls}\necho -n {curl_code}\n', encoding="utf-8")
    curl.chmod(0o755)
    where = tmp_path / "guard"
    script = cloud.guard_script(lifetime_s=life_s, idle_s=idle_s, tick_s=1, where=str(where))
    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "CONTAINER_API_KEY": "instancekey",
           "CONTAINER_ID": "4242"}
    assert subprocess.run(["bash", "-c", script], env=env, timeout=30).returncode == 0
    return where, calls


@pytest.mark.skipif(not LINUX_BASH, reason="the guard runs on the rented Linux machine (GNU stat)")
def test_guard_destroys_the_machine_when_this_computer_goes_silent(tmp_path):
    where, calls = _run_guard(tmp_path, idle_s=2, life_s=3600)
    for _ in range(60):
        if "autodestruccion" in (where / "log").read_text(encoding="utf-8") if (where / "log").exists() else False:
            break
        time.sleep(0.25)
    time.sleep(0.5)
    log = (where / "log").read_text(encoding="utf-8")
    assert (where / "state").read_text(encoding="utf-8").strip() == "armada"
    assert "sin noticias de la computadora" in log and "destruir: 200" in log
    lines = calls.read_text(encoding="utf-8").splitlines()
    assert "PUT" in lines[0] and '"state":"running"' in lines[0]  # the harmless key check
    assert any("-X DELETE" in ln and "/api/v0/instances/4242/" in ln and "Bearer instancekey" in ln for ln in lines)


@pytest.mark.skipif(not LINUX_BASH, reason="the guard runs on the rented Linux machine (GNU stat)")
def test_guard_respects_the_heartbeat_and_then_the_lifetime(tmp_path):
    where, calls = _run_guard(tmp_path, idle_s=3, life_s=6)
    t0 = time.time()
    while time.time() - t0 < 5:  # this computer keeps saying «still here»: no destroy yet
        (where / "alive").touch()
        assert "autodestruccion" not in ((where / "log").read_text(encoding="utf-8") if (where / "log").exists() else "")
        time.sleep(0.5)
    for _ in range(40):
        (where / "alive").touch()
        if "tiempo maximo" in (where / "log").read_text(encoding="utf-8"):
            break
        time.sleep(0.25)
    assert "tiempo maximo" in (where / "log").read_text(encoding="utf-8")


@pytest.mark.skipif(not LINUX_BASH, reason="the guard runs on the rented Linux machine")
def test_starting_the_guard_twice_keeps_one(tmp_path):
    where, _ = _run_guard(tmp_path, idle_s=60, life_s=60)
    time.sleep(0.5)
    pid = (where / "pid").read_text(encoding="utf-8").strip()
    script = cloud.guard_script(lifetime_s=60, idle_s=60, tick_s=1, where=str(where))
    subprocess.run(["bash", "-c", script], timeout=30, check=True)
    time.sleep(0.3)
    assert (where / "pid").read_text(encoding="utf-8").strip() == pid
    subprocess.run(["kill", pid])


# --- destroy, orphans --------------------------------------------------------------------------------------------


def test_destroy_checks_the_answer(records):
    with _client(lambda req: httpx.Response(500, text="boom")) as c:
        assert cloud.destroy(c, 1) is False
    with _client(lambda req: httpx.Response(404, text="gone")) as c:
        assert cloud.destroy(c, 1) is True  # already gone is fine
    with _client(lambda req: httpx.Response(200, json={"success": False})) as c:
        assert cloud.destroy(c, 1) is False


def test_orphans_are_the_machines_no_live_render_uses(records):
    cloud._remember(1, {"gpu_name": "RTX 3080", "dph_total": 0.12}, "a")  # this process: in use
    records.joinpath("2.json").write_text(json.dumps({"id": 2, "pid": 999_999_999}), encoding="utf-8")  # dead
    records.joinpath("9.json").write_text(json.dumps({"id": 9, "pid": 999_999_999}), encoding="utf-8")  # gone in Vast
    deleted = []

    def handler(req):
        if req.method == "GET":
            return httpx.Response(200, json={"instances": [
                {"id": 1, "label": "reels-render"}, {"id": 2, "label": "reels-render"},
                {"id": 3, "label": "reels-render", "dph_total": 0.2}, {"id": 4, "label": "otra-cosa"}]})
        deleted.append(int(req.url.path.rstrip("/").rsplit("/", 1)[1]))
        return httpx.Response(200, json={"success": True})

    with _client(handler) as c:
        lost, busy = cloud.orphans(c)
        assert sorted(m["id"] for m in lost) == [2, 3] and [m["id"] for m in busy] == [1]
        assert not records.joinpath("9.json").exists()
        done, busy = cloud.destroy_orphans(c)
    assert sorted(deleted) == [2, 3] and [m["id"] for m in busy] == [1]  # never the machine of a live render
    assert records.joinpath("1.json").exists() and not records.joinpath("2.json").exists()


def test_ctrl_c_while_preparing_destroys_the_machine(records, monkeypatch, tmp_path):
    destroyed = []
    monkeypatch.setattr(cloud, "create", lambda c, offer: 31)
    monkeypatch.setattr(cloud, "destroy", lambda c, iid: destroyed.append(iid) or True)

    def interrupted(c, iid):
        raise KeyboardInterrupt

    monkeypatch.setattr(cloud, "wait_ready", interrupted)
    with pytest.raises(KeyboardInterrupt):
        cloud._prepare(None, {"id": 1}, tmp_path, tmp_path / "scene.blend")
    assert destroyed == [31]


# --- offers: near the student first ------------------------------------------------------------------------------


def _offer(i, where, price, flops=100.0):
    return {"id": i, "geolocation": where, "dph_total": price, "total_flops": flops}


def test_offers_prefer_the_students_region_unless_far_is_much_better():
    offers = [_offer(1, "Texas, US", 0.20), _offer(2, "Spain, ES", 0.24), _offer(3, "Brazil, BR", 0.25),
              _offer(4, "Quebec, CA", 0.10)]
    assert [o["id"] for o in cloud.rank_offers(offers, "europa")] == [4, 2, 1, 3]  # 0.10 far still wins
    assert [o["id"] for o in cloud.rank_offers(offers, "america")] == [4, 1, 3, 2]
    assert [o["id"] for o in cloud.rank_offers(offers, "cualquiera")] == [4, 1, 2, 3]
    close = [_offer(1, "Texas, US", 0.20), _offer(2, "Spain, ES", 0.24)]
    assert cloud.rank_offers(close, "europa")[0]["id"] == 2  # 20 % dearer but near: near first


@pytest.mark.parametrize("hours,region", [(1, "europa"), (2, "europa"), (0, "europa"), (-3, "america"),
                                          (-6, "america"), (-5, "america"), (9, "cualquiera")])
def test_region_from_time_zone(monkeypatch, hours, region):
    class FakeNow:
        @staticmethod
        def now():
            class D:
                def astimezone(self):
                    class T:
                        def utcoffset(self):
                            return timedelta(hours=hours)
                    return T()
            return D()

    monkeypatch.delenv("VAST_REGION", raising=False)
    monkeypatch.setattr(cloud, "datetime", FakeNow)
    assert cloud.home_region() == region
    monkeypatch.setenv("VAST_REGION", "América")
    assert cloud.home_region() == "america"


# --- ssh plumbing --------------------------------------------------------------------------------------------------


def test_ssh_options_survive_spaces_and_never_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr(cloud, "KNOWN_HOSTS", tmp_path / "María José" / "kh")
    opts = cloud._ssh_opts()
    kh = next(o for o in opts if o.startswith("UserKnownHostsFile="))
    assert kh == f'UserKnownHostsFile="{(tmp_path / "María José" / "kh").as_posix()}"' and "\\" not in kh
    assert "BatchMode=yes" in opts and "ServerAliveInterval=30" in opts
    assert not any(o.endswith("/dev/null") or o.lower().endswith("=nul") for o in opts)


@pytest.fixture
def fake_ssh(monkeypatch):
    """`ssh host cmd` → `bash -c cmd` on this computer (the remote side is plain bash on Linux)."""
    if not LINUX_BASH:
        pytest.skip("needs bash and GNU stat")
    monkeypatch.setattr(cloud, "_ssh", lambda host, port: ["bash", "-c"])
    monkeypatch.setattr(cloud.time, "sleep", lambda s: None)


def test_remote_scripts_travel_by_stdin(fake_ssh):
    script = "x='comillas \"dobles\" y $dólar'\necho \"$x\"\nexit 3\n"
    p = cloud.remote("h", 22, script, capture=True)
    assert p.returncode == 3 and cloud._text(p).strip() == 'comillas "dobles" y $dólar'


def test_upload_and_download_check_sizes(fake_ssh, tmp_path):
    src = tmp_path / "escena con espacios.blend"
    src.write_bytes(os.urandom(300_000) + b"\r\n\x00")
    dest = tmp_path / "remote" / "scene.blend"
    cloud.upload("h", 22, src, str(dest))
    assert dest.read_bytes() == src.read_bytes()
    back = tmp_path / "back.mp4"
    cloud.download("h", 22, str(dest), back)
    assert back.read_bytes() == src.read_bytes() and not back.with_name("back.mp4.part").exists()
    with pytest.raises(cloud.CloudError):
        cloud.download("h", 22, str(tmp_path / "no-existe"), tmp_path / "x.mp4")


def test_heartbeat_touches_the_guard_file(fake_ssh, monkeypatch, tmp_path):
    monkeypatch.setattr(cloud, "GUARD_DIR", str(tmp_path))
    beat = cloud.Heartbeat("h", 22)
    beat.start()
    beat.stop()  # it still beats once (right away) before looking at stop
    beat.join(10)
    assert (tmp_path / "alive").exists()


# --- system helpers used by the cloud ------------------------------------------------------------------------------


def test_pid_alive():
    assert system.pid_alive(os.getpid())
    assert not system.pid_alive(999_999_999)
    assert not system.pid_alive(0)


@pytest.mark.skipif(sys.platform.startswith("win"), reason="SIGTERM to oneself is POSIX")
def test_sigterm_runs_finally():
    import signal

    ran = []
    with pytest.raises(SystemExit):
        with system.exit_cleanly_on_terminate():
            try:
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(1)
            finally:
                ran.append("destroy")
    assert ran == ["destroy"]


def test_windows_finds_ssh_of_git_or_openssh(monkeypatch, tmp_path):
    monkeypatch.setattr(system, "current_os", lambda: "windows")
    monkeypatch.setattr(system, "find_tool", lambda name, env=None: None)
    monkeypatch.delenv("SSH_BIN", raising=False)
    monkeypatch.setenv("SystemRoot", str(tmp_path / "Windows"))
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "PF"))
    monkeypatch.setenv("ProgramW6432", str(tmp_path / "PF"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "LA"))
    assert system.find_ssh_tool("ssh") is None
    git = tmp_path / "LA" / "Programs" / "Git" / "usr" / "bin"
    git.mkdir(parents=True)
    (git / "ssh.exe").write_bytes(b"")
    assert system.find_ssh_tool("ssh") == str(git / "ssh.exe")
    openssh = tmp_path / "Windows" / "System32" / "OpenSSH"
    openssh.mkdir(parents=True)
    (openssh / "ssh.exe").write_bytes(b"")
    assert system.find_ssh_tool("ssh") == str(openssh / "ssh.exe")  # Windows' own client first


def test_cloud_cleanup_is_pre_approved():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    allow = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]
    assert "Bash(uv run reels cloud-cleanup:*)" in allow  # it only destroys machines nobody uses: it saves money
