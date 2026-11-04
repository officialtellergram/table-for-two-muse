# Demo script — "Get me in" (3 minutes, voiceover)

For the submission video. One flow, per SPEC section 1: a spoken/typewritten ask →
Muse plans over our data and live Resy → a three-tier plan (Now / Drop / Watch).
Everything shown is live on the sandbox as of recording — no mocks.

- **URL on camera:** https://tablefortwo.city
- **Total VO:** ~370 words at a natural pace = ~2:55. Hard cap 3:00.
- **The ask (use verbatim, it's the panel's example):** "Get four of us into Carbone
  this Saturday around eight, or something similar in the West Village if that's
  impossible."

## Before you hit record (do all of these)

1. **Pre-warm Modal.** The agent scales to zero; a cold start costs 10–20 s you
   don't have on camera. Hit `/health`, then run one full ask (any model) 2–3
   minutes before recording so the container and the 10-min Resy cache are warm.
2. **Browser:** fresh profile or clear `t42-entered` / `t42-city` for
   tablefortwo.city so the landing plays.
   Bookmarks bar off, notifications off, 100% zoom, dark theme.
3. **Check the live facts an hour before.** The voiceover never promises a
   specific alternate's times — slots change. Screen shows what's real; VO says
   "finds one that's actually open". (Verified 2 Nov for Sat 7 Nov: Carbone
   nothing open 19:00–21:00 for 4; Marea 20:00/20:30/20:45/21:00 open.)
4. **Voice beat:** quiet room; the panel mic encodes 16 kHz WAV in-browser.
   Rehearse the sentence once so the transcript lands clean (Muse Voice
   Transcribe returned it near-verbatim in testing).
5. Record 1080p+. Cut dead air in the tool-run beats — the steps stream in
   ~10–25 s on Wonder; a gentle 2× speed-up on that section is honest and
   keeps pace. Do not speed up the final plan landing.

## Shot list + voiceover (read the lines as written)

### 0:00–0:15 — The problem (landing hero, embers rising)
*Screen: landing plays — wordmark, "The best reservations in your city, booked
for you", the example ask types itself.*
> "The hardest restaurant tables in any city are gone in seconds — released a
> month out, at an exact minute, to people who know the system. Table for Two
> is the system, in one ask."

### 0:15–0:40 — The ask (click "Get me in", type the sentence, send)
*Screen: concierge panel opens; the sentence goes in; Muse Wonder starts —
steps begin streaming (search_spots…).*
> "I tap 'Get me in' and just say what I want: four of us into Carbone this
> Saturday around eight — or something similar nearby. That's Muse Wonder,
> Meta's reasoning model, running as an agent on our own reservation data."

### 0:40–1:20 — The agent works (tool steps ticking by; plan lands)
*Screen: get_spot → next_drop → check_live_availability → similar_spots →
create_watch; then the NOW / DROP / WATCH cards.*
> "Watch it work. It finds Carbone, reads its release pattern — daily, ten AM,
> thirty days out — and checks Resy live for Saturday. Nothing open. So it
> computes the drop that covered this date, pulls the tactics regulars use,
> and checks alternates live until it finds one that's actually open for
> that night. Then it answers the way a great concierge would: what's open
> now, when the next drop lands, and a watch set on the table I asked for —
> with the booking link one tap away."

### 1:20–1:45 — Voice in (mic button, speak the sentence, transcript appears)
*Screen: hold the mic, speak the same ask; the Muse Voice Transcribe transcript
appears in the box, editable; send; steps start again (cut early).*
> "Or skip typing. I hold the mic and say it — Muse Voice Transcribe turns
> speech into the same ask, right in the browser. Voice in, agent out."

### 1:45–2:15 — Open weights (flip the model toggle to "Spark Open · open weights")
*Screen: model switch in the panel; run a short ask; the steps stream again —
this time the planner is Muse Spark Open on Baseten.*
> "Same agent, different brain. This run is planned by Muse Spark Open —
> Meta's open-weights model, served by Baseten — calling the identical seven
> tools. If it ever stumbles, it falls back to Wonder automatically. Two Meta
> planners, one concierge, zero retraining."

### 2:15–2:40 — Make it real (watch → alerts → the wider product)
*Screen: tap "Get alerts", the sign-in sheet (magic link), watch listed; cut to
the city grid scrolling — venue cards, drop countdowns, the cancellation radar.*
> "A watch only matters if it can reach me, so I sign in and the alert is
> real — the moment a cancellation frees up, it lands. Underneath is the same
> Table for Two our users already know: twenty-one cities of vetted rooms,
> every release time, every countdown — now with an agent on top. Even the
> artwork is Muse: every plate image was generated with Muse Image."

### 2:40–3:00 — Close (end card over the landing)
*Screen: end card — tablefortwo. wordmark, live URL, repo URL, model credits
(Muse Wonder · Muse Voice Transcribe · Muse Spark Open on Baseten · Muse Image).*
> "Built for the Meta Global AI Developer Hackathon on Muse — Wonder plans,
> Voice listens, Spark Open proves it open, Image paints it. The best
> reservations in your city, booked for you. Try it live."

## If something misbehaves on recording day

- **Modal cold on camera:** re-run step 1 of prep; never record the first ask cold.
- **Resy rate-limited (429):** the tool says so honestly and never calls a failed
  lookup "sold out". Wait 30+ min, keep `--limit` low, don't hammer retries.
- **Spark Open slow round:** the panel streams thinking/tool steps, so it's
  visibly working. Worst case it falls back to Wonder and says so in a note —
  that's a feature; keep the take if the plan lands.
- **Voice garbled:** re-record the sentence closer to the mic; the transcript is
  editable before sending, which the script already shows.
- **Saturday facts changed:** VO is written to survive any live outcome. Only
  re-check that Carbone is still "nothing open" — if it suddenly has tables,
  pick the same ask for a different hard room (Via Carota, difficulty 4) or
  move the party size up.

## End-card text (exact)

```
tablefortwo.
The best reservations in your city, booked for you.
Live: tablefortwo.city
Code: github.com/officialtellergram/table-for-two-muse
Built with Muse Wonder · Muse Voice Transcribe · Muse Spark Open (Baseten) · Muse Image
Prior work (baseline 2efd01a) declared in HACKATHON.md
```
