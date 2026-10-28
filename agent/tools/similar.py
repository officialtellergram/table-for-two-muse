"""similar_spots tool: up to three alternates to a spot, each live-checked.

Heuristic ranking over the curated data (vibe, occasion, cuisine, neighborhood,
difficulty, price, walk-ins), never more than three results, and each alternate
goes through check_live_availability on the same request budget (SPEC section 3).
The optional open-weights re-rank (Glimmer on Modal, phase 3) plugs in here.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Any

from .. import data
from .. import drops as engine
from ..context import RequestContext
from .live import check_live_availability
from .spots import _norm, compact

MAX_N = 3


def _overlap(a: list[str] | None, b: list[str] | None) -> list[str]:
    sa = {_norm(x) for x in (a or [])}
    return [x for x in (b or []) if _norm(x) in sa]


def score(anchor: dict[str, Any], s: dict[str, Any]) -> tuple[float, list[str]]:
    """(score, reasons) for s as an alternate to anchor. Higher is more similar and easier."""
    pts, why = 0.0, []
    v = _overlap(anchor.get("vibe"), s.get("vibe"))
    if v:
        pts += 2.0 * len(v)
        why.append("vibe: " + ", ".join(v))
    o = _overlap(anchor.get("occasion"), s.get("occasion"))
    if o:
        pts += 1.0 * len(o)
        why.append("occasion: " + ", ".join(o))
    ac, sc = _norm(anchor.get("cuisine")), _norm(s.get("cuisine"))
    if ac and sc and (ac in sc or sc in ac):
        pts += 3.0
        why.append(f"same cuisine ({s.get('cuisine')})")
    if _norm(anchor.get("neighborhood")) and _norm(anchor.get("neighborhood")) == _norm(s.get("neighborhood")):
        pts += 2.0
        why.append(f"same neighborhood ({s.get('neighborhood')})")
    ad, sd = int(anchor.get("difficulty") or 0), int(s.get("difficulty") or 0)
    if sd and ad:
        if sd < ad:
            pts += 1.0 + 0.5 * (ad - sd)
            why.append(f"easier to book ({sd}/5 vs {ad}/5)")
        elif sd == ad:
            pts += 0.5
        else:
            pts -= 1.0 * (sd - ad)
    if anchor.get("priceRange") and anchor.get("priceRange") == s.get("priceRange"):
        pts += 1.0
        why.append(f"same price ({s.get('priceRange')})")
    if s.get("walkIns"):
        pts += 0.75
        why.append("takes walk-ins")
    av = s.get("availability") or {}
    if av.get("open"):
        pts += 0.5
    return pts, why


def similar_spots(city: str, spot_id: str, party: int = 2, date: str | None = None, n: int = MAX_N,
                  time_from: str | None = None, time_to: str | None = None, live_check: bool = True,
                  _ctx: RequestContext | None = None) -> dict[str, Any]:
    c = data.resolve_city(city)
    anchor = data.spot(c["key"], spot_id)
    day = None
    if date:
        try:
            day = _date.fromisoformat(str(date).strip()[:10]).isoformat()
        except ValueError as e:
            raise ValueError(f"date must be YYYY-MM-DD, got {date!r}") from e
    n = max(1, min(int(n or MAX_N), MAX_N))
    party = max(1, min(int(party or 2), 20))
    ctx = _ctx if _ctx is not None else RequestContext()

    ranked: list[tuple[float, list[str], dict[str, Any]]] = []
    for s in data.spots(c["key"]):
        if s.get("id") == anchor.get("id"):
            continue
        pts, why = score(anchor, s)
        if pts <= 0:
            continue
        ranked.append((pts, why, s))
    ranked.sort(key=lambda t: (-t[0], int(t[2].get("difficulty") or 0), _norm(t[2].get("name"))))

    tz = c.get("timezone") or "America/New_York"
    out = []
    for pts, why, s in ranked[:n]:
        row: dict[str, Any] = dict(compact(s), score=round(pts, 2), why=why)
        if day:
            d = engine.describe(s, tz, _date.fromisoformat(day))
            row["drop"] = {"schedule": d.get("schedule"), "next_drop": d.get("next_drop"),
                           "drop_for_target": d.get("drop_for_target"), "note": d.get("note")}
            if live_check:
                live = check_live_availability(c["key"], s["id"], day, party, time_from, time_to, _ctx=ctx)
                row["live"] = {k: live[k] for k in ("status", "checked", "cached", "checked_at", "slots",
                                                    "in_window", "booking_url", "note")}
        out.append(row)

    return {
        "city": c["key"],
        "anchor": {"id": anchor.get("id"), "name": anchor.get("name"), "neighborhood": anchor.get("neighborhood"),
                   "cuisine": anchor.get("cuisine"), "difficulty": anchor.get("difficulty")},
        "date": day,
        "party": party,
        "window": {"from": time_from, "to": time_to} if (time_from or time_to) else None,
        "live_checked": bool(day and live_check),
        "alternates": out,
        **ctx.resy_budget.as_dict(),
    }
