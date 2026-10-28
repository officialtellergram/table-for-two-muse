"""Watch storage for create_watch: the guest's Supabase watchlist, or a local file.

Signed-in guest (the panel forwards their Supabase access token): one row is
inserted into public.watchlists through PostgREST with the anon key plus the
guest's JWT, so Row Level Security applies exactly as it does for web/auth.js.
The radar's ingest function then emails them when a matching table opens.

No token, or the insert fails: the watch is appended to a local JSON file
(agent/.watches.json, git-ignored) and the result says so plainly. A local
watch does not alert anyone; it is the honest fallback SPEC section 3 asks for.

Supabase URL and anon key: SUPABASE_URL / SUPABASE_ANON_KEY in the environment
(Modal secret), else parsed from web/config.js, which holds the same public-safe
values the site ships. The service role key is never used here.
"""
from __future__ import annotations

import base64
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import ROOT

_lock = threading.Lock()
_JS_RE = {
    "url": re.compile(r'SUPABASE_URL\s*=\s*"([^"]+)"'),
    "key": re.compile(r'SUPABASE_ANON_KEY\s*=\s*"([^"]+)"'),
}


def local_path() -> Path:
    return Path(os.environ.get("T42_WATCHES_PATH") or (ROOT / "agent" / ".watches.json"))


def supabase_config() -> tuple[str | None, str | None]:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_ANON_KEY")
    if url and key:
        return url.rstrip("/"), key
    cfg = ROOT / "web" / "config.js"
    try:
        text = cfg.read_text(encoding="utf-8")
    except OSError:
        return None, None
    mu, mk = _JS_RE["url"].search(text), _JS_RE["key"].search(text)
    return (mu.group(1).rstrip("/") if mu else None), (mk.group(1) if mk else None)


def user_id_from_token(token: str | None) -> str | None:
    """The `sub` claim of a Supabase JWT, read without verifying (Supabase verifies)."""
    if not token or token.count(".") != 2:
        return None
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload)).get("sub")
    except (ValueError, UnicodeDecodeError):
        return None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def save_supabase(row: dict[str, Any], token: str) -> dict[str, Any]:
    """Insert into public.watchlists as the guest. Raises on any failure."""
    url, anon = supabase_config()
    if not (url and anon):
        raise RuntimeError("Supabase is not configured on the concierge")
    uid = user_id_from_token(token)
    if not uid:
        raise RuntimeError("the guest token is not a Supabase session token")
    import requests
    r = requests.post(f"{url}/rest/v1/watchlists", json=dict(row, user_id=uid), timeout=15,
                      headers={"apikey": anon, "Authorization": f"Bearer {token}",
                               "Content-Type": "application/json", "Prefer": "return=representation"})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Supabase answered {r.status_code}: {r.text[:200]}")
    data = r.json()
    return data[0] if isinstance(data, list) and data else data


def save_local(row: dict[str, Any]) -> dict[str, Any]:
    path = local_path()
    rec = dict(row, id=str(uuid.uuid4()), created_at=_now(), active=True)
    with _lock:
        try:
            rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        except ValueError:
            rows = []
        rows.append(rec)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    return rec


def list_local() -> list[dict[str, Any]]:
    path = local_path()
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except ValueError:
        return []


def save(row: dict[str, Any], token: str | None) -> tuple[dict[str, Any], str, str | None]:
    """(stored row, where, problem). where is 'supabase' or 'local'."""
    if token:
        try:
            return save_supabase(row, token), "supabase", None
        except Exception as e:  # noqa: BLE001 - any failure falls back, and is reported
            problem = str(e)
            return save_local(row), "local", problem
    return save_local(row), "local", None
