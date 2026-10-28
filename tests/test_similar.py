"""Offline tests for similar_spots: ranking over real NYC data, live calls stubbed."""
import pytest

from agent import live, tools
from agent.context import Budget, RequestContext
from agent.tools import similar

DAY = "2026-11-07"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    live.clear_cache()
    monkeypatch.setattr(live, "PACE_S", 0.0)
    monkeypatch.setattr(live, "rate_limited", lambda: False)
    monkeypatch.setattr(live, "_seeded", True)
    # Every Resy venue resolves without a lookup so the budget only counts find calls.
    monkeypatch.setattr(live, "venue_id", lambda spot, budget: (hash(spot["id"]) % 100000 + 1, "cached"))
    yield
    live.clear_cache()


def test_ranking_prefers_shared_traits_and_easier_tables():
    carbone = tools.call("get_spot", {"city": "nyc", "spot_id": "carbone"})
    r = tools.call("similar_spots", {"city": "nyc", "spot_id": "carbone", "party": 4, "date": DAY,
                                     "live_check": False})
    assert r["anchor"]["id"] == "carbone" and r["live_checked"] is False
    alts = r["alternates"]
    assert 1 <= len(alts) <= 3 and all(a["id"] != "carbone" for a in alts)
    assert [a["score"] for a in alts] == sorted((a["score"] for a in alts), reverse=True)
    for a in alts:
        assert a["why"] and "live" not in a and a["drop"]["schedule"]
        shared = set(a.get("vibe") or []) & set(carbone["vibe"]) or \
            set(a.get("occasion") or []) & set(carbone["occasion"]) or \
            carbone["cuisine"].lower() in (a.get("cuisine") or "").lower()
        assert shared, a
    pts_easy, _ = similar.score(carbone, dict(carbone, id="x", difficulty=3))
    pts_hard, _ = similar.score(carbone, dict(carbone, id="y", difficulty=5))
    assert pts_easy > pts_hard


def test_each_alternate_is_live_checked_on_the_shared_budget(monkeypatch):
    calls = []

    def fake(vid, day, party, lat, lng):
        calls.append((vid, day, party))
        return [{"date": day, "time": "20:00", "type": "Dining Room", "token": "t"}]

    monkeypatch.setattr(live, "_find", fake)
    ctx = RequestContext(resy_budget=Budget(4))
    ctx.resy_budget.take()   # the first choice already spent one
    r = tools.call("similar_spots", {"city": "nyc", "spot_id": "carbone", "party": 2, "date": DAY,
                                     "time_from": "19:00", "time_to": "21:00"}, ctx)
    assert r["live_checked"] is True and len(r["alternates"]) == 3
    resy = [a for a in r["alternates"] if a["platform"] == "Resy"]
    for a in r["alternates"]:
        assert "live" in a and "booking_url" in a["live"]
        if a["platform"] == "Resy":
            assert a["live"]["status"] == "open" and a["live"]["in_window"][0]["time"] == "20:00"
        else:
            assert a["live"]["status"] == "unsupported"
    assert len(calls) == len(resy) and r["resy_calls_used"] == 1 + len(resy)
    assert r["resy_calls_used"] <= 4


def test_budget_exhaustion_is_reported_not_hidden(monkeypatch):
    monkeypatch.setattr(live, "_find", lambda *a: [])
    ctx = RequestContext(resy_budget=Budget(1))
    r = tools.call("similar_spots", {"city": "nyc", "spot_id": "carbone", "party": 2, "date": DAY}, ctx)
    statuses = [a["live"]["status"] for a in r["alternates"] if a["platform"] == "Resy"]
    assert statuses[0] == "none" and all(s == "budget" for s in statuses[1:])
    assert r["resy_calls_left"] == 0


def test_n_is_capped_and_errors_are_data():
    r = tools.call("similar_spots", {"city": "nyc", "spot_id": "carbone", "party": 2, "date": DAY, "n": 9,
                                     "live_check": False})
    assert len(r["alternates"]) == 3
    assert "error" in tools.call("similar_spots", {"city": "nyc", "spot_id": "carbone", "party": 2, "date": "Sat"})
    assert "error" in tools.call("similar_spots", {"city": "nyc", "spot_id": "nope", "party": 2, "date": DAY})
