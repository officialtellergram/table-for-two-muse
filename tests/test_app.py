"""Offline tests for the FastAPI service; the planner is stubbed so no model is called."""
import json

from fastapi.testclient import TestClient

from agent import app as service
from agent import planner


def _fake_run(message, city="nyc", model=None, max_rounds=None, now=None):
    yield {"type": "tool_call", "id": "t1", "name": "search_spots", "input": {"city": city, "query": "Carbone"}}
    yield {"type": "tool_result", "id": "t1", "name": "search_spots", "ok": True, "preview": "{}", "bytes": 2}
    yield {"type": "final", "text": f"NOW: plan for {message!r}", "rounds": 1, "input_tokens": 10, "output_tokens": 5}


def test_health_and_tools():
    c = TestClient(service.app)
    h = c.get("/health").json()
    assert h["ok"] and "nyc" in h["cities"] and "next_drop" in h["tools"]
    assert [t["name"] for t in c.get("/tools").json()] == h["tools"]


def test_direct_tool_call():
    c = TestClient(service.app)
    r = c.post("/tools/next_drop", json={"city": "nyc", "spot_id": "carbone", "target_date": "2026-11-07"})
    assert r.status_code == 200 and r.json()["schedule"] == "daily"
    assert c.post("/tools/nope", json={}).status_code == 404


def test_ask_collects_run(monkeypatch):
    monkeypatch.setattr(planner, "run", _fake_run)
    c = TestClient(service.app)
    r = c.post("/ask", json={"message": "Carbone Saturday", "city": "NYC"}).json()
    assert r["answer"].startswith("NOW:") and r["usage"]["rounds"] == 1 and r["error"] is None
    assert [s["type"] for s in r["steps"]] == ["tool_call", "tool_result"]


def test_sse_stream(monkeypatch):
    monkeypatch.setattr(planner, "run", _fake_run)
    c = TestClient(service.app)
    with c.stream("GET", "/ask/stream", params={"q": "Carbone Saturday"}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = "".join(r.iter_text())
    frames = [f for f in body.split("\n\n") if f.strip()]
    types = [f.split("\n")[0].removeprefix("event: ") for f in frames]
    assert types == ["tool_call", "tool_result", "final"]
    last = json.loads(frames[-1].split("\n", 1)[1].removeprefix("data: "))
    assert last["text"].startswith("NOW:")
    r = c.post("/ask/stream", json={"message": "x"})
    assert r.status_code == 200 and "event: final" in r.text
