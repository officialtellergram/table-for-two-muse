"""booking_link tool: a pre-filled platform URL for a date and party size.

Backed by scraper/sniper.booking_url for Resy (its date/seats params are what the
radar already uses). Other platforms get the per-platform parameters the web app
uses in prefillUrl()/partyParam() in index.html; EU widgets and plain websites are
returned untouched, because spraying ?date= on an arbitrary page breaks trust.
"""
from __future__ import annotations

import sys
from datetime import date
from typing import Any
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

from .. import data
from ..config import SCRAPER_DIR

_sniper = None


def _sniper_booking_url():
    """Import scraper/sniper.py lazily (it pulls in the Resy client modules)."""
    global _sniper
    if _sniper is None:
        if str(SCRAPER_DIR) not in sys.path:
            sys.path.insert(0, str(SCRAPER_DIR))
        try:
            import sniper  # type: ignore
            _sniper = sniper
        except Exception:  # pragma: no cover - requests missing etc.
            _sniper = False
    return getattr(_sniper, "booking_url", None) if _sniper else None


def _with_params(url: str, **params: str) -> str:
    u = urlparse(url)
    q = dict(parse_qsl(u.query, keep_blank_values=True))
    q.update(params)
    return urlunparse(u._replace(query=urlencode(q)))


def prefill(spot: dict[str, Any], day: str, party: int) -> tuple[str, str]:
    """(url, how) for the spot's platform."""
    base = spot.get("platformUrl") or ""
    if not base:
        return "", "no platform URL on file"
    host = urlparse(base).hostname or ""
    n = str(int(party))
    if "resy.com" in host:
        fn = _sniper_booking_url()
        if fn:
            return fn(spot, day, n), "resy via scraper/sniper.booking_url"
        return _with_params(base, date=day, seats=n), "resy"
    if "opentable.com" in host:
        return _with_params(base, dateTime=f"{day}T19:00", covers=n), "opentable"
    if "exploretock.com" in host:
        return _with_params(base, date=day, size=n), "tock"
    if "sevenrooms.com" in host:
        return _with_params(base, date=day, party_size=n), "sevenrooms"
    return base, "platform does not take date/party in the URL; link left untouched"


def booking_link(city: str, spot_id: str, date: str, party: int) -> dict[str, Any]:
    c = data.resolve_city(city)
    s = data.spot(c["key"], spot_id)
    try:
        day = _date_iso(date)
    except ValueError as e:
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}") from e
    url, how = prefill(s, day, int(party))
    return {
        "spot_id": s.get("id"),
        "name": s.get("name"),
        "platform": s.get("platform"),
        "date": day,
        "party": int(party),
        "url": url,
        "how": how,
        "walk_ins": s.get("walkIns"),
        "phone": s.get("phoneNumber") or None,
        "website": s.get("website") or None,
    }


def _date_iso(text: str) -> str:
    from datetime import date as _d
    return _d.fromisoformat(str(text).strip()[:10]).isoformat()
