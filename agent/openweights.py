"""Muse Spark Open on Baseten: the same tool loop, over the OpenAI chat-completions shape.

Meta's open-weights Muse Spark Open (816B MoE, 42B active) is far too big to host on
hackathon credits, but Baseten serves it per token for the event
(https://inference.baseten.co/v1, model meta-models/muse-spark-open-1026). This module
runs the concierge planner on it: the Anthropic-shaped tool definitions in agent.tools
are translated to OpenAI function tools, tool calls come back as message.tool_calls,
results go back as role "tool" messages. Reasoning arrives in message.reasoning_content
(Spark Open always reasons; reasoning_effort trims it) and is surfaced as a "thinking"
event, never echoed back into the conversation.

run() yields the same event dicts as agent.planner.run so the CLI, the SSE endpoint and
the web panel need no changes. If the very first call fails (no key, 4xx, network) the
run falls back to Muse Wonder on the Meta API, so the demo never depends on it.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any, Iterator

import httpx

from . import config
from .context import RequestContext
from .tools import TOOLS, call as call_tool

_RESULT_PREVIEW = 400
_RESULT_INLINE_MAX = 24000
_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.S)


class OpenWeightsError(RuntimeError):
    pass


def openai_tools(tools: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Anthropic-shaped tool definitions -> OpenAI function tools."""
    return [{"type": "function",
             "function": {"name": t["name"], "description": t["description"],
                          "parameters": t["input_schema"]}}
            for t in (tools if tools is not None else TOOLS)]


def chat(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
         model: str | None = None, max_tokens: int | None = None, effort: str | None = None,
         timeout: float = 180.0, client: httpx.Client | None = None) -> dict[str, Any]:
    """One chat-completions call to Baseten. Raises OpenWeightsError on a 4xx/5xx."""
    body: dict[str, Any] = {
        "model": model or config.OPENWEIGHTS_MODEL,
        "messages": messages,
        "max_tokens": max_tokens or config.OPENWEIGHTS_MAX_TOKENS,
        "reasoning_effort": effort or config.OPENWEIGHTS_EFFORT,
    }
    if tools:
        body["tools"] = tools
    headers = {"Authorization": f"Bearer {config.baseten_key()}"}
    url = config.BASETEN_BASE_URL.rstrip("/") + "/chat/completions"
    r = (client.post(url, headers=headers, json=body, timeout=timeout) if client
         else httpx.post(url, headers=headers, json=body, timeout=timeout))
    if r.status_code >= 400:
        raise OpenWeightsError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def resolve_model(model: str | None) -> str:
    """Aliases ('spark-open', 'baseten', ...) become the hackathon slug; full slugs pass through."""
    m = (model or "").strip()
    if not m or m.lower() in config.OPENWEIGHTS_ALIASES:
        return config.OPENWEIGHTS_MODEL
    return m


def _text(msg: dict[str, Any]) -> str:
    c = msg.get("content")
    if isinstance(c, list):          # some servers return content parts
        c = "".join(p.get("text", "") for p in c if isinstance(p, dict))
    return _THINK_RE.sub("", c or "").strip()


def run(message: str, city: str = "nyc", model: str | None = None,
        max_rounds: int | None = None, now: datetime | None = None,
        ctx: RequestContext | None = None, fallback: bool = True,
        client: httpx.Client | None = None) -> Iterator[dict[str, Any]]:
    """Drive one request through Spark Open on Baseten, yielding planner-shaped events."""
    from . import planner   # system prompt and the Wonder fallback; imported late (planner imports us)

    if config.OPENWEIGHTS == "off":
        yield {"type": "error", "text": "open weights are switched off (OPENWEIGHTS=off)"}
        return
    model = resolve_model(model)
    max_rounds = max_rounds or config.MAX_TOOL_ROUNDS
    ctx = ctx or RequestContext(city=city)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": planner.system_prompt(city, now)},
        {"role": "user", "content": message},
    ]
    tools = openai_tools()
    total_in = total_out = 0

    for rnd in range(1, max_rounds + 1):
        t0 = time.time()
        try:
            resp = chat(messages, tools, model=model, client=client)
        except (OpenWeightsError, httpx.HTTPError, RuntimeError) as e:
            yield {"type": "note", "text": f"{model} on Baseten: {type(e).__name__}: {str(e)[:200]}"}
            if rnd == 1 and fallback:
                yield {"type": "note", "text": f"fell back to {config.PLANNER_MODEL} on the Meta API"}
                yield from planner.run(message, city, model=config.PLANNER_MODEL,
                                       max_rounds=max_rounds, now=now, ctx=ctx)
                return
            yield {"type": "error", "text": "open-weights model failed mid-run"}
            return

        choice = (resp.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        u = resp.get("usage") or {}
        total_in += u.get("prompt_tokens") or 0
        total_out += u.get("completion_tokens") or 0
        yield {"type": "usage", "round": rnd, "model": resp.get("model") or model,
               "provider": "baseten", "ms": int((time.time() - t0) * 1000),
               "input_tokens": u.get("prompt_tokens"), "output_tokens": u.get("completion_tokens"),
               "cache_read": (u.get("prompt_tokens_details") or {}).get("cached_tokens"),
               "stop_reason": choice.get("finish_reason")}

        reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
        if reasoning:
            yield {"type": "thinking", "text": reasoning[:600], "chars": len(reasoning)}
        text = _text(msg)
        calls = msg.get("tool_calls") or []
        assistant: dict[str, Any] = {"role": "assistant", "content": msg.get("content") or ""}
        if calls:
            assistant["tool_calls"] = calls
        messages.append(assistant)

        if text and calls:
            yield {"type": "text", "text": text, "interim": True}
        if not calls:
            if choice.get("finish_reason") == "length" and not text:
                yield {"type": "error", "text": "max_tokens hit before any answer; raise OPENWEIGHTS_MAX_TOKENS"}
                return
            yield {"type": "final", "text": text, "rounds": rnd, "provider": "baseten",
                   "input_tokens": total_in, "output_tokens": total_out,
                   **ctx.resy_budget.as_dict()}
            return

        for tc in calls:
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            yield {"type": "tool_call", "id": tc.get("id"), "name": name, "input": args}
            out = call_tool(name, args, ctx)
            payload = json.dumps(out, ensure_ascii=False, default=str)
            ev = {"type": "tool_result", "id": tc.get("id"), "name": name, "ok": "error" not in out,
                  "preview": payload[:_RESULT_PREVIEW], "bytes": len(payload)}
            if len(payload) <= _RESULT_INLINE_MAX:
                ev["result"] = out
            yield ev
            messages.append({"role": "tool", "tool_call_id": tc.get("id"), "content": payload})

    yield {"type": "error", "text": f"stopped after {max_rounds} tool rounds without a final answer"}
