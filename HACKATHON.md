# Table for Two × Meta Global AI Developer Hackathon

Hackathon entry built on top of [Table for Two](https://github.com/officialtellergram/table-for-two)
(live at tablefortwo.city), developed here with Meta's **Muse** models — Muse Wonder
drives Claude Code for the build, and the product itself integrates the Meta Model API.

## Prior-work declaration (required by the rules: "new work only, call out prior work")
- **Prior work** = commit `2efd01a` ("Hackathon baseline"), a verbatim snapshot of the
  existing Table for Two repo taken on 26 Oct 2026 before the kickoff ended: the static
  site (`index.html`, `cities/`, `deploy/`), the Python research/radar pipeline
  (`scraper/`), Supabase stage-2 (`supabase/`, `web/`) and iOS docs (`docs/ios/`).
  None of it used any Meta model.
- **New work** = every commit after the baseline. Everything demoed in the submission
  video is built from those commits.

## The hackathon in one screen (from the 26 Oct 2026 kickoff stream)
- **Organiser/partners:** Meta (Model API team) with Cerebral Valley; partners Baseten,
  Fireworks AI, Modal.
- **Window:** hacking opens after the 26 Oct kickoff; **submissions due Wed 4 Nov 2026, 9:00 PM ET.**
- **Tracks:** Indie Developer (individuals/students; judged on creativity, technical
  ambition, whether it works) and Startups (incorporated). You applied to one of them.
- **Themes:** *Build for your world* (bring Meta models into a domain you know firsthand)
  or *Push the frontier*. Table for Two is squarely *Build for your world*.
- **Models on offer:** Muse Spark and Muse Wonder (reasoning, via Model API), Muse Code
  (coding agents), Muse Image, Muse Voice Transcribe, and open-weights Muse Glimmer /
  Muse Spark Open (local or via Fireworks, Baseten, Modal).
- **Credits:** $150 Meta Model API, $100 Baseten (+2M TPM), $100 Modal (first 1,000
  teams), $25 Fireworks. Claim forms live on the Cerebral Valley event-details page.
- **Rules:** new work only; must be open source with a **public GitHub repo**; demo only
  what was built during the event; teams of up to 4, all approved; nothing that breaks
  legal/ethical/platform policy. Organisers explicitly discourage plain chat wrappers,
  simple RAG apps, image analyzers and medical-advice generators.
- **Prizes:** $950K across tracks + $50K bonus. Indie: $150K first down to $25K fifth.
  Startup: $250K first, $150K second, down to $25K fifth. Bonus: most viral (X post
  linked in the form), best build on open weights (Glimmer/Spark Open), community vote
  (project-gallery upvotes), best agentic use case ($5K), best creative build ($5K).
- **Judging:** stage 1 pass/fail — fits a theme **and uses Meta AI products**. Stage 2,
  Meta judges score 0–10 on the rubric: **impact first** (real-world potential, who
  benefits, fits the problem statement), then **use of Meta AI tooling**, **technical
  depth**, **demo**. Top 5 per track present live at the 9 Nov closing ceremony, where
  judges watch the 3-minute video and rank first to fifth. Community-vote winner
  announced 16 Nov.
- **Submission:** "Submit Project" button on the event page; the **3-minute demo video
  with voiceover** is a major part of the score; public repo link; prior-work call-out;
  optional bonus-prize opt-ins. Review the form early.
- **Live sessions:** Meta engineering workshop Tue 27 Oct (Suraj) and Wed 28 Oct (Yash),
  Fireworks workshop Fri 30 Oct, all noon ET; Meta office hours every weekday morning ET
  in Discord (event URL + `/discord`).

## What this means for the build
The baseline product makes **zero model calls**: curation is done offline by agents, and
the site is static JSON. To pass stage 1 and score on "use of Meta AI tooling", the
shipped app must call the Meta Model API itself — e.g. a Muse-powered concierge that
reasons over the live drop/availability data, agentic booking-window detection, or a
voice flow via Muse Voice Transcribe. Decide that scope first, then build.

**Decision (26 Oct 2026):** build the **"Get me in" concierge agent** on Muse Wonder, with
voice entry via Muse Voice Transcribe and Muse Glimmer (30B open weights) on Modal as the
open-weights layer, plus a Muse Image design pass. (Spark Open was the first idea; it is an
816B MoE needing 8 Blackwell GPUs, so Glimmer it is.) The full build spec, verified API shapes, tool
surface and phase plan are in `docs/hackathon/SPEC.md`.

## Attribution
Hackathon commits are made by Claude Code running on **muse-wonder-1.0** through the Meta
Model API, so each one carries `Co-Authored-By: Muse Wonder 1.0 <muse@noreply.meta.ai>`
(the committed `.claude/settings.json` sets this trailer for Claude Code sessions here,
`CLAUDE.md` instructs the agent to add it, and `.githooks/prepare-commit-msg` adds it to any
commit that has no co-author yet; enable the hook once per clone with
`git config core.hooksPath .githooks`). The address is an attribution label, not a mailbox.
The baseline and setup commits were made with Claude and say so.

## Working on it with Muse
Open Claude Code in this folder. `.claude/settings.local.json` (git-ignored, holds the
API key) points every model slot at Muse, so plain `claude` here already uses it. From
any other folder, the global `muse-cc` command does the same thing (`muse` itself is left
free for Meta's Muse Code CLI, which also reads `CLAUDE.md`).

## What was deliberately left out of the copy
- `.github/workflows/` — the production radar, drop-detection and SEO jobs. They run on
  schedules, hit Resy, and push commits; a second copy would double the load on Resy
  and race the real repo. Re-add on purpose if the hack needs CI.
- `CNAME` — so GitHub Pages here can't claim the production domain.
- `wrangler.jsonc` worker name is `table-for-two-muse`, so a stray `wrangler deploy`
  cannot overwrite the live worker.

## Status log
- 26 Oct 2026: baseline, rules brief and build spec in place; phase 1 (agent skeleton) starts next.
- 26 Oct 2026 (evening): phase 1 landed in `agent/`: drop engine, the four read-only tools, the Muse Wonder tool loop, CLI harness, FastAPI + SSE service and the Modal wrapper (24 offline tests). Demo sentence verified live on muse-wonder-1.0. These commits were made with Claude, not Muse, and say so in their trailer. Next: phase 2 (live availability, similar_spots, create_watch, the Get-me-in panel, voice route).
