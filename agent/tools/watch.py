"""create_watch tool: arm an alert for a spot over a date range and time window.

Row shape mirrors public.watchlists / scraper/notify.py:
{city, venues:[spot_id], earliest, latest, dates:[...], party}. Where it was
stored (the guest's account watchlist or the concierge's local file) is part of
the result, so the answer can be honest about whether an email will come.
"""
from __future__ import annotations

from datetime import date as _date, timedelta
from typing import Any

from .. import data, watches
from ..context import RequestContext
from .live import _hhmm

MAX_DAYS = 14


def _day(text: str | None, name: str) -> _date | None:
    if not text:
        return None
    try:
        return _date.fromisoformat(str(text).strip()[:10])
    except ValueError as e:
        raise ValueError(f"{name} must be YYYY-MM-DD, got {text!r}") from e


def create_watch(city: str, spot_id: str, date_from: str, date_to: str | None = None, party: int = 2,
                 time_from: str | None = None, time_to: str | None = None, channel: str = "email",
                 _ctx: RequestContext | None = None) -> dict[str, Any]:
    c = data.resolve_city(city)
    s = data.spot(c["key"], spot_id)
    start = _day(date_from, "date_from")
    end = _day(date_to, "date_to") or start
    if end < start:
        raise ValueError("date_to is before date_from")
    if (end - start).days + 1 > MAX_DAYS:
        end = start + timedelta(days=MAX_DAYS - 1)
    days = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    party = max(1, min(int(party or 2), 20))
    lo, hi = _hhmm(time_from, "time_from"), _hhmm(time_to, "time_to")
    channel = (channel or "email").strip().lower()
    if channel not in ("email", "telegram", "push"):
        channel = "email"

    row = {"city": c["key"], "venues": [s["id"]], "earliest": lo, "latest": hi, "dates": days, "party": party}
    token = _ctx.user_token if _ctx is not None else None
    stored, where, problem = watches.save(row, token)

    if where == "supabase":
        note = ("Saved to the guest's Table for Two watchlist. The radar emails them the moment a matching "
                "table opens (cancellation or drop).")
    else:
        note = ("Saved on the concierge only: the guest is not signed in, so this watch will NOT email anyone. "
                "Tell them to tap Get alerts and sign in to make it a real watch.")
        if problem:
            note = f"Account save failed ({problem}); " + note[0].lower() + note[1:]
    return {
        "id": stored.get("id"),
        "stored_in": where,
        "alerts_active": where == "supabase",
        "city": c["key"],
        "spot_id": s["id"],
        "name": s.get("name"),
        "dates": days,
        "earliest": lo,
        "latest": hi,
        "party": party,
        "channel": channel,
        "note": note,
    }
