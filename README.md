# Tech Radar

A self-hosted technology radar that automatically discovers emerging technologies from GitHub Trending, Reddit, and RSS feeds, then lets you curate them through a CLI and view the results as an interactive static dashboard.

---

## How it works

```
GitHub Trending ──┐
Reddit            ├──► runner.py ──► data/items/ ──► data/radar.json ──► dashboard
RSS Feeds         ┘                       ▲
                                    radar.py (human curation)
```

1. **Discovery** — `runner.py` runs all scrapers, deduplicates across sources using canonical GitHub URLs, and writes one JSON file per technology into `data/items/`.
2. **Curation** — `radar.py` lets you triage the inbox (`Discovered` ring), promote items to `Assess`, `Trial`, or `Adopt`, and fix metadata. Every change rebuilds `data/radar.json` automatically.
3. **Deploy** — `build_site.py` assembles a self-contained `site/` folder you can push to GitHub Pages, Netlify, or serve locally.

---

## Prerequisites

- Python 3.8+ (no third-party packages — stdlib only)
- A modern browser (for the dashboard)
- No Node.js, no npm, no build step

---

## Quick start

```bash
# 1. Run discovery (writes to data/items/, builds data/radar.json)
python runner.py

# 2. See what was found
python radar.py list --ring Discovered

# 3. Promote something you like
python radar.py promote "Bun" Trial

# 4. Build the static site
python build_site.py

# 5. Preview in browser
cd site && python -m http.server 8000
# open http://localhost:8000
```

---

## Scripts

### `runner.py` — Discovery

```bash
python runner.py              # run all scrapers, then build radar.json
python runner.py --build      # only rebuild radar.json from existing items (no scraping)
python runner.py --dry-run    # discover and print, write nothing
```

The runner never touches items a human has already classified. Re-discovered technologies get their `last_seen` refreshed and their star count updated, but their ring and other curated fields are left alone.

### `radar.py` — Curation

```bash
python radar.py list                          # all items, grouped by ring
python radar.py list --ring Discovered        # the review inbox

python radar.py show <id-or-name>             # full JSON for one item
python radar.py find <text>                   # search name + description

python radar.py promote <id-or-name> Trial    # move to a ring
python radar.py demote <id-or-name>           # send back to Discovered
python radar.py set <id-or-name> quadrant Platforms
python radar.py set <id-or-name> company "Anthropic"
python radar.py archive <id-or-name>          # Hold + 'archived' tag
```

Items can be referenced by exact id (`github:oven-sh/bun`), exact name (`Bun`), or a unique partial name (`uv`).

### `build_site.py` — Deploy

```bash
python build_site.py    # produces ./site/ ready for static hosting
```

Strips the `export default` from `dashboard.jsx` so it runs under the CDN/Babel setup without a build step.

---

## Data model

### Rings

| Ring | Meaning |
|------|---------|
| `Discovered` | Found by a scraper; not yet reviewed — the inbox |
| `Assess` | Worth a closer look or experiment |
| `Trial` | Actively using on real work |
| `Adopt` | Recommended default |
| `Hold` | Avoid / deprecated / not now |

Only a human moves items out of `Discovered`. Scrapers never classify.

### Quadrants

`Techniques` · `Tools` · `Platforms` · `Languages`

### Item schema

```json
{
  "id": "github:oven-sh/bun",
  "name": "Bun",
  "description": "Incredibly fast JavaScript runtime",
  "quadrant": "Tools",
  "ring": "Trial",
  "source": "GitHub",
  "url": "https://github.com/oven-sh/bun",
  "canonical_url": "github.com/oven-sh/bun",
  "also_seen": [
    { "source": "Reddit", "url": "https://...", "seen": "2026-05-23" }
  ],
  "company": "Oven",
  "stars": 78900,
  "momentum": 72,
  "tags": ["runtime"],
  "first_seen": "2026-05-21",
  "last_seen": "2026-05-23",
  "stars_history": { "2026-05-21": 78900, "2026-05-23": 78950 },
  "trend": "up",
  "trend_delta": 50
}
```

`trend` and `trend_delta` are computed by `runner.py` at build time from `stars_history` — they are not stored in the per-item files.

---

## Deployment

| Target | Command |
|--------|---------|
| Local preview | `cd site && python -m http.server 8000` |
| GitHub Pages | Push `site/` contents to the `gh-pages` branch |
| Netlify | Drag and drop the `site/` folder onto Netlify |

---

## Project layout

```
tech-radar/
├── runner.py           # discovery orchestrator — runs scrapers daily
├── radar.py            # curation CLI — human triage and ring management
├── radar_core.py       # shared library — item schema, dedup, persistence
├── build_site.py       # static site assembler
├── github_trending.py  # GitHub Trending scraper  ← should be scrapers/
├── reddit.py           # Reddit scraper            ← should be scrapers/
├── index.html          # HTML shell — loads React + dashboard.jsx via CDN
├── dashboard.jsx       # React dashboard (Observatory + Dispatch views)
├── SKILL-manage.md     # Skill definition for Claude-assisted curation
├── concept-drawings/   # Prototype dashboard concepts (dashboard2/3.jsx)
├── data/
│   ├── items/          # one .json file per technology (generated)
│   │   ├── github/
│   │   └── reddit/
│   ├── raw/            # audit trail of raw scrape output (generated)
│   └── radar.json      # aggregated payload for the dashboard (generated)
└── site/               # deployable static site (generated by build_site.py)
    ├── index.html
    ├── dashboard.jsx
    └── data/
        └── radar.json
```

---

## Known gaps

| Gap | Status |
|-----|--------|
| `scrapers/` package | `runner.py` imports from `scrapers.github_trending` etc. but the files live at the top level. Move `github_trending.py` and `reddit.py` into a `scrapers/` directory and add `scrapers/__init__.py`. |
| `scrapers/base.py` | The scrapers import `from scrapers.base import Scraper` — this base class needs to be created. |
| `scrapers/rss_feeds.py` | RSS scraper is registered in `runner.py` but not yet implemented. |
| `dashboard.jsx` | The build expects `dashboard.jsx` at the root; only prototype versions (`concept-drawings/dashboard2.jsx`, `dashboard3.jsx`) exist. |

---

## Suggested weekly workflow

1. `python runner.py` — run discovery (or schedule it via cron)
2. `python radar.py list --ring Discovered` — see what's new
3. For each interesting item: `show`, then `promote` to the right ring
4. Fix wrong quadrants or missing companies: `set`
5. Archive irrelevant or stale tech: `archive`
6. `python build_site.py` — publish the updated dashboard

See `SKILL-manage.md` for Claude-assisted curation instructions.
