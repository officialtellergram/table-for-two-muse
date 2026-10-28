"""Offline tests for check_live_availability: the Resy HTTP call is stubbed, the
cache, budget and None-vs-[] semantics are exercised for real."""
import pytest

from agent import live, tools
from agent.context import Budget, RequestContext

DAY = "2026-11-07"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    live.clear_cache()
    monkeypatch.setattr(live, "PACE_S", 0.0)
    monkeypatch.setattr(live, "rate_limited", lambda: False)
    # Carbone's Resy id is in scraper/.sniper_state.json; make the test independent of it.
    monkeypatch.setitem(live._venue_ids, "new-york-ny/carbone", 6194)
    monkeypatch.setattr(live, "_seeded", True)
    yield
    live.clear_cache()


def _stub(monkeypatch, answer):
    calls = []

    def fake(vid, day, party, lat, lng):
        calls.append((vid, day, party))
        return answer() if callable(answer) else answer

    monkeypatch.setattr(live, "_find", fake)
    return calls


def test_open_slots_and_window(monkeypatch):
    calls = _stub(monkeypatch, [{"date": DAY, "time": "21:30", "type": "Dining Room", "token": "x"},
                                {"date": DAY, "time": "17:00", "type": "Bar", "token": "y"},
                                {"date": DAY, "time": "20:15", "type": "Dining Room", "token": "z"}])
    ctx = RequestContext()
    r = tools.call("check_live_availability",
                   {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 4,
                    "time_from": "19:00", "time_to": "21:00"}, ctx)
    assert r["status"] == "open" and r["checked"] is True and r["cached"] is False
    assert [s["time"] for s in r["slots"]] == ["17:00", "20:15", "21:30"]
    assert [s["time"] for s in r["in_window"]] == ["20:15"]
    assert r["booking_url"].startswith("https://resy.com/") and "seats=4" in r["booking_url"]
    assert r["resy_calls_used"] == 1 and r["resy_calls_left"] == 3
    assert calls == [(6194, DAY, 4)]


def test_cache_hit_is_free(monkeypatch):
    calls = _stub(monkeypatch, [])
    ctx = RequestContext()
    a = tools.call("check_live_availability", {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 2}, ctx)
    b = tools.call("check_live_availability", {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 2}, ctx)
    assert a["status"] == "none" and a["checked"] is True and a["slots"] == []
    assert b["status"] == "none" and b["cached"] is True and b["checked_at"] == a["checked_at"]
    assert len(calls) == 1 and ctx.resy_budget.used == 1
    # A different party size is a different cache key.
    tools.call("check_live_availability", {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 3}, ctx)
    assert len(calls) == 2


def test_failed_lookup_is_unknown_not_empty(monkeypatch):
    _stub(monkeypatch, None)
    r = tools.call("check_live_availability", {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 2},
                   RequestContext())
    assert r["status"] == "failed" and r["checked"] is False and r["slots"] == []
    assert "unknown" in r["note"].lower()
    # Failures are not cached: the next call tries Resy again.
    calls = _stub(monkeypatch, [])
    r = tools.call("check_live_availability", {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 2},
                   RequestContext())
    assert r["status"] == "none" and len(calls) == 1


def test_budget_cap(monkeypatch):
    calls = _stub(monkeypatch, [])
    ctx = RequestContext(resy_budget=Budget(2))
    for i in range(3):
        r = tools.call("check_live_availability",
                       {"city": "nyc", "spot_id": "carbone", "date": f"2026-11-0{i + 1}", "party": 2}, ctx)
    assert r["status"] == "budget" and r["checked"] is False
    assert len(calls) == 2 and r["resy_calls_left"] == 0


def test_rate_limited_skips_resy(monkeypatch):
    calls = _stub(monkeypatch, [])
    monkeypatch.setattr(live, "rate_limited", lambda: True)
    r = tools.call("check_live_availability", {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 2},
                   RequestContext())
    assert r["status"] == "rate_limited" and calls == [] and r["resy_calls_used"] == 0


def test_non_resy_platform_is_unsupported(monkeypatch):
    calls = _stub(monkeypatch, [])
    others = [s for s in tools.call("search_spots", {"city": "nyc", "limit": 20})["spots"] if s["platform"] != "Resy"]
    if not others:
        pytest.skip("no non-Resy spot in NYC data")
    r = tools.call("check_live_availability", {"city": "nyc", "spot_id": others[0]["id"], "date": DAY, "party": 2},
                   RequestContext())
    assert r["status"] == "unsupported" and r["checked"] is False and calls == []
    assert r["booking_url"]


def test_bad_inputs_are_data():
    assert "error" in tools.call("check_live_availability",
                                 {"city": "nyc", "spot_id": "carbone", "date": "Saturday", "party": 2})
    assert "error" in tools.call("check_live_availability",
                                 {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 2, "time_from": "8pm"})
    # The model cannot smuggle a context in.
    r = tools.call("check_live_availability",
                   {"city": "nyc", "spot_id": "carbone", "date": DAY, "party": 2, "_ctx": "x"})
    assert "error" not in r or "bad arguments" not in r["error"]


def test_parse_slots_shape():
    payload = {"results": {"venues": [{"slots": [
        {"date": {"start": "2026-11-07 19:30:00"}, "config": {"type": "Dining Room", "token": "t"}},
        {"date": {"start": "bad"}, "config": {}},
    ]}]}}
    assert live.parse_slots(payload) == [{"date": DAY, "time": "19:30", "type": "Dining Room", "token": "t"}]
