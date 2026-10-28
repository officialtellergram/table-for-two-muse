# `agent/` — the "Get me in" concierge (phase 2)

Muse Wonder plans over Table for Two's own drop data and live Resy through seven tools,
and Muse Voice Transcribe turns a spoken request into the text it plans from. The web
panel (`web/concierge.js`, opened by "Get me in" in `index.html`) streams the run.
Open weights (Glimmer on Modal) and the design pass are phase 3 (see
`docs/hackathon/SPEC.md` section 8).

```
agent/
  config.py        paths, model names, Meta Model API key lookup
  context.py       per-request state: the Resy call Budget (cap 4) and the guest's token
  data.py          cities/index.json + cities/<key>.json access
  drops.py         release-drop engine (port of nextDrop() from index.html)
  live.py          capped, cached, paced Resy slot lookups over scraper/resy_find
  watches.py       create_watch storage: Supabase watchlists (guest JWT) or local JSON
  voice.py         Muse Voice Transcribe (/v1/asr/transcribe, multipart)
  tools/           search_spots, get_spot, next_drop, booking_link,
                   check_live_availability, similar_spots, create_watch + registry
  prompts/system.md  planner rules, rendered with today's date and the city list
  planner.py       Anthropic SDK -> https://api.meta.ai tool loop (events generator)
  cli.py           python -m agent.cli "..."  |  --tool NAME k=v  |  --voice FILE.wav
  app.py           FastAPI: /health, /tools, /ask, /ask/stream (SSE), /ask/voice
  modal_app.py     Modal deployment wrapper
tests/             pytest, all offline (planner, Resy, Supabase and the voice API stubbed)
web/concierge.js   the panel: SSE client, NOW/DROP/WATCH rendering, mic -> WAV
```

## The tools

| tool | what it does | what it costs |
|---|---|---|
| `search_spots` | find a named spot or filter by neighborhood, cuisine, vibe, occasion, difficulty | nothing |
| `get_spot` | full record incl. tips, walk-ins, `lastVerified` | nothing |
| `next_drop` | the release that covers a date, whether it has passed, seconds until | nothing |
| `booking_link` | pre-filled platform URL for date + party | nothing |
| `check_live_availability` | real Resy slots for date + party, optional time window | 1 Resy call (cache 10 min, hard cap 4 per request) |
| `similar_spots` | up to 3 alternates ranked by vibe/occasion/cuisine/neighborhood/price/easier difficulty, each with its drop and a live check | 1 Resy call per Resy alternate, same budget |
| `create_watch` | arm an alert for a spot over a date range and window | a Supabase insert as the guest, or a local row |

`check_live_availability` reports an explicit `status`: `open`, `none` (Resy answered,
nothing open), or `failed` / `budget` / `rate_limited` / `unsupported`, which all mean
unknown. The system prompt forbids calling a table impossible on anything but `none`.
A 429 flips `resy_find.RATE_LIMITED` and the process stops calling Resy; the ban cools
off over hours, so the interactive path never retries.

`create_watch` writes `public.watchlists` through PostgREST with the anon key plus the
guest's own Supabase access token (the panel forwards it as `user_token`), so Row Level
Security applies as it does for `web/auth.js`. Without a token the watch goes to
git-ignored `agent/.watches.json` and the result says `alerts_active: false`.

## Run it

```bash
pip install -r agent/requirements.txt
python -m pytest tests -q

# the key: MODEL_API_KEY or ANTHROPIC_AUTH_TOKEN in the environment, or the
# git-ignored .claude/settings.local.json this folder already has
python -m agent.cli "Get four of us into Carbone this Saturday around eight, or something similar in the West Village if that's impossible."
python -m agent.cli --tool check_live_availability city=nyc spot_id=carbone date=2026-11-07 party=4 time_from=19:00 time_to=21:00
python -m agent.cli --tool similar_spots city=nyc spot_id=carbone party=4 date=2026-11-07 live_check=0
python -m agent.cli --voice speech.wav --transcribe-only
python -m agent.cli --system            # the rendered system prompt

uvicorn agent.app:app --reload          # http://127.0.0.1:8000/docs
python -m http.server 8080              # then open http://127.0.0.1:8080/ and tap "Get me in"
curl -N "http://127.0.0.1:8000/ask/stream?q=Carbone%20Saturday%20for%204"
```

The page talks to `http://127.0.0.1:8000` when served from localhost; anywhere else it
uses `CONCIERGE_URL_PROD` in `web/config.js`, or `?concierge=<url>` on the page URL
(remembered in localStorage), which is how the demo points at a `modal serve` URL.

## Deploy on Modal

```bash
modal token new
modal secret create meta-model-api MODEL_API_KEY=<key>      # add SUPABASE_URL / SUPABASE_ANON_KEY to override web/config.js
modal serve agent/modal_app.py          # dev URL, hot reload
modal deploy agent/modal_app.py         # stable URL -> CONCIERGE_URL_PROD in web/config.js
```

## How the Meta Model API is used

The Anthropic Python SDK is pointed at `https://api.meta.ai` with the Model API key as
`auth_token`. Wonder answers with `redacted_thinking` + `text` + `tool_use` blocks and
`stop_reason: tool_use`; the planner echoes the assistant blocks back untouched and
appends `tool_result` blocks until `end_turn`. `max_tokens` is 2000 because thinking
tokens count against it. Prompt caching kicks in from the second round. If Wonder
fails, the same request is retried on `muse-spark-1.3`.

Voice is a separate endpoint: `POST /v1/asr/transcribe`, multipart with a `request`
JSON part (`muse-voice-transcribe-1.0`, WAV, push-to-talk) and the `audio` part. The
browser records with MediaRecorder, decodes and resamples to 16 kHz mono 16-bit WAV
itself, and the service forwards it; the transcript is shown editable before the
planner runs.

## Phase 2 verification (28 Oct 2026)

In Chrome against the local service, the demo sentence ran in 6 rounds (24 s, 3 live
Resy calls): `search_spots` -> `get_spot` + `next_drop` -> `check_live_availability`
Carbone 2026-10-31 (none) -> `similar_spots` (Sartiano's, Ci Siamo, Marea; Marea open
at 19:30, 20:15, 20:30, 20:45, 21:00 with links) -> `create_watch` Carbone (saved locally,
no account attached) -> NOW/DROP/WATCH. The synthesized demo sentence (7.1 s WAV) came
back verbatim from Muse Voice Transcribe in 1.8 s through the CLI and `/ask/voice`.

## Phase 1 verification (26 Oct 2026)

The demo sentence ran in 5 rounds (about 24 s): `search_spots` -> `get_spot` +
`next_drop` + `booking_link` for Carbone -> `search_spots` West Village Italian ->
`next_drop` + `booking_link` for three alternates -> NOW/DROP/WATCH answer, with the
model stating that live tables are not checked in this build.
