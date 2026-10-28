"""Live Resy availability for the concierge: capped, cached, honest.

Wraps the radar's Resy client (scraper/resy_find.py, scraper/resy_verify.py) for the
interactive path. It differs from the sweep on purpose:

- Hard cap of RESY_CALLS_PER_REQUEST (4) Resy HTTP calls per planner run, counted by
  the request's Budget (agent.context). Venue-id lookups count too; cache hits are free.
- A 10-minute cache per (venue, day, party), shared by every request in the process.
- One attempt per call and no 25 s retry sleep (the sweep can wait, a guest cannot).
  A 429 flips resy_find.RATE_LIMITED, after which every call in this process skips
  Resy until the flag is cleared: the ban cools off over hours (CLAUDE.md).
- Consecutive Resy calls are paced at least PACE_S apart.
- None means the lookup FAILED; [] means the venue genuinely has nothing open. The
  tool layer turns that into an explicit status so the planner can never read a
  failed lookup as "sold out".

Venue ids are seeded from scraper/.sniper_state.json (tracked in git, shipped in the
Modal image), so the demo venues never spend a budget call on id resolution.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

from .config import SCRAPER_DIR
from .context import Budget

CACHE_TTL_S = int(os.environ.get("T42_LIVE_CACHE_TTL", "600"))
PACE_S = float(os.environ.get("T42_RESY_PACE", "0.75"))
TIMEOUT_S = 15

_SLUG_RE = re.compile(r"resy\.com/cities/([^/]+)/venues/([^/?#]+)", re.I)
_START_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})")

_lock = threading.Lock()
_cache: dict[tuple[int, str, int], tuple[float, list[dict[str, Any]] | None]] = {}
_venue_ids: dict[str, int] = {}
_seeded = False
_last_call = 0.0


# ---- scraper access -----------------------------------------------------------

def _scraper():
    """(resy_find, resy_verify) imported lazily from scraper/, or (None, None)."""
    if str(SCRAPER_DIR) not in sys.path:
        sys.path.insert(0, str(SCRAPER_DIR))
    try:
        import resy_find  # type: ignore
        import resy_verify  # type: ignore
    except Exception:  # requests missing, scraper folder absent
        return None, None
    return resy_find, resy_verify


def rate_limited() -> bool:
    rf, _ = _scraper()
    return bool(rf and getattr(rf, "RATE_LIMITED", False))


def resy_ref(spot: dict[str, Any]) -> tuple[str, str] | None:
    """(location, slug) from the spot's Resy URL, or None for other platforms."""
    m = _SLUG_RE.search(spot.get("platformUrl") or "")
    return (m.group(1), m.group(2)) if m else None


def _seed_venue_ids() -> None:
    global _seeded
    if _seeded:
        return
    _seeded = True
    path = SCRAPER_DIR / ".sniper_state.json"
    try:
        venues = json.loads(path.read_text(encoding="utf-8")).get("venues") or {}
        for k, v in venues.items():
            if isinstance(v, int):
                _venue_ids.setdefault(k, v)
    except (OSError, ValueError):
        pass


def venue_id(spot: dict[str, Any], budget: Budget) -> tuple[int | None, str]:
    """(resy venue id, how). A cached id is free; a lookup spends one budget call."""
    ref = resy_ref(spot)
    if not ref:
        return None, "not a Resy venue"
    key = f"{ref[0]}/{ref[1]}"
    with _lock:
        _seed_venue_ids()
        vid = _venue_ids.get(key)
    if vid:
        return vid, "cached"
    if rate_limited():
        return None, "rate_limited"
    if not budget.take():
        return None, "budget"
    _, rv = _scraper()
    if rv is None:
        return None, "failed"
    _pace()
    info = rv.venue_info(ref[1], ref[0])
    vid = (info or {}).get("id")
    if not vid:
        return None, "failed"
    with _lock:
        _venue_ids[key] = int(vid)
    return int(vid), "looked up"


# ---- the Resy call ------------------------------------------------------------

def _pace() -> None:
    global _last_call
    with _lock:
        wait = PACE_S - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def parse_slots(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Slot rows from a /4/find payload, the same shape resy_find.slots returns."""
    out: list[dict[str, Any]] = []
    for v in (data.get("results") or {}).get("venues") or []:
        for sl in v.get("slots") or []:
            m = _START_RE.match(((sl.get("date") or {}).get("start")) or "")
            if not m:
                continue
            cfg = sl.get("config") or {}
            out.append({"date": m.group(1), "time": m.group(2),
                        "type": (cfg.get("type") or "").strip(), "token": cfg.get("token") or ""})
    return out


def _find(venue_id: int, day: str, party: int, lat: float, lng: float) -> list[dict[str, Any]] | None:
    """One GET /4/find. Mirrors resy_find.slots minus the 25 s retry; None = failed."""
    rf, rv = _scraper()
    if rf is None:
        return None
    try:
        import requests
    except ImportError:
        return None
    params = {"venue_id": venue_id, "day": day, "party_size": party, "lat": lat or 0, "long": lng or 0}
    _pace()
    try:
        r = requests.get(rf.FIND_URL, params=params, headers=rv._H, timeout=TIMEOUT_S)
    except Exception:
        return None
    if r.status_code == 429:
        rf.RATE_LIMITED = True
        return None
    if r.status_code != 200:
        return None
    try:
        return parse_slots(r.json())
    except ValueError:
        return None


# ---- public entry -------------------------------------------------------------

def slots_for(spot: dict[str, Any], day: str, party: int, budget: Budget) -> dict[str, Any]:
    """Live slots for one spot/day/party under the request budget.

    status: open | none | failed | budget | rate_limited | unsupported
    checked is True only for open/none (a real answer from Resy, fresh or cached).
    """
    now = datetime.now(timezone.utc).replace(microsecond=0)
    base: dict[str, Any] = {"slots": [], "cached": False, "checked_at": None, "venue_id": None}
    if not resy_ref(spot):
        plat = spot.get("platform") or "this platform"
        return dict(base, status="unsupported", checked=False,
                    note=f"Live checks run on Resy only; {plat} needs a browser session. Use the booking link.")
    vid, how = venue_id(spot, budget)
    if vid is None:
        status = how if how in ("budget", "rate_limited") else "failed"
        return dict(base, status=status, checked=False, note=_note(status))
    base["venue_id"] = vid
    key = (vid, day, int(party))
    with _lock:
        hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_S and hit[1] is not None:
        at = datetime.fromtimestamp(hit[0], timezone.utc).replace(microsecond=0)
        status = "open" if hit[1] else "none"
        return dict(base, status=status, checked=True, slots=list(hit[1]), cached=True,
                    checked_at=at.isoformat(), note=_note(status))
    if rate_limited():
        return dict(base, status="rate_limited", checked=False, note=_note("rate_limited"))
    if not budget.take():
        return dict(base, status="budget", checked=False, note=_note("budget"))
    coord = spot.get("coordinates") or {}
    res = _find(vid, day, int(party), coord.get("lat") or 0.0, coord.get("lng") or 0.0)
    if res is None:
        return dict(base, status="failed", checked=False, note=_note("failed"))
    with _lock:
        _cache[key] = (time.time(), res)
    status = "open" if res else "none"
    return dict(base, status=status, checked=True, slots=list(res), checked_at=now.isoformat(),
                note=_note(status))


def _note(status: str) -> str:
    return {
        "open": "Live from Resy: these times are open right now (they go fast).",
        "none": "Live from Resy: nothing open for this date and party size right now. Not a permanent no: "
                "cancellations and the next drop can change it.",
        "failed": "The live lookup FAILED (Resy did not answer). Availability is unknown, not empty. "
                  "Point to the booking link.",
        "budget": "Out of live checks for this request (hard cap per request). Availability is unknown, not empty.",
        "rate_limited": "Resy is rate-limiting us right now; live checks are paused for a while. "
                        "Availability is unknown, not empty.",
    }.get(status, "")


def clear_cache() -> None:
    with _lock:
        _cache.clear()
