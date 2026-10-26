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

## Working on it with Muse
Open Claude Code in this folder. `.claude/settings.local.json` (git-ignored, holds the
API key) points every model slot at Muse, so plain `claude` here already uses it. From
any other folder, the global `muse` command does the same thing.

## What was deliberately left out of the copy
- `.github/workflows/` — the production radar, drop-detection and SEO jobs. They run on
  schedules, hit Resy, and push commits; a second copy would double the load on Resy
  and race the real repo. Re-add on purpose if the hack needs CI.
- `CNAME` — so GitHub Pages here can't claim the production domain.
- `wrangler.jsonc` worker name is `table-for-two-muse`, so a stray `wrangler deploy`
  cannot overwrite the live worker.
