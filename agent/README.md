# `agent/` — the "Get me in" concierge (phase 1)

Muse Wonder plans over Table for Two's own drop data through four read-only tools.
Live Resy checks, alternates re-ranking, watches, voice and the web panel come in
later phases (see `docs/hackathon/SPEC.md` section 8).

```
agent/
  config.py        paths, model names, Meta Model API key lookup
  data.py          cities/index.json + cities/<key>.json access
  drops.py         release-drop engine (port of nextDrop() from index.html)
  tools/           search_spots, get_spot, next_drop, booking_link + registry
  prompts/system.md  planner rules, rendered with today's date and the city list
  planner.py       Anthropic SDK -> https://api.meta.ai tool loop (events generator)
  cli.py           python -m agent.cli "..."
  app.py           FastAPI: /health, /tools, /ask, /ask/stream (SSE)
  modal_app.py     Modal deployment wrapper
tests/             pytest, all offline (planner stubbed)
```

## Run it

```bash
pip install -r agent/requirements.txt
python -m pytest tests -q

# the key: MODEL_API_KEY or ANTHROPIC_AUTH_TOKEN in the environment, or the
# git-ignored .claude/settings.local.json this folder already has
python -m agent.cli "Get four of us into Carbone this Saturday around eight, or something similar in the West Village if that's impossible."
python -m agent.cli --tool next_drop city=nyc spot_id=carbone target_date=2026-11-07
python -m agent.cli --system            # the rendered system prompt

uvicorn agent.app:app --reload          # http://127.0.0.1:8000/docs
curl -N "http://127.0.0.1:8000/ask/stream?q=Carbone%20Saturday%20for%204"
```

## Deploy on Modal

```bash
modal token new
modal secret create meta-model-api MODEL_API_KEY=<key>
modal serve agent/modal_app.py          # dev URL, hot reload
modal deploy agent/modal_app.py         # stable URL
```

## How the Meta Model API is used

The Anthropic Python SDK is pointed at `https://api.meta.ai` with the Model API key as
`auth_token`. Wonder answers with `redacted_thinking` + `text` + `tool_use` blocks and
`stop_reason: tool_use`; the planner echoes the assistant blocks back untouched and
appends `tool_result` blocks until `end_turn`. `max_tokens` is 2000 because thinking
tokens count against it. Prompt caching kicks in from the second round. If Wonder
fails, the same request is retried on `muse-spark-1.3`.

## Phase 1 verification (26 Oct 2026)

The demo sentence ran in 5 rounds (about 24 s): `search_spots` -> `get_spot` +
`next_drop` + `booking_link` for Carbone -> `search_spots` West Village Italian ->
`next_drop` + `booking_link` for three alternates -> NOW/DROP/WATCH answer, with the
model stating that live tables are not checked in this build.
