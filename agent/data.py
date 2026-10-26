"""Read-only access to the city manifest and per-city spot datasets."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import CITIES_DIR


class UnknownCity(KeyError):
    pass


class UnknownSpot(KeyError):
    pass


@lru_cache(maxsize=1)
def manifest() -> list[dict[str, Any]]:
    data = json.loads((CITIES_DIR / "index.json").read_text(encoding="utf-8"))
    return [c for c in data.get("cities", []) if (c.get("source") or {}).get("type") == "json"]


def city_keys() -> list[str]:
    return [c["key"] for c in manifest()]


def resolve_city(name: str) -> dict[str, Any]:
    """Accept the manifest key, label or short code, case-insensitively."""
    q = (name or "").strip().lower()
    if not q:
        raise UnknownCity(name)
    for c in manifest():
        if q in {c["key"].lower(), (c.get("label") or "").lower(), (c.get("short") or "").lower()}:
            return c
    # loose: "new york" -> New York City, "washington" -> Washington, DC
    for c in manifest():
        if q in (c.get("label") or "").lower():
            return c
    raise UnknownCity(name)


def city_timezone(city: str) -> str:
    return resolve_city(city).get("timezone") or "America/New_York"


@lru_cache(maxsize=32)
def _load_city(key: str) -> dict[str, Any]:
    path = CITIES_DIR / f"{key}.json"
    if not path.exists():
        raise UnknownCity(key)
    data = json.loads(path.read_text(encoding="utf-8"))
    spots = data["spots"] if isinstance(data, dict) else data
    for s in spots:
        s.setdefault("city", key)
    return {"meta": data.get("meta", {}) if isinstance(data, dict) else {}, "spots": spots}


def spots(city: str) -> list[dict[str, Any]]:
    return _load_city(resolve_city(city)["key"])["spots"]


def spot(city: str, spot_id: str) -> dict[str, Any]:
    sid = (spot_id or "").strip().lower()
    for s in spots(city):
        if s.get("id", "").lower() == sid:
            return s
    raise UnknownSpot(spot_id)
