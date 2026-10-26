# Table for Two — Meta Global AI Developer Hackathon entry

Read `HACKATHON.md` first (rules, rubric, deadline 4 Nov 2026 9 PM ET, prior-work
declaration), then `README.md`. The app is a single-file static site (`index.html`)
over per-city JSON in `cities/`; `deploy/` is the published mirror; `scraper/` is the
Python research + radar pipeline (docs in `scraper/README.md`, `scraper/sniper.md`,
`scraper/refresh.md`); `supabase/` holds Stage-2 auth/watchlists/alerts.

Rules for this repo:
- Everything after commit `2efd01a` is hackathon work and must stay distinguishable as
  such: clear commit messages, no rewriting the baseline.
- The product must use Meta AI models at runtime (Meta Model API: Muse Spark / Muse
  Wonder; optionally Muse Voice Transcribe / Muse Image / open-weights Glimmer or
  Spark Open). Using Muse only as the coding agent does not satisfy the judging rubric.
- Judging weighs impact first, then Meta tooling use, technical depth, and the
  3-minute demo. Prefer one working, demoable flow over breadth.
- This is a hackathon sandbox, not production. Never push to the
  `officialtellergram/table-for-two` remote and never run `wrangler deploy` against
  the production worker name.
- Resy is rate-limited (429s cool off over hours). Keep any live sweeps small: few
  cities, `--limit` low, `--sleep` ≥ 0.75s.
- Secrets never go in git. The Muse key is in the git-ignored
  `.claude/settings.local.json`; Supabase service keys never live on disk here.
