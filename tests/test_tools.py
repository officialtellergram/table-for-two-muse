"""Offline tests for the phase-1 tools over the real cities/*.json data."""
import json

from agent import tools
from agent.data import city_keys


def test_registry_matches_schemas():
    assert {t["name"] for t in tools.TOOLS} == set(tools.REGISTRY)
    for t in tools.TOOLS:
        assert t["input_schema"]["type"] == "object"
        assert "city" in t["input_schema"]["properties"]


def test_city_resolution_accepts_label_and_short():
    assert "nyc" in city_keys()
    a = tools.call("search_spots", {"city": "New York City", "query": "Carbone"})
    b = tools.call("search_spots", {"city": "NYC", "query": "Carbone"})
    assert a["city"] == b["city"] == "nyc"
    assert a["spots"][0]["id"] == "carbone"
    assert a["spots"][0]["match"] == 1.0


def test_search_filters():
    r = tools.call("search_spots", {"city": "nyc", "neighborhood": "west village", "max_difficulty": 4, "limit": 5})
    assert r["matched"] >= 1
    for s in r["spots"]:
        assert "west village" in s["neighborhood"].lower()
        assert s["difficulty"] <= 4
    assert len(r["spots"]) <= 5
    r = tools.call("search_spots", {"city": "nyc", "vibe": "romantic", "cuisine": "italian"})
    for s in r["spots"]:
        assert "romantic" in s["vibe"] and "italian" in s["cuisine"].lower()


def test_search_fuzzy_name():
    r = tools.call("search_spots", {"city": "nyc", "query": "carbon"})
    assert r["spots"][0]["id"] == "carbone"


def test_get_spot_has_tips_and_freshness():
    s = tools.call("get_spot", {"city": "nyc", "spot_id": "carbone"})
    assert s["name"] == "Carbone" and s["tips"] and s["lastVerified"]
    assert s["timezone"] == "America/New_York"
    assert "coordinates" not in s


def test_next_drop_carbone():
    r = tools.call("next_drop", {"city": "nyc", "spot_id": "carbone", "target_date": "2026-11-07"})
    assert r["schedule"] == "daily" and r["booking_window_days"] == 30
    assert r["next_drop"]["local"].endswith("-04:00") or r["next_drop"]["local"].endswith("-05:00")
    assert "T10:00:00" in r["next_drop"]["local"]
    assert r["drop_for_target"]["local"].startswith("2026-10-08T10:00")
    assert r["drop_for_target"]["already_released"] is True


def test_next_drop_spain_has_none():
    r = tools.call("next_drop", {"city": "malaga", "spot_id": tools.call("search_spots", {"city": "malaga"})["spots"][0]["id"]})
    assert r["next_drop"] is None and "note" in r


def test_booking_link_platforms():
    r = tools.call("booking_link", {"city": "nyc", "spot_id": "carbone", "date": "2026-11-07", "party": 4})
    assert r["url"].startswith("https://resy.com/") and "date=2026-11-07" in r["url"] and "seats=4" in r["url"]
    # One of each other platform, if present in NYC.
    plats = {}
    for s in tools.call("search_spots", {"city": "nyc", "limit": 20})["spots"]:
        plats.setdefault(s["platform"], s["id"])
    for plat, key in (("OpenTable", "covers=4"), ("Tock", "size=4"), ("SevenRooms", "party_size=4")):
        if plat in plats:
            r = tools.call("booking_link", {"city": "nyc", "spot_id": plats[plat], "date": "2026-11-07", "party": 4})
            assert key in r["url"], (plat, r)


def test_errors_are_data_not_exceptions():
    assert "error" in tools.call("search_spots", {"city": "atlantis"})
    assert "error" in tools.call("get_spot", {"city": "nyc", "spot_id": "nope"})
    assert "error" in tools.call("next_drop", {"city": "nyc", "spot_id": "carbone", "target_date": "Saturday"})
    assert "error" in tools.call("nonexistent", {})
    json.loads(tools.call_json("get_spot", {"city": "nyc", "spot_id": "carbone"}))
