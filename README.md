# Table for Two ✌︎

A luxury-minimal dashboard for hard-to-book restaurant reservations across NYC, DC,
Richmond, Boston, and Houston. Real Resy availability for the next 7 days, live
countdowns to monthly reservation drops (per-city timezone, DST-aware), one-tap
pre-filled booking links for every platform, list + map views, and a dark/light theme.

## Host it — one click

[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/officialtellergram/table-for-two)

Click the button → sign in with GitHub → **Save & Deploy**. That's it — no settings to
fill in (the included `netlify.toml` sets everything). You get a public HTTPS URL like
`https://your-name.netlify.app` to share. Every future `git push` redeploys automatically.

> Want a nicer URL? In Netlify: **Site configuration → Change site name**.

Prefer Vercel? Import the repo at [vercel.com/new](https://vercel.com/new) and set
**Root Directory = `deploy`** (the one setting it needs).

## Run locally
Must be served over http (not opened as a `file://` — it'll show a warning if you do):

```bash
npx serve -l 8080 .      # then open http://localhost:8080
# or:  python -m http.server 8080
```

## How it's built
- **`index.html`** — the whole app, single file, no build step.
- **`cities/`** — one JSON dataset per city + a manifest. Adding a city never touches code (see [`cities/README.md`](cities/README.md)).
- **`deploy/`** — the published folder (a clean copy of `index.html` + `cities/`); this is what Netlify serves.
- **`scraper/`** — the Python pipeline that researches each city, validates Resy links, checks live availability, ranks the top 25, and regenerates the datasets. See [`scraper/refresh.md`](scraper/refresh.md).

## Data & caveats
- NYC is sourced from the unofficial [hardtobook.xyz](https://www.hardtobook.xyz) data; DC/Richmond/Boston/Houston are research-compiled top-25 lists.
- **Availability is a snapshot** baked in at the last refresh (stamped "as of …"); it isn't live until the snapshot is regenerated. Release times can change — always confirm on the platform.
