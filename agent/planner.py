"""Muse Wonder planner: the tool-use loop over agent.tools via the Meta Model API.

The Meta Model API speaks the Anthropic Messages shape (SPEC section 4), so the
Anthropic SDK is pointed at https://api.meta.ai with the Model API key as the
bearer token. Wonder returns redacted_thinking blocks alongside text/tool_use;
they are echoed back verbatim in the assistant turn, as the protocol requires.

run() is a generator of event dicts so the CLI and the SSE endpoint share one
loop:  {"type": "text"|"tool_call"|"tool_result"|"usage"|"final"|"error", ...}
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator
from zoneinfo import ZoneInfo

import anthropic

from . import config, data
from .context import RequestContext
from .tools import TOOLS, call as call_tool

_RESULT_PREVIEW = 400
# Full tool results up to this size ride along in the tool_result event so the web
# panel can render slots, links and watches from data instead of parsing prose.
_RESULT_INLINE_MAX = 6000


def system_prompt(default_city: str = "nyc", now: datetime | None = None) -> str:
    c = data.resolve_city(default_city)
    tz = ZoneInfo(c.get("timezone") or "America/New_York")
    local = (now or datetime.now(timezone.utc)).astimezone(tz)
    days = [(local + timedelta(days=i)) for i in range(1, 8)]
    tmpl = (config.PROMPTS_DIR / "system.md").read_text(encoding="utf-8")
    return tmpl.format(
        city_count=len(data.city_keys()),
        today_pretty=local.strftime("%A %d %B %Y, %H:%M"),
        timezone=c.get("timezone"),
        next_days=", ".join(d.strftime("%a %Y-%m-%d") for d in days),
        default_city=f"{c['key']} ({c.get('label')})",
        cities=", ".join(data.city_keys()),
    )


def client() -> anthropic.Anthropic:
    return anthropic.Anthropic(base_url=config.META_BASE_URL, auth_token=config.api_key(),
                               max_retries=2, timeout=120.0)


def _blocks(resp: anthropic.types.Message) -> list[dict[str, Any]]:
    """Assistant content as plain dicts, redacted_thinking included, for the next turn."""
    return [b.model_dump(exclude_none=True) for b in resp.content]


def run(message: str, city: str = "nyc", model: str | None = None,
        max_rounds: int | None = None, now: datetime | None = None,
        ctx: RequestContext | None = None) -> Iterator[dict[str, Any]]:
    """Drive one request through the planner, yielding events as they happen.

    `ctx` carries the per-request Resy budget and, when the guest is signed in,
    their Supabase token; a fresh one is made when none is given.
    """
    model = model or config.PLANNER_MODEL
    max_rounds = max_rounds or config.MAX_TOOL_ROUNDS
    ctx = ctx or RequestContext(city=city)
    system = system_prompt(city, now)
    messages: list[dict[str, Any]] = [{"role": "user", "content": message}]
    cli = client()
    models = [model] + ([config.FALLBACK_MODEL] if config.FALLBACK_MODEL != model else [])
    total_in = total_out = 0

    for rnd in range(1, max_rounds + 1):
        resp = None
        t0 = time.time()
        for m in models:
            try:
                resp = cli.messages.create(model=m, max_tokens=config.MAX_TOKENS, system=system,
                                           tools=TOOLS, messages=messages)
                if m != model:
                    yield {"type": "note", "text": f"fell back to {m}"}
                break
            except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
                yield {"type": "note", "text": f"{m}: {type(e).__name__}: {str(e)[:200]}"}
                continue
        if resp is None:
            yield {"type": "error", "text": "all models failed"}
            return
        u = resp.usage
        total_in += getattr(u, "input_tokens", 0) or 0
        total_out += getattr(u, "output_tokens", 0) or 0
        yield {"type": "usage", "round": rnd, "model": resp.model, "ms": int((time.time() - t0) * 1000),
               "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
               "cache_read": getattr(u, "cache_read_input_tokens", None),
               "stop_reason": resp.stop_reason}

        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        messages.append({"role": "assistant", "content": _blocks(resp)})

        if text and tool_uses:
            yield {"type": "text", "text": text, "interim": True}
        if resp.stop_reason != "tool_use" or not tool_uses:
            if resp.stop_reason == "max_tokens" and not text:
                yield {"type": "error", "text": "max_tokens hit before any answer; raise MUSE_MAX_TOKENS"}
                return
            yield {"type": "final", "text": text, "rounds": rnd,
                   "input_tokens": total_in, "output_tokens": total_out,
                   **ctx.resy_budget.as_dict()}
            return

        results: list[dict[str, Any]] = []
        for tu in tool_uses:
            yield {"type": "tool_call", "id": tu.id, "name": tu.name, "input": tu.input}
            out = call_tool(tu.name, tu.input or {}, ctx)
            payload = json.dumps(out, ensure_ascii=False, default=str)
            ev = {"type": "tool_result", "id": tu.id, "name": tu.name, "ok": "error" not in out,
                  "preview": payload[:_RESULT_PREVIEW], "bytes": len(payload)}
            if len(payload) <= _RESULT_INLINE_MAX:
                ev["result"] = out
            yield ev
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": payload})
        messages.append({"role": "user", "content": results})

    yield {"type": "error", "text": f"stopped after {max_rounds} tool rounds without a final answer"}


def ask(message: str, city: str = "nyc", **kw: Any) -> dict[str, Any]:
    """Blocking helper: collect the run into {answer, steps, usage}."""
    steps: list[dict[str, Any]] = []
    answer, usage, error = "", {}, None
    for ev in run(message, city, **kw):
        if ev["type"] in ("tool_call", "tool_result", "text", "note"):
            steps.append(ev)
        elif ev["type"] == "final":
            answer = ev["text"]
            usage = {k: ev[k] for k in ("rounds", "input_tokens", "output_tokens")}
        elif ev["type"] == "error":
            error = ev["text"]
    return {"answer": answer, "steps": steps, "usage": usage, "error": error}
