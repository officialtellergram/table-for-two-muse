# Table for Two × Muse hackathon

Hackathon fork of [Table for Two](https://github.com/officialtellergram/table-for-two)
(live at tablefortwo.city), built here with Meta's **muse-wonder-1.0** driving
Claude Code. Snapshot taken from `main` on 26 Oct 2026; history starts fresh so
every commit in this repo is hackathon work.

## Working on it with Muse
Open Claude Code in this folder. `.claude/settings.local.json` (git-ignored, holds
the API key) points every model slot at Muse, so plain `claude` here already uses
it. From any other folder, the global `muse` command does the same thing.

## What was deliberately left out of the copy
- `.github/workflows/` — the production radar, drop-detection and SEO jobs. They
  run on schedules, hit Resy, and push commits; a second copy would double the
  load on Resy and race the real repo. Re-add on purpose if the hack needs CI.
- `CNAME` — so GitHub Pages here can't claim the production domain.
- `wrangler.jsonc` worker name is `table-for-two-muse`, so a stray
  `wrangler deploy` cannot overwrite the live worker.

Everything else — `index.html`, `cities/`, `deploy/`, `scraper/`, `supabase/`,
`web/`, `docs/ios/` — is a faithful copy. See `README.md` for how it runs.
