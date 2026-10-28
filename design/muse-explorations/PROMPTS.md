# Muse Image explorations — 26 Oct 2026

Generated with `muse-image-1.0` via `POST https://api.meta.ai/v1/images/generations`
(OpenAI images shape: `{model, prompt, n, size}` → `data[0].b64_json`, WebP).

Shared style suffix used on every prompt (keep this verbatim for consistency):

> Original editorial halftone dot-screen illustration, coarse printed grain, two-colour
> risograph feel in deep ink black and warm cream with one bone-white highlight, no text,
> no letters, no emoji, no gradients, flat graphic shapes, high contrast, luxury-minimal
> restaurant brand.

| file | subject prompt (before the suffix) | size |
|---|---|---|
| icon-a.webp | App icon mark: two empty chairs facing each other across a small round table, seen from above, built entirely from halftone dots, centered on a solid cream square, generous margin. | 1024x1024 |
| icon-b.webp | App icon mark: a single ringing bell above a dinner plate, the alert for an impossible restaurant table, rendered as a halftone dot-screen graphic on solid ink-black square, centered, generous margin. | 1024x1024 |
| card-art.webp | Wide hero illustration: a tense moment at 9:59:59 before reservations drop, a wall clock, a phone glowing, an empty candlelit table, all in coarse halftone dot screen, cinematic composition, dark ink background with warm cream light. | 1536x1024 |
| venue-plate.webp | Square venue-card art: overhead view of a plate of rigatoni vodka with a glass of red wine on dark linen, abstracted into a bold halftone dot-screen print, chiaroscuro lighting, poster-like. | 1024x1024 |

## Design pass, 28 Oct 2026 (`scripts/muse_art.py`)

The pipeline keeps the suffix above verbatim (`STYLE` in the script) and caches every
prompt in `design/.cache/`. Candidates live in `design/candidates/` (icons, hero), kept
outputs in `art/` and `icons/`; `python scripts/muse_art.py gallery` writes a one-page
contact sheet at `design/candidates/index.html`.

| direction | subject prompt (before the suffix) | used for |
|---|---|---|
| icons/chairs | Two empty chairs facing each other across a small round table, seen straight from above, built from halftone dots, solid cream square. | alternative mark |
| icons/bell | A single ringing bell above a dinner plate, the alert for an impossible table, solid ink-black square. | alternative mark (alerts) |
| icons/candle | One lit candle on a small round table with two empty chairs, tight symmetric silhouette from the side, solid ink-black square. | **the app icon** (`candle-2` → `icons/*.png` via `build-icons`) |
| icons/plate-clock | A dinner plate whose rim is a clock face with fork and knife as the hands at one minute to ten. | alternative mark (drops) |
| hero/doorway | Maître d' stand and an open doorway into a glowing dining room seen from the dark street, one empty table for two inside. | alternative hero |
| hero/ten-oclock | The second before reservations drop: wall clock at 9:59, a phone glowing on an empty candlelit table for two. | alternative hero |
| hero/city-table | A single set table for two floating above a dense night skyline, water towers below. | **the Get-me-in hero** (`art/hero.webp`) and the share images (`icons/og-square.png`, `icons/og-image.png`) |
| venues | Overhead view of the spot's `signatureDish` on dark linen with one glass, its cuisine and vibe tags, chiaroscuro, poster-like. | `art/<city>/<id>.webp`, shown on the card in place of the platform photo when present |
