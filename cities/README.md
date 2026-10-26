# Adding a city

You **do not edit `index.html`** to add a city. Two steps:

### 1. Drop a dataset file
Copy `_template.json` to `cities/<key>.json` (e.g. `cities/la.json`) and fill in the spots.
A bare array of spots works too — the wrapper `{ "meta": ..., "spots": [...] }` is optional.

### 2. Register it in `index.json`
Change that city's `source` from `{"type":"soon"}` to:

```json
{ "type": "json", "url": "cities/la.json" }
```

Reload the page. Done — it appears in the city switcher, fully filterable, with live countdowns and map pins.

---

## Source types (the `source` field in `index.json`)

| `type`        | Meaning                                                              |
|---------------|---------------------------------------------------------------------|
| `hardtobook`  | Pull live from the hardtobook.xyz API (used by NYC). Optional `url`. |
| `json`        | Load a static file you drop in this folder. Needs `url`.            |
| `rest`        | Any endpoint returning `{spots:[]}` or a bare `[]`. Needs `url`.    |
| `soon`        | Greyed-out "coming soon" placeholder. No data.                      |

## Spot schema

Every field is optional **except** the countdown inputs. The engine computes the
"next reservation drop" purely from:

- **`releaseSchedule`** — `daily` · `weekly` · `calendar-month` · `monthly` · `none`
- **`releaseTime`** — e.g. `"10:00 AM ET"`, `"12:00 AM (Midnight) ET"`
- **`releaseDay`** — only for `weekly` (e.g. `"Saturday midnight"`); for monthly the drop is the 1st

Everything else (`name`, `coordinates`, `difficulty`, `platform`, `tips`, `walkIn`, …)
is display only. See `_template.json` for the full annotated shape.

Times are interpreted in **America/New_York**. If you add a West Coast city and want
local release times, that's a small change to the `ET` constant / engine — ask and it
can be made per-city.
