"""Offline tests for create_watch: local fallback for real, Supabase stubbed."""
import base64
import json

import pytest
from fastapi.testclient import TestClient

from agent import app as service
from agent import planner, tools, watches
from agent.context import RequestContext


def _jwt(sub="11111111-2222-3333-4444-555555555555"):
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{b64({'alg': 'HS256'})}.{b64({'sub': sub, 'role': 'authenticated'})}.sig"


@pytest.fixture(autouse=True)
def _local(tmp_path, monkeypatch):
    monkeypatch.setenv("T42_WATCHES_PATH", str(tmp_path / "watches.json"))
    yield


def test_local_fallback_when_not_signed_in():
    r = tools.call("create_watch", {"city": "nyc", "spot_id": "carbone", "date_from": "2026-11-07",
                                    "party": 4, "time_from": "19:00", "time_to": "21:00"}, RequestContext())
    assert r["stored_in"] == "local" and r["alerts_active"] is False and r["id"]
    assert r["dates"] == ["2026-11-07"] and r["earliest"] == "19:00" and r["latest"] == "21:00"
    assert "NOT email" in r["note"]
    rows = watches.list_local()
    assert len(rows) == 1 and rows[0]["venues"] == ["carbone"] and rows[0]["party"] == 4


def test_date_range_is_expanded_and_capped():
    r = tools.call("create_watch", {"city": "nyc", "spot_id": "carbone", "date_from": "2026-11-07",
                                    "date_to": "2026-11-09", "party": 2})
    assert r["dates"] == ["2026-11-07", "2026-11-08", "2026-11-09"]
    r = tools.call("create_watch", {"city": "nyc", "spot_id": "carbone", "date_from": "2026-11-01",
                                    "date_to": "2026-12-31", "party": 2})
    assert len(r["dates"]) == 14
    assert "error" in tools.call("create_watch", {"city": "nyc", "spot_id": "carbone", "date_from": "2026-11-09",
                                                  "date_to": "2026-11-07", "party": 2})
    assert "error" in tools.call("create_watch", {"city": "nyc", "spot_id": "carbone", "date_from": "Sat", "party": 2})


def test_signed_in_guest_inserts_into_supabase(monkeypatch):
    sent = {}

    class Resp:
        status_code = 201
        text = ""

        def json(self):
            return [dict(sent["json"], id="db-row-1")]

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.update(url=url, json=json, headers=headers)
        return Resp()

    import requests
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co/")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    ctx = RequestContext(user_token=_jwt())
    r = tools.call("create_watch", {"city": "nyc", "spot_id": "carbone", "date_from": "2026-11-07", "party": 2}, ctx)
    assert r["stored_in"] == "supabase" and r["alerts_active"] is True and r["id"] == "db-row-1"
    assert sent["url"] == "https://example.supabase.co/rest/v1/watchlists"
    assert sent["headers"]["apikey"] == "anon-key" and sent["headers"]["Authorization"].endswith(_jwt())
    assert sent["json"]["user_id"] == "11111111-2222-3333-4444-555555555555"
    assert sent["json"]["venues"] == ["carbone"] and sent["json"]["dates"] == ["2026-11-07"]
    assert watches.list_local() == []


def test_supabase_failure_falls_back_to_local_and_says_so(monkeypatch):
    class Resp:
        status_code = 401
        text = "JWT expired"

    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: Resp())
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    r = tools.call("create_watch", {"city": "nyc", "spot_id": "carbone", "date_from": "2026-11-07", "party": 2},
                   RequestContext(user_token=_jwt()))
    assert r["stored_in"] == "local" and r["alerts_active"] is False
    assert "401" in r["note"] and "NOT email" in r["note"]
    assert len(watches.list_local()) == 1


def test_supabase_config_comes_from_web_config_js(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    url, key = watches.supabase_config()
    assert url and url.startswith("https://") and ".supabase.co" in url
    assert key and key.startswith("eyJ")


def test_token_reaches_the_request_context(monkeypatch):
    seen = {}

    def fake_run(message, city="nyc", model=None, max_rounds=None, now=None, ctx=None):
        seen["token"] = ctx.user_token if ctx else None
        yield {"type": "final", "text": "ok", "rounds": 1, "input_tokens": 1, "output_tokens": 1}

    monkeypatch.setattr(planner, "run", fake_run)
    c = TestClient(service.app)
    c.post("/ask", json={"message": "x", "user_token": "tok-body"})
    assert seen["token"] == "tok-body"
    c.post("/ask/stream", json={"message": "x"}, headers={"Authorization": "Bearer tok-header"})
    assert seen["token"] == "tok-header"
    c.get("/ask/stream", params={"q": "x"})
    assert seen["token"] is None
    assert c.get("/health").json()["phase"] == 2
