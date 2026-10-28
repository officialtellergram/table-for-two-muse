"""Tool registry: Anthropic-shaped tool definitions plus a dispatcher.

Each tool is a plain function taking keyword arguments and returning a JSON-able
dict. Errors come back as {"error": ...} so the planner can recover instead of
crashing the run. Phase 1 tools are read-only over cities/*.json. Phase 2 adds
check_live_availability (capped Resy calls, agent.live); tools listed in CTX_TOOLS
receive the per-request RequestContext as `_ctx` (SPEC section 3 and 8).
"""
from __future__ import annotations

import json
from typing import Any, Callable

from ..context import RequestContext
from ..data import UnknownCity, UnknownSpot, city_keys
from . import booking, drops, live, similar, spots, watch

ToolFn = Callable[..., dict[str, Any]]

_CITY_PROP = {
    "type": "string",
    "description": "City key, label or short code from the manifest, e.g. 'nyc', 'New York City', 'LA'.",
}
_SPOT_PROP = {"type": "string", "description": "The spot id returned by search_spots (e.g. 'carbone')."}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_spots",
        "description": (
            "Search the curated hard-to-book restaurants of one city. Use it to find a named "
            "restaurant (query='Carbone') or to shortlist alternates by neighborhood, cuisine, "
            "vibe, occasion and difficulty. Returns compact records with release schedule and "
            "booking window; call get_spot for the full record and tips."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": _CITY_PROP,
                "query": {"type": "string", "description": "Free text: restaurant name, dish, cuisine or neighborhood."},
                "neighborhood": {"type": "string", "description": "Neighborhood filter, substring match."},
                "cuisine": {"type": "string", "description": "Cuisine filter, substring match."},
                "vibe": {"type": "string", "description": "One vibe tag, e.g. 'romantic', 'special-occasion', 'lively'."},
                "occasion": {"type": "string", "description": "One occasion tag, e.g. 'impress', 'anniversary', 'group'."},
                "party": {"type": "integer", "description": "Party size (1-8). Recorded, not used to filter in this phase."},
                "max_difficulty": {"type": "integer", "minimum": 1, "maximum": 5,
                                   "description": "Keep spots with difficulty <= this (1 easy, 5 near-impossible)."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Max results, default 8."},
            },
            "required": ["city"],
        },
    },
    {
        "name": "get_spot",
        "description": "Full record for one spot: tips (quote verbatim), walk-in policy, platform URL, "
                       "availability snapshot and lastVerified date.",
        "input_schema": {
            "type": "object",
            "properties": {"city": _CITY_PROP, "spot_id": _SPOT_PROP},
            "required": ["city", "spot_id"],
        },
    },
    {
        "name": "next_drop",
        "description": (
            "When a spot next releases reservations (city-local and UTC, seconds until), and, "
            "given target_date, the exact drop at which that date becomes bookable and whether it "
            "has already happened. Use this before calling any date impossible."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": _CITY_PROP,
                "spot_id": _SPOT_PROP,
                "target_date": {"type": "string", "description": "YYYY-MM-DD the guest wants to dine."},
            },
            "required": ["city", "spot_id"],
        },
    },
    {
        "name": "booking_link",
        "description": "Pre-filled booking URL on the spot's own platform for a date and party size.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": _CITY_PROP,
                "spot_id": _SPOT_PROP,
                "date": {"type": "string", "description": "YYYY-MM-DD."},
                "party": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Party size."},
            },
            "required": ["city", "spot_id", "date", "party"],
        },
    },
    {
        "name": "check_live_availability",
        "description": (
            "Real open time slots on Resy for one spot, date and party size, right now. "
            "Read `status`: open = live tables listed in `slots`; none = Resy answered and nothing "
            "is open; failed / budget / rate_limited = UNKNOWN, not sold out. Each request has a hard "
            "cap of 4 Resy calls (see resy_calls_left): spend them on the first choice, then the best "
            "alternates. Results are cached 10 minutes. Non-Resy platforms come back `unsupported`."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": _CITY_PROP,
                "spot_id": _SPOT_PROP,
                "date": {"type": "string", "description": "YYYY-MM-DD."},
                "party": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Party size."},
                "time_from": {"type": "string", "description": "Optional HH:MM (24h) start of the guest's window."},
                "time_to": {"type": "string", "description": "Optional HH:MM (24h) end of the guest's window."},
            },
            "required": ["city", "spot_id", "date", "party"],
        },
    },
    {
        "name": "similar_spots",
        "description": (
            "Up to 3 alternates to a spot, ranked by shared vibe, occasion, cuisine, neighborhood, "
            "price and easier difficulty, with each one's drop for the date and a live Resy check "
            "(same 4-call budget; read each alternate's live.status). One call replaces search_spots "
            "+ next_drop + check_live_availability + booking_link for the alternates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": _CITY_PROP,
                "spot_id": dict(_SPOT_PROP, description="The guest's first choice; alternates are ranked against it."),
                "party": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Party size."},
                "date": {"type": "string", "description": "YYYY-MM-DD the guest wants to dine."},
                "n": {"type": "integer", "minimum": 1, "maximum": 3, "description": "How many alternates, max 3."},
                "time_from": {"type": "string", "description": "Optional HH:MM (24h) start of the guest's window."},
                "time_to": {"type": "string", "description": "Optional HH:MM (24h) end of the guest's window."},
                "live_check": {"type": "boolean", "description": "Default true. False skips the Resy calls."},
            },
            "required": ["city", "spot_id", "party", "date"],
        },
    },
    {
        "name": "create_watch",
        "description": (
            "Arm an alert for a spot over a date range (max 14 days) and optional time window. "
            "Signed-in guests get a real watchlist row (the radar emails them when a table opens); "
            "otherwise it is saved on the concierge only and `alerts_active` is false. Read "
            "`stored_in` and `note` and tell the guest which one happened. One watch per spot."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city": _CITY_PROP,
                "spot_id": _SPOT_PROP,
                "date_from": {"type": "string", "description": "YYYY-MM-DD, first date to watch."},
                "date_to": {"type": "string", "description": "YYYY-MM-DD, last date to watch (default: date_from)."},
                "party": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Party size."},
                "time_from": {"type": "string", "description": "Optional HH:MM (24h) earliest seating."},
                "time_to": {"type": "string", "description": "Optional HH:MM (24h) latest seating."},
                "channel": {"type": "string", "enum": ["email", "telegram", "push"], "description": "Default email."},
            },
            "required": ["city", "spot_id", "date_from", "party"],
        },
    },
]

REGISTRY: dict[str, ToolFn] = {
    "search_spots": spots.search_spots,
    "get_spot": spots.get_spot,
    "next_drop": drops.next_drop,
    "booking_link": booking.booking_link,
    "check_live_availability": live.check_live_availability,
    "similar_spots": similar.similar_spots,
    "create_watch": watch.create_watch,
}

# Tools that take the per-request context (Resy budget, guest token) as `_ctx`.
CTX_TOOLS = {"check_live_availability", "similar_spots", "create_watch"}


def call(name: str, args: dict[str, Any], ctx: RequestContext | None = None) -> dict[str, Any]:
    fn = REGISTRY.get(name)
    if fn is None:
        return {"error": f"unknown tool {name!r}", "known_tools": sorted(REGISTRY)}
    kwargs = dict(args or {})
    kwargs.pop("_ctx", None)          # never let the model inject the context
    if name in CTX_TOOLS:
        kwargs["_ctx"] = ctx if ctx is not None else RequestContext()
    try:
        return fn(**kwargs)
    except UnknownCity as e:
        return {"error": f"unknown city {e.args[0]!r}", "known_cities": city_keys()}
    except UnknownSpot as e:
        return {"error": f"unknown spot id {e.args[0]!r}; use search_spots to find the id"}
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except ValueError as e:
        return {"error": str(e)}


def call_json(name: str, args: dict[str, Any], ctx: RequestContext | None = None) -> str:
    return json.dumps(call(name, args, ctx), ensure_ascii=False, default=str)
