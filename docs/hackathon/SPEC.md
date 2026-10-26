# Build spec — "Get me in": the Table for Two concierge agent on Muse

Decided 26 Oct 2026. Spine = option 1 (agentic concierge), front = option 2 (voice),
infrastructure booster = option 6 (open weights on Modal), plus a Muse Image design pass.
Deadline: **Wed 4 Nov 2026, 9:00 PM ET**. Judged on impact → Meta tooling → depth → demo.

## 1. The one flow we demo
1. User taps the mic on tablefortwo and says: *"Get four of us into Carbone this Saturday
   around eight, or something similar in the West Village if that's impossible."*
2. Muse Voice Transcribe turns it into text (verified: transcript came back near-verbatim).
3. Muse Wonder plans with tools over our own data and live Resy: finds Carbone, sees it is
   a daily 10:00 AM ET drop with a 30-day window, checks live slots for Saturday, finds
   none, computes the next drop that covers Saturday, pulls Carbone's snipe tips, ranks
   two or three alternates by vibe/neighborhood/difficulty, checks those live, and sets a
   watch on Carbone.
4. The UI shows a three-tier plan: **Now** (live tables it found, with pre-filled booking
   links), **Drop** (exact release moment with a countdown and the tips), **Watch** (the
   alert it created). Later, a radar sweep finds a cancellation and the alert lands.

Impact: this is the wedge (impossible-table alerts) made conversational, in a domain the
builder knows firsthand (theme: *build for your world*).

## 2. Architecture
```
browser (index.html + new "Get me in" panel)
  |  mic -> WAV 16 kHz mono  ---------------->  POST api.meta.ai/v1/asr/transcribe (Muse Voice)
  |  text / transcript  --> SSE ------------->  agent service on Modal (Python, FastAPI)
  |                                              |- Muse Wonder via /v1/messages (planner, tool loop)
  |                                              |- tools = thin wrappers over scraper/*.py + cities/*.json
  |                                              |- Resy live calls via resy_find.slots (capped, cached)
  |                                              |- Supabase watchlists (create_watch)
  |                                              '- Muse Glimmer (30B open weights) on a Modal GPU (vLLM)
  |                                                 for cheap structured sub-tasks; falls back to muse-spark-1.3
  '- design assets generated with Muse Image (+ SAM 3.1 cut-outs, stretch)
```
Why Modal for the agent: it runs the existing Python scraper verbatim (no JS port of the
Resy client), it is a hackathon partner with credits, and the same account hosts the
open-weights model, so option 6 is one more Modal function, not a second platform.

Repo layout for new work: `agent/` (service), `agent/tools/`, `agent/prompts/`,
`agent/openweights/` (Glimmer deploy), `web/concierge.js` + panel markup in
`index.html`, `scripts/muse_art.py` (design pipeline), `design/` (assets).

## 3. Tool surface (name → backing code → contract)
| tool | backed by | notes |
|---|---|---|
| `search_spots(city, query?, neighborhood?, cuisine?, vibe?, occasion?, party?, max_difficulty?)` | `cities/<city>.json` → `spots[]` | fields: id, name, neighborhood, cuisine, difficulty 1–5, priceRange, platform, platformUrl, releaseSchedule, releaseTime, releaseDay, bookingWindowDays, walkIns, tips[], vibe[], occasion[], availability snapshot, photo |
| `get_spot(city, spot_id)` | same | full record incl. tips and `lastVerified` |
| `next_drop(city, spot_id, target_date)` | port of the countdown logic in `index.html` / `docs/ios/countdown-engine.md`; city tz from `cities/index.json` | returns the release instant (UTC + local), whether it covers `target_date`, and seconds until |
| `check_live_availability(city, spot_id, date, party)` | `scraper/resy_find.slots` (venue id resolution as in `scraper/sniper.py` + `resy_verify`) | **None = lookup failed, [] = genuinely nothing**; cache 10 min per (venue,date,party); hard cap 4 Resy calls per request; respect `resy_find.RATE_LIMITED`; OpenTable via `opentable_find.find` only if cheap |
| `just_opened(city, neighborhood?)` | `cities/just-opened.json` | the radar feed; items carry date/time/url/firstSeen |
| `booking_link(city, spot_id, date, party)` | `scraper/sniper.booking_url` | pre-filled platform URL |
| `similar_spots(city, spot_id, party, date, n=3)` | heuristic over vibe/occasion/cuisine/neighborhood/difficulty, optionally re-ranked by Spark Open | never more than 3, each then goes through `check_live_availability` |
| `create_watch(city, spot_id, date_from, date_to, party, channel)` | Supabase `watchlists` (see `supabase/migrations/0001_init.sql`, `web/auth.js`) | if no signed-in session, store in a hackathon `agent_watches` table or local JSON and say so |

Planner rules (system prompt): never call a table impossible before checking live; cap
Resy calls; answer in the three tiers; quote tips verbatim from the data; state data
freshness (`lastVerified`, `availability.checkedAt`); never invent slots or times; keep
the first answer under ~120 words, details on request.

## 4. Verified Meta Model API facts (26 Oct 2026, this key)
Base `https://api.meta.ai`, auth `Authorization: Bearer <MODEL_API_KEY>`.
Docs: https://dev.meta.ai/docs (protocols, tool-calling, prompt-caching, structured-output,
search-grounding, image-generation, speech-to-text, muse-spark-open deploy,
cookbook/agent-patterns).
- Models listed by `GET /v1/models`: muse-wonder-1.0, muse-spark-1.3 (+1.1/1.2, contributor
  variants), muse-image-1.0, muse-voice-transcribe-1.0, sam-3.1.
- `POST /v1/messages` (Anthropic shape, `anthropic-version: 2023-06-01`): Wonder and Spark both
  return `redacted_thinking` + `text` + `tool_use` blocks, `stop_reason: tool_use`; prompt
  caching active (`cache_read_input_tokens`). Use the Anthropic Python SDK with
  `base_url="https://api.meta.ai"`, `auth_token=MODEL_API_KEY`. Reserve `max_tokens` ≥ 1500:
  thinking tokens count against it (a 300 budget was eaten by thinking).
- `POST /v1/chat/completions` and `POST /v1/responses` also work (OpenAI shapes).
- `POST /v1/images/generations` `{model:"muse-image-1.0", prompt, n, size}` → `data[0].b64_json`
  (WebP). Sizes 1024x1024 and 1536x1024 confirmed. `/images/edit` exists per docs.
- `POST /v1/asr/transcribe`: multipart parts `request` (JSON:
  `{"model":"muse-voice-transcribe-1.0","audioEncoding":"WAV","mode":"PUSH_TO_TALK"}`) and
  `audio` (WAV, mono 16-bit, 16 or 24 kHz, ≤10 min, ≤32 MB). Response
  `{sessionId, transcript, audioDurationMs, turns[]}`. Do not use Git Bash curl for the
  multipart (it mangles the `;type=` part); Python `requests` works.
- `wss://api.meta.ai/v1/asr/realtime`: first text frame within 10 s =
  `{"authorization":{"accessToken":"Bearer <KEY>"},"audioEncoding":"PCM_24KHZ","model":"muse-voice-transcribe-1.0","mode":"PUSH_TO_TALK"}`;
  then binary PCM frames paced in real time; end with `{"type":"endStream"}`; events
  `{"type":"transcript","transcript":"...","final":bool}`. Stretch goal only.
- The voice model is NOT reachable through /v1/messages, /chat/completions or /responses.

## 5. Voice front end
MediaRecorder → decode to PCM → resample to 16 kHz mono → encode WAV in the browser (small
helper, no library) → POST to the agent service `/ask/voice`, which forwards to
`/v1/asr/transcribe` and streams the agent run. Keep the raw transcript visible and editable
before the agent runs so misheard names can be fixed.

## 6. Open weights on Modal (option 6)
**Use Muse Glimmer, not Spark Open.** Spark Open is an 816B-parameter MoE (42B active) that
needs 8 Blackwell GPUs (4 at NVFP4); it is not deployable on hackathon credits. Glimmer is a
30B dense multimodal model (Apache 2.0, 128K context, distilled from Spark, built for local
agentic workflows) and counts for the same "best build on open weights" bonus.
Deploy Glimmer with vLLM on one Modal GPU (docs: /docs/muse-glimmer/get-the-model,
/docs/muse-glimmer/quantization, /docs/muse-glimmer/deploy): bf16 (~60 GB) on an A100-80GB
or H100, or a 4-bit quant (~17 GB) on an L4/A10G at roughly $1/hour. Scale to zero,
short idle timeout, and expect a 1–3 minute cold start, which is why the API fallback
below is mandatory. Budget: the current $30 Modal credit covers the CPU agent service
for the whole hackathon plus a few GPU hours for Glimmer; the $100 credit, once approved,
removes the constraint. Use it for: (a) structured extraction of the
request into `{party, date, time_window, neighborhoods[], cuisines[], vibe[], must_have}`,
(b) `similar_spots` re-ranking, (c) alert copy, (d) scoring radar openings for relevance to
active watches. Behind a flag `OPENWEIGHTS=modal|api|off` with `muse-spark-1.3` as the API
fallback so the demo never depends on a cold GPU. This is also the entry for the
"best build on open weights" bonus.

## 7. Design pass with Muse Image
Explorations and the exact style suffix live in `design/muse-explorations/`. Plan:
- Icon: refine `icon-a` (two chairs) and `icon-b` (bell over plate) into the app icon set
  (`icons/`, `manifest.webmanifest`), halftone kept, no text.
- Hero: `card-art` direction for the landing/empty state of the Get-me-in panel.
- Per-venue art: `scripts/muse_art.py` reads each spot's `signatureDish`, cuisine and vibe,
  generates a square halftone plate into `art/<city>/<id>.webp` with a manifest and cache,
  and the card falls back to the Resy photo when absent. Stretch: SAM 3.1 to cut the dish
  out of the Resy photo and re-render it through the same style via `/images/edit`.
- Keep the house rules: original halftone/grain dot-screen art, no emoji, subtle animation.

## 8. Phase plan
- **26–27 Oct:** `agent/` skeleton on Modal; Wonder loop with `search_spots`, `get_spot`,
  `next_drop`, `booking_link`; CLI harness; SSE endpoint. Watch the Meta workshop 27 Oct noon ET.
- **28–29 Oct:** `check_live_availability` with caps/cache, `similar_spots`, `create_watch`;
  the Get-me-in panel in `index.html`; voice route wired.
- **30–31 Oct:** Glimmer on Modal behind the flag; design pass (icons, hero, venue art).
- **1–2 Nov:** demo script, record the 3-minute video with voiceover, README for judges,
  flip repo public, fill the submission form (prior-work call-out, bonus opt-ins: agentic,
  open weights, creative, community vote).
- **3 Nov:** buffer. Submit the evening of 3 Nov; deadline is 4 Nov 9 PM ET.

## 9. Owner actions (Karen)
- Claim credits from the event-details page: Modal $100 (needed for §2 and §6), Baseten,
  Fireworks; confirm the Meta $150 is on this key.
- Create the Modal account/workspace and set secrets `MODEL_API_KEY`, `SUPABASE_URL`,
  `SUPABASE_ANON_KEY` (never the service role key).
- Confirm which track was applied for (Indie vs Startup) and team members (≤4, approved).
- Make the repo public before submitting:
  `gh repo edit officialtellergram/table-for-two-muse --visibility public --accept-visibility-change-consequences`

## 10. Kickoff prompt for the Muse session
The hackathon folder is `C:\Users\Karen Plankton\Desktop\table-for-two-muse`. Open it in
VS Code (File → Open Folder) and run `claude` in its terminal; the project settings route
that session to Muse. Then paste:
> Read CLAUDE.md, HACKATHON.md and docs/hackathon/SPEC.md. Start phase 1: create `agent/`
> with a FastAPI app for Modal, an Anthropic-SDK client pointed at https://api.meta.ai using
> muse-wonder-1.0, and the tools search_spots, get_spot, next_drop, booking_link over
> cities/*.json and scraper/sniper.py. Add a CLI harness `python -m agent.cli "..."` that
> prints the tool calls and the final plan. No live Resy calls yet. Commit in small steps
> with clear messages.
