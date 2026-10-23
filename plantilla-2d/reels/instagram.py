"""Instagram metrics for our own reels (Instagram API with Instagram Login, read-only).

Snapshots go to metrics/instagram.jsonl (versioned: small, and the history is the point).
The long-lived token comes from IG_ACCESS_TOKEN in .env; refreshed copies live in .cache/ig_token.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import unicodedata
from datetime import datetime, timezone

import httpx

from reels.assets import PUBLISH, ROOT, published
from reels import system

API = "https://graph.instagram.com/v25.0"
TOKEN_CACHE = ROOT / ".cache/ig_token.json"
SNAPSHOTS = ROOT / "metrics/instagram.jsonl"
ACCOUNT = ROOT / "metrics/account.jsonl"  # followers over time (the API has no per-reel follows for reels)
REFRESH_AFTER_DAYS = 7  # tokens last 60 days; refreshing weekly keeps a wide margin
# Reels insights. Some are marked "in development" by Meta: a metric the API rejects is dropped and retried.
METRICS = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
           "ig_reels_avg_watch_time", "reels_skip_rate"]


class InstagramError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token() -> str:
    """The newest token we have, refreshed if it is more than a week old (needs >24 h of age, Meta's rule)."""
    env = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    cached = json.loads(TOKEN_CACHE.read_text(encoding="utf-8")) if TOKEN_CACHE.exists() else {}
    # A new token pasted into .env wins over an older refreshed copy.
    if env and env != cached.get("source"):
        cached = {"token": env, "source": env, "since": _now().isoformat()}
        _save_token(cached)
    token = cached.get("token")
    if not token:
        raise InstagramError("falta IG_ACCESS_TOKEN en .env (Meta for Developers → tu app → Generar token)")
    age = (_now() - datetime.fromisoformat(cached["since"])).total_seconds() / 86400
    if age >= REFRESH_AFTER_DAYS:
        r = httpx.get(f"{API.rsplit('/', 1)[0]}/refresh_access_token",
                      params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
        if r.status_code == 200:
            cached.update(token=r.json()["access_token"], since=_now().isoformat())
            _save_token(cached)
            token = cached["token"]
    return token


def _save_token(data: dict) -> None:
    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(data), encoding="utf-8")
    TOKEN_CACHE.chmod(0o600)


def _get(client: httpx.Client, path: str, **params) -> dict:
    r = client.get(f"{API}/{path}", params=params)
    data = r.json()
    if r.status_code != 200 or "error" in data:
        msg = data.get("error", {}).get("message", r.text[:200])
        raise InstagramError(f"{path}: HTTP {r.status_code}: {msg}")
    return data


def account(client: httpx.Client) -> dict:
    return _get(client, "me", fields="user_id,username,account_type,followers_count")


def _reels(client: httpx.Client, ig_id: str) -> list[dict]:
    out, after = [], None
    while True:
        params = {"fields": "id,caption,media_product_type,timestamp,permalink,is_shared_to_feed", "limit": 50}
        if after:
            params["after"] = after
        page = _get(client, f"{ig_id}/media", **params)
        out += [m for m in page.get("data", []) if m.get("media_product_type") == "REELS"]
        after = page.get("paging", {}).get("cursors", {}).get("after") if page.get("paging", {}).get("next") else None
        if not after:
            return out


def _insights(client: httpx.Client, media_id: str) -> dict:
    metrics = list(METRICS)
    while metrics:
        try:
            data = _get(client, f"{media_id}/insights", metric=",".join(metrics))
        except InstagramError as e:
            bad = next((m for m in metrics if m in str(e)), None)
            if not bad:
                raise
            metrics.remove(bad)
            continue
        return {d["name"]: d["values"][0]["value"] for d in data.get("data", []) if d.get("values")}
    return {}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if c.isalnum())


def _slug_for(caption: str) -> str | None:
    """Match a post to its episode by the first line of publicar/<episode>/<slug>.txt (that is what gets pasted)."""
    cap = _norm(caption or "")[:60]
    for txt in PUBLISH.glob("*/*.txt"):
        first = _norm(txt.read_text(encoding="utf-8").strip().splitlines()[0])[:60]
        if first and (first in cap or cap.startswith(first[:30])):
            return txt.stem
    return None


def _slug_of(m: dict) -> str | None:
    """A trial reel (not shared to the feed) is the B hook: <slug>-b, even if A's caption was pasted on it."""
    slug = _slug_for(m.get("caption", ""))
    if slug and not slug.endswith("-b") and m.get("is_shared_to_feed") is False \
            and (PUBLISH / slug / f"{slug}-b.mp4").exists():
        return f"{slug}-b"
    return slug


def _duration(slug: str | None) -> float | None:
    video = published(slug, ".mp4") if slug else None
    if not video or not video.exists():
        return None
    out = subprocess.run([system.ffprobe(), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return float(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None


def snapshot() -> list[dict]:
    """Fetch every reel's metrics now, append them to metrics/instagram.jsonl and return them."""
    with httpx.Client(timeout=30, params={"access_token": _token()}) as client:
        me = account(client)
        rows = []
        now = _now()
        for m in _reels(client, me["user_id"]):
            posted = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
            slug = _slug_of(m)
            rows.append({
                "fetched_at": now.isoformat(timespec="seconds"),
                "media_id": m["id"],
                "slug": slug,
                "posted_at": posted.isoformat(),
                "age_h": round((now - posted).total_seconds() / 3600, 1),
                "permalink": m.get("permalink"),
                "duration_s": _duration(slug),
                "metrics": _insights(client, m["id"]),
            })
    SNAPSHOTS.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOTS.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with ACCOUNT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"fetched_at": now.isoformat(timespec="seconds"),
                            "followers": me.get("followers_count")}) + "\n")
    return rows


def followers() -> list[dict]:
    """Follower snapshots, oldest first."""
    return [json.loads(line) for line in ACCOUNT.read_text(encoding="utf-8").splitlines()] if ACCOUNT.exists() else []


COMMENTS = ROOT / "metrics/comments.jsonl"  # git-ignored: other people's words stay on this computer


def comments() -> tuple[int, int]:
    """Fetch every reel's comments into metrics/comments.jsonl (deduplicated by id). Returns (new, total)."""
    seen = set()
    if COMMENTS.exists():
        seen = {json.loads(line)["id"] for line in COMMENTS.read_text(encoding="utf-8").splitlines()}
    new_rows, expected = [], 0
    with httpx.Client(timeout=30, params={"access_token": _token()}) as client:
        me = account(client)
        for m in _reels(client, me["user_id"]):
            slug = _slug_of(m)
            expected += _insights(client, m["id"]).get("comments") or 0
            after = None
            while True:
                params = {"fields": "id,text,timestamp,like_count", "limit": 50}
                if after:
                    params["after"] = after
                page = _get(client, f"{m['id']}/comments", **params)
                for c in page.get("data", []):
                    if c["id"] not in seen:
                        seen.add(c["id"])
                        new_rows.append({"id": c["id"], "media_id": m["id"], "slug": slug, "timestamp": c.get("timestamp"),
                                         "likes": c.get("like_count", 0), "text": c.get("text", "")})
                paging = page.get("paging", {})
                after = paging.get("cursors", {}).get("after") if paging.get("next") else None
                if not after:
                    break
    if not seen and expected:
        # Meta answers 200 with an empty list when the token lacks the comments scope.
        raise InstagramError(
            f"Instagram dice que hay {expected} comentarios pero no deja leerlos: el token no tiene el permiso "
            "instagram_business_manage_comments. Meta for Developers → tu app → Instagram → añade ese permiso, "
            "genera un token nuevo y pégalo en .env (IG_ACCESS_TOKEN)")
    COMMENTS.parent.mkdir(parents=True, exist_ok=True)
    with COMMENTS.open("a", encoding="utf-8") as f:
        for r in new_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(new_rows), len(seen)
