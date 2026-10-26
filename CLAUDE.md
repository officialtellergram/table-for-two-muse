# Table for Two — Muse hackathon copy

Read `HACKATHON.md` first, then `README.md`. The app is a single-file static
site (`index.html`) over per-city JSON in `cities/`; `deploy/` is the published
mirror; `scraper/` is the Python research + radar pipeline (docs in
`scraper/README.md`, `scraper/sniper.md`, `scraper/refresh.md`); `supabase/`
holds Stage-2 auth/watchlists/alerts.

Rules for this repo:
- This is a hackathon sandbox, not production. Never push to the
  `officialtellergram/table-for-two` remote and never run `wrangler deploy`
  against the production worker name.
- Resy is rate-limited (429s cool off over hours). Keep any live sweeps small:
  few cities, `--limit` low, `--sleep` ≥ 0.75s.
- Secrets never go in git. The Muse key is in the git-ignored
  `.claude/settings.local.json`; Supabase service keys never live on disk here.
