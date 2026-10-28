"""check_live_availability tool: real Resy slots for one spot, date and party size.

Backed by agent.live (capped, cached, paced). The result always says what kind of
answer it is: `checked` is True only when Resy actually answered (fresh or cached);
every other status means UNKNOWN, never "sold out".
"""
from __future__ import annotations

from datetime import date as _date
from typing import Any

from .. import data, live
from ..context import Budget, RequestContext
from .booking import prefill


def _hhmm(text: str | None, name: str) -> str | None:
    if not text:
        return None
    t = str(text).strip()
    if len(t) == 4 and t[1] == ":":
        t = "0" + t
    if len(t) != 5 or t[2] != ":" or not (t[:2] + t[3:]).isdigit():
        raise ValueError(f"{name} must be HH:MM (24h), got {text!r}")
    return t


def check_live_availability(city: str, spot_id: str, date: str, party: int = 2,
                            time_from: str | None = None, time_to: str | None = None,
                            _ctx: RequestContext | None = None) -> dict[str, Any]:
    c = data.resolve_city(city)
    s = data.spot(c["key"], spot_id)
    try:
        day = _date.fromisoformat(str(date).strip()[:10]).isoformat()
    except ValueError as e:
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}") from e
    party = max(1, min(int(party or 2), 20))
    lo, hi = _hhmm(time_from, "time_from"), _hhmm(time_to, "time_to")
    budget = _ctx.resy_budget if _ctx is not None else Budget()

    res = live.slots_for(s, day, party, budget)
    url, _how = prefill(s, day, party)
    slots = [{"time": sl["time"], "type": sl["type"]} for sl in res["slots"]]
    slots.sort(key=lambda x: x["time"])
    in_window = [sl for sl in slots if (not lo or sl["time"] >= lo) and (not hi or sl["time"] <= hi)]
    return {
        "spot_id": s.get("id"),
        "name": s.get("name"),
        "platform": s.get("platform"),
        "date": day,
        "party": party,
        "status": res["status"],
        "checked": res["checked"],
        "cached": res["cached"],
        "checked_at": res["checked_at"],
        "slots": slots,
        "in_window": in_window if (lo or hi) else None,
        "window": {"from": lo, "to": hi} if (lo or hi) else None,
        "booking_url": url,
        "note": res["note"],
        **budget.as_dict(),
    }
