# Weekly refresh routine — Table for Two

This is the script the scheduled cloud agent runs once a week. It re-researches the
four AI-sourced cities, regenerates every dataset (with live availability + top-25
ranking), and pushes — the connected host then auto-deploys.

## Steps (run in order)

1. **Re-research each city.** For DC, Richmond, Boston, Houston, run a web-research
   pass per `research_spec.md` and write the result to `scraper/sources/<city>.json`
   (a JSON array of ~32 candidate objects, ordered hardest-first). Use the prompt
   template below. Houston release times are **Central ("CT")**; the others Eastern ("ET").

2. **Regenerate + rank.** From the repo root:
   ```
   python scraper/refresh.py --fetch-nyc
   ```
   This re-pulls NYC from the hardtobook API, runs the scraper on all five cities
   (validating Resy links, checking live availability for a party of 2 over the next
   14 days), ranks each researched city by hardness, trims to the **top 25**, updates
   the manifest, and restages `deploy/`.

3. **Commit & push.**
   ```
   git add -A
   git commit -m "weekly refresh YYYY-MM-DD"
   git push
   ```
   The connected host (Netlify/Vercel, publish dir = `deploy`) redeploys automatically.

4. **Report** what changed: new entries, dropped entries, and the new open/booked counts.

## Per-city research prompt template
Replace {CITY}, {SOURCES}, and {TZ}:

> Research the hardest-to-book restaurants in {CITY} for a reservation dashboard.
> Return a BROAD pool of ~32, ordered hardest-to-book first. Rank by: reservation
> scarcity (instant sellouts, tiny rooms, monthly drops), acclaim (Michelin, James
> Beard, "best of"/"hardest reservation" lists), and current buzz (new hot openings
> rise). Must be currently OPEN and take reservations; skip walk-in-only and
> fast-casual. Use real web search + fetch ({SOURCES}, Michelin, venue sites,
> Resy/Tock/OpenTable). Do NOT invent data; verify open status and the actual booking
> platform. Release times in {TZ}.
> For each return JSON: id, name, platform (Resy|Tock|OpenTable|SevenRooms),
> platformUrl, website, difficulty (1-5), priceRange, releaseSchedule, releaseTime,
> releaseDay, bookingWindowDays, walkIns, neighborhood, cuisine, address,
> signatureDish, tips (array; "VERIFY release time" where unsourced), evidence.
> Return ONLY a JSON array of ~32 objects, hardest first.

Sources by city:
- DC — Eater DC, Washingtonian, The Infatuation
- Richmond — Richmond Magazine, Eater, Style Weekly, The Infatuation
- Boston — Eater Boston, Boston Magazine, The Infatuation (note Michelin arrived 2025/26)
- Houston — Eater Houston, Houston Chronicle, Texas Monthly, The Infatuation ({TZ}=CT)

## Notes
- Ranking/trim math lives in `curate.py` (`hardness()` + `--top 25`); see `research_spec.md`.
- The pipeline self-heals Resy links and skips re-enriching already-complete spots.
- If a research pass returns fewer than 25 usable candidates, keep what's valid — don't pad.
