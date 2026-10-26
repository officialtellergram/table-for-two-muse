# Drop Watch curation scraper

Turns a small **seed file** into a dashboard-ready `cities/<key>.json`.

The split that matters:

| You provide (can't be scraped) | Tool auto-fills (scraped) |
|--------------------------------|---------------------------|
| `name`, `platform`, `platformUrl` | `coordinates` (JSON-LD → OSM geocode) |
| `releaseSchedule`, `releaseTime`, `releaseDay` | `cuisine`, `priceRange`, `phoneNumber` |
| `difficulty`, `bookingWindowDays` (recommended) | `neighborhood` (best-effort) |
| `tips`, `walkIn*`, `signatureDish` (optional) | `lastVerified` = today |

`releaseSchedule` + `releaseTime` are **policy facts** (e.g. "drops daily at 10 AM").
No reservation platform exposes them in an API — verify each from the venue's
Resy/Tock/OpenTable page or socials. That's the real curation work; the tool does the rest.

## Setup
```bash
# uses your Anaconda python
& "$env:USERPROFILE\anaconda3\python.exe" -m pip install -r requirements.txt   # requests only
```

## Generate a city
```bash
cd scraper
python curate.py sources/la.csv --city la --label "Los Angeles" \
    --region "Los Angeles, CA" --update-manifest
```
- Writes `../cities/la.json`.
- `--update-manifest` flips the city live in `../cities/index.json` (map center auto-averaged from spots).
- Omit `--update-manifest` to just print the manifest snippet to paste yourself.
- `--no-fetch` runs fully offline (schema only, no enrichment) — good for a quick dry run.

## Seed format
CSV (spreadsheet-friendly) or JSON (a bare list of spot objects). CSV columns
(all optional except `name`; blanks get auto-filled where possible):

```
id, name, platform, platformUrl, website, difficulty, priceRange,
releaseSchedule, releaseTime, releaseDay, bookingWindowDays,
walkIns, walkInDoors, walkInLineBy, walkInAdvice,
neighborhood, cuisine, phoneNumber, signatureDish, tips, address, lat, lng
```
- `tips` — multiple tips separated by `|`.
- `walkIns` — `true`/`yes`/`1`.
- `address` — only used to improve geocoding; not stored.
- `lat,lng` — set these to skip geocoding entirely for a row.
- Rows whose `name` starts with `#` are treated as comments.

See `sources/la.example.csv`. Output validates against the same schema the dashboard
reads — once written, the city appears in the switcher with live countdowns and map pins.

## Being polite
Network calls send an identifiable User-Agent, cache geocodes in `.geocache.json`,
and respect OpenStreetMap's 1 req/sec limit. This reads public pages only; it does
**not** log into or automate any reservation platform.
