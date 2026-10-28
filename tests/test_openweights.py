"""agent.openweights: Muse Spark Open on Baseten over the OpenAI chat shape, offline.

A MockTransport stands in for inference.baseten.co; search_spots runs for real over
cities/*.json so the tool round is exercised end to end.
"""
from __future__ import annotations

import json

import httpx
import pytest

from agent import config, openweights, planner


def _resp(message: dict, finish: str = "stop") -> dict:
    return {"id": "chatcmpl-1", "model": "meta-models/muse-spark-open-1026",
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 30,
                      "prompt_tokens_details": {"cached_tokens": 100}}}


def _client(responses: list, log: list) -> httpx.Client:
    def handler(req: httpx.Request) -> httpx.Response:
        log.append({"url": str(req.url), "auth": req.headers.get("authorization"),
                    "body": json.loads(req.content)})
        r = responses.pop(0)
        if isinstance(r, int):
            return httpx.Response(r, json={"error": {"message": "boom"}})
        return httpx.Response(200, json=r)
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("BASETEN_API_KEY", "test-baseten-key")
    monkeypatch.setattr(config, "OPENWEIGHTS", "baseten")


def test_openai_tools_shape():
    tools = openweights.openai_tools()
    names = [t["function"]["name"] for t in tools]
    assert "search_spots" in names and "create_watch" in names
    t = tools[0]
    assert t["type"] == "function"
    assert t["function"]["parameters"]["type"] == "object"
    assert "description" in t["function"]


def test_resolve_model_aliases():
    assert openweights.resolve_model("spark-open") == config.OPENWEIGHTS_MODEL
    assert openweights.resolve_model(None) == config.OPENWEIGHTS_MODEL
    assert openweights.resolve_model("meta-models/other") == "meta-models/other"
    assert config.is_openweights_model("Spark-Open") and not config.is_openweights_model("muse-wonder-1.0")


def test_tool_round_then_final(key):
    log: list = []
    responses = [
        _resp({"role": "assistant", "content": "", "reasoning_content": "find it first",
               "tool_calls": [{"id": "call_1", "type": "function",
                               "function": {"name": "search_spots",
                                            "arguments": json.dumps({"city": "nyc", "query": "Carbone"})}}]},
              "tool_calls"),
        _resp({"role": "assistant", "reasoning_content": "done",
               "content": "<think>hidden</think>NOW: Carbone is on Resy; DROP: 30 days out."}),
    ]
    evs = list(openweights.run("Carbone Saturday for four", "nyc", model="spark-open",
                               client=_client(responses, log)))
    assert [e["type"] for e in evs] == ["usage", "thinking", "tool_call", "tool_result",
                                        "usage", "thinking", "final"]
    final = evs[-1]
    assert final["text"].startswith("NOW: Carbone") and "<think>" not in final["text"]
    assert final["provider"] == "baseten" and final["rounds"] == 2
    assert final["input_tokens"] == 240 and final["output_tokens"] == 60
    assert evs[0]["cache_read"] == 100 and evs[0]["provider"] == "baseten"

    tr = evs[3]
    assert tr["ok"] and tr["name"] == "search_spots" and tr["result"]["spots"]
    assert any(s["id"] == "carbone" for s in tr["result"]["spots"])

    first, second = log[0], log[1]
    assert first["url"].endswith("/v1/chat/completions")
    assert first["auth"] == "Bearer test-baseten-key"
    b = first["body"]
    assert b["model"] == "meta-models/muse-spark-open-1026"
    assert b["reasoning_effort"] == config.OPENWEIGHTS_EFFORT and b["max_tokens"] == config.OPENWEIGHTS_MAX_TOKENS
    assert b["messages"][0]["role"] == "system" and "concierge" in b["messages"][0]["content"]
    assert b["tools"][0]["function"]["name"] == "search_spots"
    msgs = second["body"]["messages"]
    assert msgs[-2]["role"] == "assistant" and msgs[-2]["tool_calls"][0]["id"] == "call_1"
    assert "reasoning_content" not in msgs[-2]
    assert msgs[-1]["role"] == "tool" and msgs[-1]["tool_call_id"] == "call_1"
    assert "carbone" in msgs[-1]["content"]


def test_bad_arguments_still_dispatch(key):
    log: list = []
    responses = [
        _resp({"role": "assistant", "content": None,
               "tool_calls": [{"id": "c1", "type": "function",
                               "function": {"name": "search_spots", "arguments": "{not json"}}]}, "tool_calls"),
        _resp({"role": "assistant", "content": "WATCH: nothing"}),
    ]
    evs = list(openweights.run("x", "nyc", client=_client(responses, log)))
    tr = [e for e in evs if e["type"] == "tool_result"][0]
    assert tr["ok"] is False and "error" in tr["result"]      # city missing -> tool error, run continues
    assert evs[-1]["type"] == "final"


def test_first_call_fails_falls_back_to_wonder(key, monkeypatch):
    seen: dict = {}

    def fake_run(message, city="nyc", model=None, **kw):
        seen.update(message=message, city=city, model=model)
        yield {"type": "final", "text": "from wonder", "rounds": 1}
    monkeypatch.setattr(planner, "run", fake_run)
    evs = list(openweights.run("hi", "nyc", client=_client([503], [])))
    assert [e["type"] for e in evs] == ["note", "note", "final"]
    assert "HTTP 503" in evs[0]["text"] and "fell back to" in evs[1]["text"]
    assert evs[-1]["text"] == "from wonder"
    assert seen["model"] == config.PLANNER_MODEL and seen["message"] == "hi"


def test_mid_run_failure_is_an_error_not_a_fallback(key, monkeypatch):
    monkeypatch.setattr(planner, "run", lambda *a, **k: iter([{"type": "final", "text": "no"}]))
    responses = [
        _resp({"role": "assistant", "content": "",
               "tool_calls": [{"id": "c1", "type": "function",
                               "function": {"name": "search_spots", "arguments": '{"city":"nyc","query":"Carbone"}'}}]}, "tool_calls"),
        500,
    ]
    evs = list(openweights.run("x", "nyc", client=_client(responses, [])))
    assert evs[-1]["type"] == "error" and "mid-run" in evs[-1]["text"]


def test_no_key_falls_back(monkeypatch):
    monkeypatch.delenv("BASETEN_API_KEY", raising=False)
    monkeypatch.setattr(config, "_local_env", lambda: {})
    monkeypatch.setattr(config, "OPENWEIGHTS", "baseten")
    monkeypatch.setattr(planner, "run", lambda *a, **k: iter([{"type": "final", "text": "wonder"}]))
    evs = list(openweights.run("x", "nyc"))
    assert "No Baseten API key" in evs[0]["text"] and evs[-1]["text"] == "wonder"


def test_off_flag(monkeypatch):
    monkeypatch.setattr(config, "OPENWEIGHTS", "off")
    evs = list(openweights.run("x", "nyc"))
    assert evs == [{"type": "error", "text": "open weights are switched off (OPENWEIGHTS=off)"}]


def test_planner_dispatches_alias(monkeypatch):
    called: dict = {}

    def fake(message, city="nyc", model=None, **kw):
        called.update(model=model, city=city)
        yield {"type": "final", "text": "ow", "rounds": 1, "input_tokens": 1, "output_tokens": 1}
    monkeypatch.setattr(openweights, "run", fake)
    evs = list(planner.run("hi", "la", model="spark-open"))
    assert evs[0]["text"] == "ow" and called == {"model": "spark-open", "city": "la"}
    out = planner.ask("hi", "la", model="baseten")
    assert out["answer"] == "ow"
