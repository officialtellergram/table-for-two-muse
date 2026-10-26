"""search_spots and get_spot over cities/<city>.json."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from .. import data

_COMPACT_FIELDS = (
    "id", "name", "neighborhood", "cuisine", "difficulty", "priceRange", "platform",
    "releaseSchedule", "releaseTime", "releaseDay", "bookingWindowDays", "walkIns",
    "vibe", "occasion", "signatureDish", "lastVerified", "dateNote",
)
_DROP_FIELDS = {"photoAttr", "photoChecked", "sources", "coordinates", "walkIn"}


def _norm(s: Any) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower()).strip()


def _tokens(s: Any) -> set[str]:
    return {t for t in _norm(s).split() if len(t) > 1}


def _availability_summary(av: dict[str, Any] | None) -> dict[str, Any] | None:
    if not av:
        return None
    return {
        "open": bool(av.get("open")),
        "checkedAt": av.get("checkedAt"),
        "partySize": av.get("partySize"),
        "windowDays": av.get("windowDays"),
        "openDays": av.get("openDays"),
        "dates": (av.get("dates") or [])[:5],
    }


def compact(s: dict[str, Any]) -> dict[str, Any]:
    out = {k: s.get(k) for k in _COMPACT_FIELDS if k in s}
    out["availability"] = _availability_summary(s.get("availability"))
    return out


def _score(s: dict[str, Any], query: str) -> float:
    """0..1 relevance of a spot to a free-text query; name matches dominate."""
    q = _norm(query)
    if not q:
        return 0.0
    name = _norm(s.get("name"))
    best = SequenceMatcher(None, q, name).ratio()
    if q == name:
        best = 1.0
    elif q in name or name in q:
        best = max(best, 0.9)
    qt = _tokens(query)
    hay = _tokens(name) | _tokens(s.get("cuisine")) | _tokens(s.get("neighborhood")) | _tokens(s.get("signatureDish"))
    if qt and hay:
        best = max(best, 0.6 * len(qt & hay) / len(qt))
    return best


def search_spots(city: str, query: str | None = None, neighborhood: str | None = None,
                 cuisine: str | None = None, vibe: str | None = None, occasion: str | None = None,
                 party: int | None = None, max_difficulty: int | None = None,
                 limit: int = 8) -> dict[str, Any]:
    c = data.resolve_city(city)
    rows = data.spots(c["key"])
    nb, cu = _norm(neighborhood), _norm(cuisine)
    vb, oc = _norm(vibe), _norm(occasion)
    picked: list[tuple[float, dict[str, Any]]] = []
    for s in rows:
        if nb and nb not in _norm(s.get("neighborhood")):
            continue
        if cu and cu not in _norm(s.get("cuisine")):
            continue
        if vb and vb not in {_norm(v) for v in (s.get("vibe") or [])}:
            continue
        if oc and oc not in {_norm(v) for v in (s.get("occasion") or [])}:
            continue
        if max_difficulty is not None and int(s.get("difficulty") or 0) > int(max_difficulty):
            continue
        sc = _score(s, query) if query else 0.0
        if query and sc < 0.35:
            continue
        picked.append((sc, s))
    # Relevance first; without a query, hardest tables first (that's what the site leads with).
    picked.sort(key=lambda t: (-t[0], -int(t[1].get("difficulty") or 0), _norm(t[1].get("name"))))
    lim = max(1, min(int(limit or 8), 20))
    return {
        "city": c["key"],
        "city_label": c.get("label"),
        "timezone": c.get("timezone"),
        "party": party,
        "matched": len(picked),
        "spots": [dict(compact(s), match=round(sc, 2)) if query else compact(s) for sc, s in picked[:lim]],
    }


def get_spot(city: str, spot_id: str) -> dict[str, Any]:
    c = data.resolve_city(city)
    s = data.spot(c["key"], spot_id)
    out = {k: v for k, v in s.items() if k not in _DROP_FIELDS}
    out["city"] = c["key"]
    out["timezone"] = c.get("timezone")
    return out
