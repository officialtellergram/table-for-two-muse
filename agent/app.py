"""FastAPI service for the concierge. Runs locally with uvicorn and on Modal via
agent/modal_app.py.

  GET  /health            liveness + model + cities + tool names
  GET  /tools             the tool definitions the planner sees
  POST /tools/{name}      call one tool directly (debugging, no model)
  POST /ask               {message, city?, model?, user_token?} -> {answer, steps, usage, error}
  GET  /ask/stream?q=..   Server-Sent Events, one event per planner event
  POST /ask/stream        same, JSON body
  POST /ask/voice         multipart {audio: WAV, city?, run?} -> Muse Voice Transcribe;
                          returns {transcript, ...} so the guest can fix it before the
                          planner runs, or with run=true streams a `transcript` event
                          followed by the planner events

SSE frames are `event: <type>` + `data: <json>` and end with a `final` or `error`
event, which web/concierge.js consumes. A signed-in guest's Supabase access token
travels as `user_token` in the body or as `Authorization: Bearer <jwt>`; it is
only ever forwarded to Supabase by create_watch, never to the model.
"""
from __future__ import annotations

import json
from typing import Any, Iterator

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import config, planner, tools, voice
from .context import RequestContext
from .data import city_keys

app = FastAPI(title="Table for Two concierge", version="0.1.0",
              description="Muse Wonder planner over Table for Two's drop data.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"],
                   allow_headers=["*"])


class AskIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="What the guest said.")
    city: str = Field("nyc", description="Default city key, label or short code.")
    model: str | None = Field(None, description="Override the planner model; 'spark-open' runs the "
                                                "open-weights Muse Spark Open on Baseten.")
    user_token: str | None = Field(None, description="Supabase access token of a signed-in guest.")


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    return auth[7:].strip() or None if auth.lower().startswith("bearer ") else None


def _ctx(city: str, token: str | None) -> RequestContext:
    return RequestContext(city=city, user_token=token)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "model": config.PLANNER_MODEL, "fallback": config.FALLBACK_MODEL,
            "base_url": config.META_BASE_URL, "cities": city_keys(),
            "tools": [t["name"] for t in tools.TOOLS], "phase": 3,
            "openweights": {"provider": config.OPENWEIGHTS, "model": config.OPENWEIGHTS_MODEL,
                            "base_url": config.BASETEN_BASE_URL, "alias": "spark-open",
                            "key": config.has_baseten_key()}}


@app.get("/tools")
def list_tools() -> list[dict[str, Any]]:
    return tools.TOOLS


@app.post("/tools/{name}")
def call_tool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    if name not in tools.REGISTRY:
        raise HTTPException(404, f"unknown tool {name!r}")
    return tools.call(name, args or {})


@app.post("/ask")
def ask(body: AskIn, request: Request) -> dict[str, Any]:
    return planner.ask(body.message, body.city, model=body.model,
                       ctx=_ctx(body.city, body.user_token or _bearer(request)))


def _sse(events: Iterator[dict[str, Any]]) -> Iterator[str]:
    for ev in events:
        yield f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"


def _stream(message: str, city: str, model: str | None, token: str | None) -> StreamingResponse:
    return StreamingResponse(_sse(planner.run(message, city, model=model, ctx=_ctx(city, token))),
                             media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/ask/stream")
def ask_stream_get(request: Request, q: str = Query(..., min_length=1, max_length=2000),
                   city: str = "nyc", model: str | None = None) -> StreamingResponse:
    return _stream(q, city, model, _bearer(request))


@app.post("/ask/stream")
def ask_stream_post(body: AskIn, request: Request) -> StreamingResponse:
    return _stream(body.message, body.city, body.model, body.user_token or _bearer(request))


@app.post("/ask/voice")
async def ask_voice(request: Request, audio: UploadFile = File(..., description="WAV, mono 16-bit, 16 or 24 kHz"),
                    city: str = Form("nyc"), run: bool = Form(False), model: str | None = Form(None),
                    user_token: str | None = Form(None)):
    data = await audio.read()
    if not data:
        raise HTTPException(400, "empty audio")
    try:
        tr = voice.transcribe(data)
    except voice.TranscribeError as e:
        raise HTTPException(502, str(e))
    if not run:
        return tr
    if not tr["transcript"]:
        raise HTTPException(422, "nothing was heard in the audio")
    token = user_token or _bearer(request)

    def events() -> Iterator[dict[str, Any]]:
        yield {"type": "transcript", **tr}
        yield from planner.run(tr["transcript"], city, model=model, ctx=_ctx(city, token))

    return StreamingResponse(_sse(events()), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
