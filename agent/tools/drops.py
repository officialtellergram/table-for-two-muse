"""next_drop tool: thin wrapper over agent.drops.describe with city timezone lookup."""
from __future__ import annotations

from datetime import date
from typing import Any

from .. import data
from .. import drops as engine


def _parse_date(text: str | None) -> date | None:
    if not text:
        return None
    try:
        return date.fromisoformat(str(text).strip()[:10])
    except ValueError as e:
        raise ValueError(f"target_date must be YYYY-MM-DD, got {text!r}") from e


def next_drop(city: str, spot_id: str, target_date: str | None = None) -> dict[str, Any]:
    c = data.resolve_city(city)
    s = data.spot(c["key"], spot_id)
    out = engine.describe(s, c.get("timezone") or "America/New_York", _parse_date(target_date))
    out["name"] = s.get("name")
    out["city"] = c["key"]
    out["walk_ins"] = s.get("walkIns")
    return out
